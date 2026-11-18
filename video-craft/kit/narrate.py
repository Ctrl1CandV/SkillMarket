"""Render Mandarin or other Edge neural voices into one take per cue.

Accepts {"id": "spoken line", ...} or a product spot.json with voice entries.
Requires edge-tts and FFmpeg. For local/private recordings, supply your own WAVs
directly to the example; this helper sends only the requested lines to Microsoft.
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

RATE = 24000
FFMPEG = os.getenv("VC_FFMPEG", "ffmpeg")


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


def trimmed_pcm(mp3):
    # Trim only silence at the outer edges. Preserve breaths, decay, and all
    # interior pauses instead of gating or reversing an entire performance.
    raw = subprocess.check_output([FFMPEG, "-nostdin", "-v", "error", "-i", str(mp3),
                                   "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"])
    samples = array("h")
    samples.frombytes(raw)
    if sys.byteorder == "big":
        samples.byteswap()
    width = RATE // 100
    active = []
    for i in range(0, len(samples), width):
        block = samples[i:i+width]
        if sum(x*x for x in block) > len(block) * (32768 * 10**(-54/20))**2:
            active.append(i)
    if not active:
        raise ValueError("Received silent audio")
    start = max(0, active[0] - 6*width)
    end = min(len(samples), active[-1] + 17*width)
    return raw[start*2:end*2]


async def render(cues, destination, voice, rate, extension="wav"):
    try:
        import edge_tts
    except ImportError:
        raise SystemExit("Install edge-tts in this Python environment, or supply recorded takes.")
    destination.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination) as scratch:
        temp = Path(scratch)
        ready = temp / "ready"
        ready.mkdir()
        for key, line in cues.items():
            source = temp / "received.mp3"
            for attempt in range(3):
                try:
                    await edge_tts.Communicate(line, voice, rate=rate).save(str(source))
                    pcm = trimmed_pcm(source)
                    break
                except (OSError, RuntimeError, edge_tts.exceptions.EdgeTTSException) as error:
                    if attempt == 2:
                        raise RuntimeError(f"Voice request failed at cue {key}: {error}") from error
                    await asyncio.sleep(1.5 * (attempt+1))
            wav = temp / "take.wav"
            with wave.open(str(wav), "wb") as w:
                w.setparams((1, 2, RATE, 0, "NONE", ""))
                w.writeframes(pcm)
            result = ready / (key+"."+extension)
            if extension == "wav":
                wav.replace(result)
            else:
                subprocess.run([FFMPEG, "-nostdin", "-v", "error", "-y", "-i", str(wav),
                                "-c:a", "libmp3lame", "-b:a", "128k", str(result)], check=True)
            print(f"{key}: {len(pcm)/(RATE*2):.2f}s", flush=True)
        # Commit takes only after every line has downloaded and decoded.
        for key in cues:
            name = key+"."+extension
            # A move straight out of TemporaryDirectory retains its private
            # Windows ACL. Create the final inode alongside the user's media.
            with NamedTemporaryFile(dir=destination, delete=False) as sibling:
                staged = Path(sibling.name)
            try:
                shutil.copyfile(ready / name, staged)
                staged.replace(destination / name)
            finally:
                staged.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    parser.add_argument("--rate", default="+0%", help="e.g. --rate=-5%%")
    parser.add_argument("--format", choices=["wav", "mp3"], default="wav")
    args = parser.parse_args()
    asyncio.run(render(read_cues(args.script), args.output, args.voice, args.rate, args.format))

