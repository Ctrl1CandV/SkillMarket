"""Build the demo master from the note sheet and Mandarin syllable recordings.

Usage (in this folder): python make-song.py path/to/units path/to/output
Requires numpy, Node and FFmpeg. No speech or music service is used.
"""
import json
import math
from pathlib import Path
import subprocess
import sys
import wave

import numpy as np


def read_unit(path):
    with wave.open(str(path), 'rb') as wav:
        if (wav.getnchannels(), wav.getsampwidth()) != (1, 2):
            raise ValueError(f'{path}: expected mono 16-bit PCM')
        rate = wav.getframerate()
        unit = np.frombuffer(wav.readframes(wav.getnframes()), '<i2').astype(float) / 32768
    loud = np.flatnonzero(abs(unit) > .004)
    if not len(loud):
        raise ValueError(f'{path}: silent unit')
    padding = round(.016 * rate)
    unit = unit[max(0, loud[0] - padding):loud[-1] + padding]
    return rate, unit / max(abs(unit))


def vocal_period(signal, middle, rate):
    # The first strong normalized autocorrelation peak avoids an octave error on a harmonic.
    width = round(.026 * rate)
    data = signal[max(0, middle-width):middle+width]
    if len(data) < width or np.mean(data*data) < .00035:
        return None
    periods = np.arange(round(rate/490), min(len(data)//2, round(rate/68)))
    corr = np.array([np.dot(data[:-p], data[p:]) / max(1e-10,
                    np.linalg.norm(data[:-p]) * np.linalg.norm(data[p:])) for p in periods])
    peaks = np.flatnonzero((corr[1:-1] >= corr[:-2]) & (corr[1:-1] > corr[2:])) + 1
    good = [i for i in peaks if corr[i] > max(.54, .83 * max(corr))]
    return int(periods[good[0]]) if good else None


def sing(unit, rate, seconds, frequency):
    centers = np.arange(round(.012*rate), len(unit)-round(.012*rate), round(.006*rate))
    measured = [(c, vocal_period(unit, c, rate)) for c in centers]
    voiced = [(c, p) for c, p in measured if p]
    if not voiced:
        raise ValueError('No pitched vowel found in the source syllable')
    times, periods = np.array(voiced).T
    first, last = int(times[0]), int(times[-1])
    if last-first < .030*rate:
        raise ValueError('Cannot sustain this sample; record a longer, steady vowel.')
    # Follow the same periodic peak from pulse to pulse. Leave the initial consonant alone.
    initial = int(periods[0])
    mark = first + int(np.argmax(unit[first:first+initial]))
    marks = []
    while mark <= last:
        period = round(np.interp(mark, times, periods))
        marks.append((mark, period))
        expected = mark + period
        radius = max(2, round(.20*period))
        section = unit[expected-radius:expected+radius+1]
        if not len(section):
            break
        mark = expected-radius + int(np.argmax(section))
    locations = np.array([m[0] for m in marks])
    length = round(seconds * rate)
    out, weight = np.zeros(length), np.zeros(length)
    end = min(len(unit) - last, round(.09*rate))
    target_end = length-end
    # Stretch the interior of the vowel; keep the diphthong movement and final nasal on the release.
    voiced_len = last-first
    attack = min(round(.055*rate), int(voiced_len*.22))
    release = min(round(.085*rate), int(voiced_len*.26))
    anchor_out = [first, first+attack, target_end-release, target_end]
    anchor_src = [first, first+attack, last-release, last]
    dest = float(first)
    while dest < target_end:
        at = np.interp(dest, anchor_out, anchor_src)
        j = int(np.searchsorted(locations, at))
        if j and (j == len(marks) or at-locations[j-1] < locations[j]-at):
            j -= 1
        source, radius = marks[j]
        dt = (dest-first)/rate
        vibrato = .028 * min(1, max(0, (dt-.15)*3)) * math.sin(2*math.pi*5.1*dt)
        glide = -.060*math.exp(-dt/.035)
        period = rate / (frequency * (1+vibrato+glide))
        center = round(dest)
        offsets = np.arange(-radius, radius+1)
        valid = ((center+offsets >= 0) & (center+offsets < length)
                 & (source+offsets >= 0) & (source+offsets < len(unit)))
        offsets = offsets[valid]
        win = .5+.5*np.cos(np.pi*offsets/radius)
        out[center+offsets] += unit[source+offsets]*win
        weight[center+offsets] += win
        dest += period
    out /= np.maximum(.6, weight)
    cross = min(first, round(.009*rate))
    out[:first-cross] = unit[:first-cross]
    blend = np.linspace(0, 1, cross)
    out[first-cross:first] = (1-blend)*unit[first-cross:first]+blend*out[first-cross:first]
    if end:
        # Add the actual tail from the release (this can contain aspiration as well as pitch).
        blend = np.minimum(1, np.arange(end)/max(1,cross))
        out[-end:] = out[-end:]*(1-blend)+unit[last:last+end]*blend
    out *= np.minimum(1, np.arange(length)/(.007*rate))
    out *= np.minimum(1, np.arange(length)[::-1]/(.030*rate))
    return out/np.maximum(max(abs(out)), .1)


RATE = 44100
TRANSPOSE = -3


def hz(midi):
    return 440 * 2 ** ((midi+TRANSPOSE-69)/12)


def put(track, at, mono, amp=1., pan=0.):
    index = round(at*RATE)
    n = min(len(mono), len(track)-index)
    if n > 0:
        track[index:index+n] += mono[:n, None]*amp*np.array([math.cos((pan+1)*math.pi/4),
                                                              math.sin((pan+1)*math.pi/4)])


def pluck(midi, length, mellow=False):
    t = np.arange(round(length*RATE))/RATE
    freq = hz(midi)
    sig = np.zeros(len(t))
    for k, amount in enumerate([1., .39, .16, .11, .05, .026], 1):
        sig += amount*np.sin(2*np.pi*freq*k*(1+.000045*k*k)*t) * np.exp(-t*(1.6+.78*k))
    return sig*np.minimum(1,t/(.012 if mellow else .005))*np.minimum(1,t[::-1]/.06)


def write(path, data):
    with wave.open(str(path), 'wb') as output:
        output.setparams((2,2,RATE,0,'NONE','not compressed'))
        output.writeframes((np.clip(data,-.999,.999)*32767).astype('<i2').tobytes())


def build(folder, output):
    show = "import {beat,duration,lines,chords} from './song.mjs';console.log(JSON.stringify({beat,duration,lines,chords}))"
    chart = json.loads(subprocess.check_output(['node','--input-type=module','-e',show], cwd=Path(__file__).parent))
    beat, duration = chart['beat'], chart['duration']
    voice = np.zeros((round(duration*RATE), 2))
    music = np.zeros_like(voice)
    rng = np.random.default_rng(707)
    for line in chart['lines']:
        for character, start, length, midi in line['notes']:
            rate, sample = read_unit(folder / f'{ord(character)}.wav')
            syllable = sing(sample,rate,length*beat,hz(midi))
            hi = np.arange(round(len(syllable)*RATE/rate))*rate/RATE
            vocal = np.interp(hi, np.arange(len(syllable)), syllable)
            put(voice,beat*start,vocal,.72)
    # An early stereo room reflection keeps sustained notes attached to the drawing's space.
    direct = voice.copy()
    for delay, gain, channel in [(.046,.12,0),(.068,.11,1),(.111,.072,0),(.149,.065,1),(.200,.045,0),(.252,.035,1)]:
        n = round(delay*RATE)
        voice[n:,channel] += direct[:-n,channel]*gain
    for bar, chord in enumerate(chart['chords']):
        start = bar*4
        for j, step in enumerate([0.,.52,1.52,2.,2.78,3.50]):
            if start+step >= chart['duration']/beat-.7:
                continue
            note = chord[[1,2,3,1,2,3][j]]+12
            put(music,(start+step)*beat,pluck(note,1.5),[.13,.105,.08,.095,.09,.07][j],-.45+.16*(j%3))
        for j in (0,2):
            t = np.arange(round(beat*1.8*RATE))/RATE
            base = hz(chord[0]-(12 if j==0 else 5))
            bass = (np.sin(2*np.pi*base*t)+.27*np.sin(4*np.pi*base*t))
            put(music,(start+j)*beat,bass*(1-np.exp(-t*65))*np.exp(-t*3)*np.minimum(1,t[::-1]/.08),.23)
        if 2 <= bar < 9:
            for pulse in range(8):
                hit = np.arange(round(.14*RATE))/RATE
                noise = rng.normal(0,1,len(hit))
                brush = np.diff(np.r_[0,noise])*np.exp(-hit*(28 if pulse in (2,6) else 75))
                put(music,(start+pulse/2+.022*(pulse%2))*beat,brush,.022 if pulse in (2,6) else .010,.31)
        if bar in (0,5,6,8):
            for j, n in enumerate(chord[1:]):
                put(music,(start+.07*j)*beat,pluck(n+24,1.70,True),.065,.54)
    endfade = np.minimum(1,np.arange(len(music))[::-1]/(.65*RATE))
    music *= endfade[:,None]
    # The pluck and brush start on some of the same beats as fricatives. Make room for their onsets.
    duck = np.ones(len(music))
    for line in chart['lines']:
        for _, start, length, _ in line['notes']:
            start_sample = max(0,round((start*beat-.028)*RATE))
            t = np.arange(round((length*beat+.14)*RATE))/RATE
            depth = (.33+.23*np.exp(-t/.20))*np.minimum(1,t/.026)*np.minimum(1,t[::-1]/.14)
            n = min(len(t),len(duck)-start_sample)
            duck[start_sample:start_sample+n] = np.minimum(duck[start_sample:start_sample+n],1-depth[:n])
    music *= duck[:,None]
    output.mkdir(parents=True,exist_ok=True)
    write(output/'vocal.wav',voice)
    write(output/'backing.wav',music)
    write(output/'mix.wav',(voice+music)*.74)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(output/'mix.wav'),
                    '-af','loudnorm=I=-16:TP=-1.6:LRA=11','-ar','48000',
                    '-c:a','libopus','-b:a','112k',str(output/'song.ogg')],check=True)


if __name__ == '__main__':
    build(Path(sys.argv[1]),Path(sys.argv[2]))
