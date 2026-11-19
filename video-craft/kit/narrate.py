"""Render narration, one WAV per cue, in one consistent voice.

    python narrate.py cues.json voice/ [--voice teacher] [--takes 3] [--engine voxcpm|edge]

cues.json is {"id": "spoken line", ...} or a spot.json with a "voice" list of {"id", "words"}.

Engines
  voxcpm  local VoxCPM (pip install voxcpm; GPU recommended). Every cue clones the same voice card, so the
          whole film has one speaker. --voice names a card in kit/voices/ (teacher, promo, story) or points
          to your own WAV with a .txt transcript beside it. With VoxCPM2 you can instead describe a voice:
          --design "一位三十岁左右的女性，声音温暖，语速从容". Model: --model or VC_VOXCPM (a local folder or
          a Hugging Face id); default openbmb/VoxCPM1.5.
  edge    Microsoft's online voices through edge-tts (sends the lines to Microsoft). Flatter, used as a
          fallback when VoxCPM is not installed. --voice zh-CN-XiaoxiaoNeural etc.

--takes N renders N versions of each line and keeps the best: the one whose transcript matches the script
(needs faster-whisper; VC_WHISPER may point to a local model) with no long gap inside and a length close
to the others. Without faster-whisper it keeps the take with the fewest long gaps.
Write lines the way they are said: "十五分钟" not "15 分钟", "七点一刻" not "19:15".
"""
import argparse
from array import array
import asyncio
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import NamedTemporaryFile, TemporaryDirectory
import wave

FFMPEG = os.getenv("VC_FFMPEG", "ffmpeg")
VOICES = Path(__file__).resolve().parent / "voices"


def read_cues(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError('Expected a JSON object mapping cue ids to text, or a spot.json with a voice list.')
    rows = ([(item["id"], item["words"]) for item in data["voice"]]
            if isinstance(data.get("voice"), list) else list(data.items()))
    cues = {}
    filenames = set()
    for key, text in rows:
        if (not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", key)
                or re.fullmatch(r"CON|PRN|AUX|NUL|(?:COM|LPT)[1-9]", key, re.I)):
            raise ValueError(f"Use a filename-safe cue id, got {key!r}")
        if key.casefold() in filenames or not isinstance(text, str) or not text.strip():
            raise ValueError(f"Duplicate or empty speech cue: {key}")
        filenames.add(key.casefold())
        cues[key] = text.strip()
    if not cues:
        raise ValueError("No speech cues in the input file")
    return cues


def pcm16(samples):
    """float list/array in -1..1 → bytes of little-endian int16"""
    out = array("h", (max(-32768, min(32767, int(round(x * 32767)))) for x in samples))
    if sys.byteorder == "big":
        out.byteswap()
    return out.tobytes()


def trim(raw, rate, below_peak_db=40, floor_db=-60):
    """Trim the outer edges only, keeping every pause inside the line. "Silence" is anything 40 dB under the
    loudest 10 ms of the take (generated takes often start with a soft breath or hiss that a fixed floor keeps,
    which makes captions lead the voice). Returns (pcm bytes, longest inner gap in seconds)."""
    s = array("h")
    s.frombytes(raw)
    if sys.byteorder == "big":
        s.byteswap()
    width = rate // 100
    power = [sum(x * x for x in s[i:i + width]) / max(1, len(s[i:i + width])) for i in range(0, len(s), width)]
    if not power or max(power) <= 0:
        raise ValueError("silent take")
    thresh = max(max(power) * 10 ** (-below_peak_db / 10), (32768 * 10 ** (floor_db / 20)) ** 2)
    active = [k * width for k, p in enumerate(power) if p > thresh]
    if not active:
        raise ValueError("silent take")
    gaps = [(b - a) / rate for a, b in zip(active, active[1:])]
    start, end = max(0, active[0] - 6 * width), min(len(s), active[-1] + 17 * width)
    return raw[start * 2:end * 2], max(gaps, default=0)


def write_wav(path, pcm, rate):
    with wave.open(str(path), "wb") as w:
        w.setparams((1, 2, rate, 0, "NONE", ""))
        w.writeframes(pcm)


# ---------------------------------------------------------------- choosing among takes
def guess_language(texts):
    """zh when the script is mostly Chinese characters, else en (override with --language)."""
    joined = "".join(texts)
    han = len(re.findall(r"[一-鿿]", joined))
    letters = len(re.findall(r"[A-Za-z]", joined))
    return "zh" if han >= letters else "en"


def plain(s, language):
    s = s.lower()
    if language == "zh":
        # recognisers write numbers as digits; compare them as Chinese numerals so "5号" matches "五号"
        s = s.translate(str.maketrans("0123456789", "零一二三四五六七八九"))
    return re.sub(r"[^\w]", "", s)


def char_errors(ref, hyp, language):
    ref, hyp = plain(ref, language), plain(hyp, language)
    d = list(range(len(hyp) + 1))
    for i, a in enumerate(ref, 1):
        prev, d[0] = d[0], i
        for j, b in enumerate(hyp, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (a != b))
    return d[-1] / max(1, len(ref))


def transcribe_all(job):
    """Runs in its own process: faster-whisper and torch in one process crash on Windows (two CUDA/OpenMP runtimes)."""
    from faster_whisper import WhisperModel
    data = json.loads(Path(job).read_text(encoding="utf-8"))
    model = WhisperModel(os.getenv("VC_WHISPER", "large-v3-turbo"), device="cpu", compute_type="int8")
    out = {}
    for item in data["takes"]:
        segs, _ = model.transcribe(item["path"], language=data["language"], beam_size=5, vad_filter=False,
                                   initial_prompt="以下是普通话的句子。" if data["language"] == "zh" else None)
        out[item["path"]] = "".join(x.text for x in segs)
    Path(job).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")


def heard(rendered, temp, language):
    """{take path: transcript} or {} when faster-whisper is unavailable"""
    job = temp / "transcribe.json"
    job.write_text(json.dumps({"language": language, "takes": [
        {"path": str(path)} for _, _, takes, _ in rendered for path, _, _ in takes]}), encoding="utf-8")
    run = subprocess.run([sys.executable, __file__, "--transcribe", str(job)], capture_output=True, text=True)
    if run.returncode:
        last = (run.stderr.strip().splitlines() or ["unknown error"])[-1]
        print(f"(no transcript check: {last}; choosing takes by pauses and length)", flush=True)
        return {}
    return json.loads(job.read_text(encoding="utf-8"))


def pick(takes, text, transcripts, language):
    """takes: [(path, seconds, longest_gap)] → index of the best: right words first, then no odd pause,
    then (with three or more takes) a length close to the typical one — an unusually long or short take
    is often a stumble or a rushed read."""
    if len(takes) == 1:
        return 0
    lens = sorted(t[1] for t in takes)
    median = lens[len(lens) // 2]
    scores = []
    for path, secs, gap in takes:
        err = char_errors(text, transcripts[str(path)], language) if str(path) in transcripts else 0.0
        typical = abs(secs - median) / median if len(takes) >= 3 else 0.0
        scores.append(err * 4 + max(0.0, gap - 0.7) + typical)
        note = f", transcript error {err:.0%}" if transcripts else ""
        print(f"    {path.name}: {secs:.2f} s, longest pause {gap:.2f} s{note}", flush=True)
    return min(range(len(takes)), key=scores.__getitem__)


# ---------------------------------------------------------------- engines
def find_card(voice):
    p = Path(voice)
    if p.suffix.lower() != ".wav":
        p = VOICES / f"{voice}.wav"
    txt = p.with_suffix(".txt")
    if not p.exists() or not txt.exists():
        names = ", ".join(sorted(x.stem for x in VOICES.glob("*.wav"))) or "none"
        raise SystemExit(f"No voice card {voice!r}. Cards in kit/voices: {names}; or pass a WAV with a .txt beside it.")
    return p, txt.read_text(encoding="utf-8").strip()


def voxcpm_takes(cues, temp, args):
    try:
        import torch
        from voxcpm import VoxCPM
    except ImportError:
        raise SystemExit("VoxCPM is not installed here (pip install voxcpm). Use --engine edge, or supply recorded takes.")
    model_id = args.model or os.getenv("VC_VOXCPM") or "openbmb/VoxCPM1.5"
    model = VoxCPM.from_pretrained(model_id, load_denoiser=False, optimize=False)
    rate = model.tts_model.sample_rate
    if args.design and type(model.tts_model).__name__ != "VoxCPM2Model":
        raise SystemExit("--design needs a VoxCPM2 model (--model openbmb/VoxCPM2); VoxCPM1.5 would read the description aloud.")
    if args.design:
        prompt = {}
        prefix = f"({args.design.strip('()（）')})"
    else:
        card, card_text = find_card(args.voice or "teacher")
        prompt = {"prompt_wav_path": str(card), "prompt_text": card_text}
        prefix = ""
    for key, line in cues.items():
        out = []
        for k in range(args.takes):
            torch.manual_seed(args.seed + k)
            wav = model.generate(text=prefix + line, cfg_value=args.cfg, inference_timesteps=args.steps,
                                 normalize=False, denoise=False, retry_badcase=True, **prompt)
            pcm, gap = trim(pcm16(wav.tolist()), rate)
            path = temp / f"{key}.take{k}.wav"
            write_wav(path, pcm, rate)
            out.append((path, len(pcm) / (2 * rate), gap))
        yield key, line, out, rate


def edge_takes(cues, temp, args):
    try:
        import edge_tts
    except ImportError:
        raise SystemExit("Install edge-tts in this Python environment, or supply recorded takes.")
    rate = 24000
    # a card name (teacher, promo…) means nothing to Edge: fall back to a default voice in the script's language
    fallback = "en-US-AriaNeural" if (args.language or guess_language(cues.values())) == "en" else "zh-CN-XiaoxiaoNeural"
    voice = args.voice if args.voice and "Neural" in args.voice else fallback

    async def one(line, mp3):
        for attempt in range(3):
            try:
                await edge_tts.Communicate(line, voice, rate=args.rate).save(str(mp3))
                return
            except (OSError, RuntimeError, edge_tts.exceptions.EdgeTTSException) as error:
                if attempt == 2:
                    raise RuntimeError(f"Voice request failed: {error}") from error
                await asyncio.sleep(1.5 * (attempt + 1))

    for key, line in cues.items():
        mp3 = temp / "received.mp3"
        asyncio.run(one(line, mp3))
        raw = subprocess.check_output([FFMPEG, "-nostdin", "-v", "error", "-i", str(mp3),
                                       "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"])
        pcm, gap = trim(raw, rate)
        path = temp / f"{key}.take0.wav"
        write_wav(path, pcm, rate)
        yield key, line, [(path, len(pcm) / (2 * rate), gap)], rate


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) == 3 and sys.argv[1] == "--transcribe":
        return transcribe_all(sys.argv[2])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--engine", choices=["voxcpm", "edge"], help="default: voxcpm when installed, else edge")
    ap.add_argument("--voice", help="voxcpm: card name in kit/voices or a WAV path; edge: voice name")
    ap.add_argument("--design", help="VoxCPM2 only: describe the voice instead of cloning a card")
    ap.add_argument("--model", help="VoxCPM model folder or Hugging Face id (or set VC_VOXCPM)")
    ap.add_argument("--takes", type=int, default=1, help="versions per line; the best one is kept")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--cfg", type=float, default=2.0)
    ap.add_argument("--steps", type=int, default=10)
    ap.add_argument("--language", help="zh or en for the transcript check; default: guessed from the script")
    ap.add_argument("--rate", default="+0%", help="edge only, e.g. --rate=-5%%")
    ap.add_argument("--format", choices=["wav", "mp3"], default="wav")
    args = ap.parse_args()

    engine = args.engine
    if not engine:
        try:
            import voxcpm  # noqa: F401
            engine = "voxcpm"
        except ImportError:
            engine = "edge"
            print("VoxCPM not installed: using Microsoft Edge voices (flatter). See references/voice.md.", flush=True)
    cues = read_cues(args.script)
    args.output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=args.output) as scratch:
        temp = Path(scratch)
        ready = []
        source = voxcpm_takes if engine == "voxcpm" else edge_takes
        rendered = list(source(cues, temp, args))
        language = args.language or guess_language(cues.values())
        transcripts = heard(rendered, temp, language) if args.takes > 1 else {}
        for key, line, takes, rate in rendered:
            if len(takes) > 1:
                print(f"{key}:", flush=True)
            best = pick(takes, line, transcripts, language)
            path, secs, gap = takes[best]
            name = f"{key}.{args.format}"
            final = temp / name
            if args.format == "wav":
                shutil.copyfile(path, final)
            else:
                subprocess.run([FFMPEG, "-nostdin", "-v", "error", "-y", "-i", str(path),
                                "-c:a", "libmp3lame", "-b:a", "160k", str(final)], check=True)
            ready.append(name)
            flag = f"  ⚠ {gap:.1f} s pause inside — listen" if gap > 1.0 else ""
            print(f"{key}: {secs:.2f} s{f' (take {best + 1} of {len(takes)})' if len(takes) > 1 else ''}{flag}", flush=True)
        # Commit only after every line rendered. Copy beside the user's media so the file gets normal permissions.
        for name in ready:
            with NamedTemporaryFile(dir=args.output, delete=False) as sibling:
                staged = Path(sibling.name)
            try:
                shutil.copyfile(temp / name, staged)
                staged.replace(args.output / name)
            finally:
                staged.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
