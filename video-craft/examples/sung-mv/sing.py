"""Render the Paper Bird score with the official Qixuan 2.7.0 DiffSinger ONNX bank.

python sing.py BANK_DIRECTORY VOCODER_DIRECTORY out/vocal.wav [--line 3]
A single-line render preserves the film's time origin. Models are provided separately.
"""
import argparse
import json
from pathlib import Path
import subprocess
import wave

import numpy as np
import onnxruntime as ort
import yaml


RATE = 44100
HOP = 512
TRANSPOSE = -3
HERE = Path(__file__).resolve().parent


def read_score():
    command = "import {beat,duration,lines} from './song.mjs'; console.log(JSON.stringify({beat,duration,lines}))"
    return json.loads(subprocess.check_output(['node', '--input-type=module', '-e', command], cwd=HERE))


def pronunciations(path, wanted):
    # The official full dictionary also includes other languages. Only keep this score's entries.
    found = {}
    current = None
    with path.open(encoding='utf-8-sig') as f:
        for line in f:
            if line.startswith('- grapheme: '):
                word = line.partition(': ')[2].strip()
                current = word if word in wanted else None
                if current:
                    found[current] = []
            elif current and line.startswith('  - '):
                found[current].append(line[4:].strip())
    missing = wanted - found.keys()
    if missing:
        raise ValueError(f'Unknown pinyin in the selected dictionary: {sorted(missing)}')
    return found


def row(seq, dtype):
    return np.asarray(seq, dtype=dtype).reshape(1, -1)


class ModelSet:
    def __init__(self, folder, config_name, roles, options):
        config = yaml.safe_load((folder / config_name).read_text(encoding='utf-8-sig'))
        for role in roles:
            session = ort.InferenceSession(str(folder / config[role]), sess_options=options,
                                           providers=['CPUExecutionProvider'])
            setattr(self, role, session)
        if 'phonemes' in config:
            self.phones = json.loads((folder / config['phonemes']).read_text(encoding='utf-8'))
            self.lang = json.loads((folder / config['languages']).read_text(encoding='utf-8'))['zh']

    def tokens(self, phones):
        return {'tokens': row([self.phones[x] for x in phones], np.int64),
                'languages': row([self.lang if x.startswith('zh/') else 0 for x in phones], np.int64)}


def infer(session, **inputs):
    outputs = session.run(None, {name: np.asarray(value) for name, value in inputs.items()})
    return {port.name: arr for port, arr in zip(session.get_outputs(), outputs)}


def schedule(line, beat, dictionary):
    # Count cumulative frames, so phone, note and audio boundaries stay on the same clock.
    # Neighbouring syllables touch. The rest between the two chorus calls remains audible.
    notes = line['notes']
    pinyin = line['pinyin'].split()
    if len(notes) != len(pinyin):
        raise ValueError(f"Each syllable needs one note for {line['text']}")
    start = round((notes[0][1] * beat - .30) * RATE / HOP)
    def frame(sec):
        return round(sec * RATE / HOP) - start
    words, tones, rests, ends = [], [], [], []
    def append(phones, tone, rest, end):
        if ends and end <= ends[-1]:
            raise ValueError('The lyric and rest boundaries must advance in time.')
        words.append(phones)
        tones.append(tone)
        rests.append(rest)
        ends.append(end)
    append(['SP'], notes[0][3] + TRANSPOSE, True, frame(notes[0][1] * beat - .065))
    for i, (_, onset, length, midi) in enumerate(notes):
        note_end = (onset + length) * beat
        next_start = notes[i + 1][1] * beat - .065 if i + 1 < len(notes) else note_end + .23
        pause = next_start - note_end > .22
        append(dictionary[pinyin[i]], midi + TRANSPOSE, False, frame(note_end if pause else next_start))
        if pause:
            append(['SP'], midi + TRANSPOSE, True, frame(next_start))
    return start, words, np.diff([0, *ends]), tones, rests


def fit_phones(words, lengths, predicted, onset_ms=None):
    result = []
    syllable_index = 0
    for syllable, length in zip(words, lengths):
        n = len(syllable)
        if length < n:
            raise ValueError('This note is too short for its consonants and vowels.')
        weights = np.maximum(.001, predicted[len(result):len(result) + n])
        ends = np.rint(np.cumsum(weights) / weights.sum() * (length - n)).astype(int)
        allocation = 1 + np.diff([0, *ends])
        if n == 2:
            # This bank encodes each Mandarin final as one token. Sustain the final on long notes.
            # Unconstrained predictions gave the consonant of the last "心" over 800 ms of hiss.
            onset = syllable[0].split('/')[-1]
            max_onset = .095 if onset in {'s', 'sh', 'x', 'ch', 'zh', 'c', 'f', 'q', 'j'} else .063
            attack = min(allocation[0], round(max_onset * RATE / HOP))
            if onset_ms is not None:
                attack = int(np.clip(round(onset_ms[syllable_index] * .001 * RATE / HOP), 1, length - 1))
            allocation = [attack, length - attack]
        if syllable != ['SP']:
            syllable_index += 1
        result.extend(allocation)
    return row(result, np.int64)


def render_line(line, beat, dictionary, duration, pitch, variance, acoustic, vocoder):
    start, words, lengths, tones, rests = schedule(line, beat, dictionary)
    phones = [ph for syllable in words for ph in syllable]
    word_div = [len(w) for w in words]
    ling = infer(duration.linguistic, **duration.tokens(phones),
                 word_div=row(word_div, np.int64), word_dur=row(lengths, np.int64))
    pred = infer(duration.dur, **ling, ph_midi=row(np.repeat(tones, word_div), np.int64))
    onsets = line.get('onsetMs')
    if onsets is not None and len(onsets) != len(line['notes']):
        raise ValueError(f"onsetMs must have one duration per syllable: {line['text']}")
    ph_dur = fit_phones(words, lengths, pred['ph_dur_pred'][0], onsets)
    frames = int(lengths.sum())
    zeros = np.zeros((1, frames), np.float32)
    def encode(model):
        return infer(model.linguistic, **model.tokens(phones), ph_dur=ph_dur)['encoder_out']
    contour = infer(pitch.pitch, encoder_out=encode(pitch), ph_dur=ph_dur,
                    note_midi=row(tones, np.float32), note_dur=row(lengths, np.int64),
                    note_rest=row(rests, bool), pitch=zeros, expr=np.full_like(zeros, .93),
                    retake=np.ones((1, frames), bool), steps=np.int64(20))['pitch_pred']
    dynamics = infer(variance.variance, encoder_out=encode(variance), ph_dur=ph_dur,
                     pitch=contour, breathiness=zeros, voicing=zeros,
                     retake=np.ones((1, frames, 2), bool), steps=np.int64(16))
    f0 = (440 * np.exp2((contour - 69) / 12)).astype(np.float32)
    mel = infer(acoustic.acoustic, **acoustic.tokens(phones), durations=ph_dur, f0=f0,
                breathiness=dynamics['breathiness_pred'], voicing=dynamics['voicing_pred'],
                gender=zeros, velocity=np.ones_like(zeros), depth=np.float32(.6),
                steps=np.int64(28))['mel']
    audio = infer(vocoder.model, mel=mel, f0=f0)['waveform'].ravel()
    if not np.isfinite(audio).all() or np.max(np.abs(audio)) < .001:
        raise ValueError('The voicebank produced a silent or non-finite phrase.')
    # The fade lies inside the model's padded silence. Preserve the sung release.
    fade = np.linspace(0, 1, min(len(audio) // 2, round(.016 * RATE)))
    audio[:len(fade)] *= fade
    audio[-len(fade):] *= fade[::-1]
    return start * HOP, audio


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('bank', type=Path)
    ap.add_argument('vocoder', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--line', type=int, help='Render one numbered lyric line for audition')
    args = ap.parse_args()
    score = read_score()
    if args.line is not None and not 1 <= args.line <= len(score['lines']):
        ap.error('line is outside this score')
    cfg = ort.SessionOptions()
    cfg.intra_op_num_threads = 6
    cfg.inter_op_num_threads = 1
    ort.set_seed(2591)
    duration = ModelSet(args.bank / 'dsdur', 'dsconfig.yaml', ['linguistic','dur'], cfg)
    pitch = ModelSet(args.bank / 'dspitch', 'dsconfig.yaml', ['linguistic','pitch'], cfg)
    variance = ModelSet(args.bank / 'dsvariance', 'dsconfig.yaml', ['linguistic','variance'], cfg)
    acoustic = ModelSet(args.bank, 'dsconfig.yaml', ['acoustic'], cfg)
    vocoder = ModelSet(args.vocoder, 'vocoder.yaml', ['model'], cfg)
    needed = {w for line in score['lines'] for w in line['pinyin'].split()}
    dictionary = pronunciations(args.bank / 'dsdur' / 'dsdict-zh.yaml', needed)
    take = np.zeros(round(score['duration'] * RATE), np.float32)
    for index, line in enumerate(score['lines'], 1):
        if args.line is not None and index != args.line:
            continue
        start, data = render_line(line, score['beat'], dictionary, duration, pitch, variance, acoustic, vocoder)
        if start < 0:
            data = data[-start:]
            start = 0
        n = min(len(data), len(take) - start)
        take[start:start + n] += data[:n]
        print(f'{index}: {line["text"]} ({len(data)/RATE:.2f}s with padding)', flush=True)
    take *= min(1., .98 / np.max(np.abs(take)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(args.output), 'wb') as f:
        f.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        f.writeframes(np.rint(take * 32767).astype('<i2').tobytes())


if __name__ == '__main__':
    main()

