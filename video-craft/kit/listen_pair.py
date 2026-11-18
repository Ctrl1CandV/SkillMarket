"""Compare two passages at matched loudness. Output contains A, 0.8 s of silence, B.

python listen_pair.py old.mp4 12.1 16.8 new.mp4 10.5 15.4 compare.wav
Needs Python 3 and FFmpeg. The inputs can have different speaking rates.
"""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave

FFMPEG = os.environ.get("VC_FFMPEG", "ffmpeg")


def ffmpeg(*args):
    return subprocess.run(
        [FFMPEG, "-nostdin", "-hide_banner", "-nostats", *map(str, args)],
        check=True, capture_output=True, encoding="utf-8", errors="replace",
    )


def passage(source, start, end, dest):
    if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end):
        raise ValueError(f"Invalid passage {start}–{end} s")
    ffmpeg("-v", "error", "-i", source, "-map", "0:a:0", "-af",
           f"aresample=48000,asetpts=PTS-STARTPTS,atrim=start={start}:end={end}",
           "-ar", "48000", "-ac", "2", "-c:a", "pcm_f32le", dest)
    report = ffmpeg("-i", dest, "-af", "loudnorm=print_format=json", "-f", "null", "-").stderr
    # FFmpeg emits the loudnorm measurement as the last JSON object in its log.
    levels = json.loads(report[report.rindex("{"):report.rindex("}") + 1])
    loudness, peak = float(levels["input_i"]), float(levels["input_tp"])
    if not (math.isfinite(loudness) and math.isfinite(peak)):
        raise ValueError(f"Cannot match levels for {source.name} at {start}–{end} s. Choose a longer passage containing voice.")
    return loudness, peak


def compare(args):
    output = args.output.resolve()
    if output.suffix.lower() != ".wav" or output in (args.first.resolve(), args.second.resolve()):
        raise ValueError("Choose a separate .wav output path")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as work:
        temp = Path(work)
        sources = [(args.first, args.start_a, args.end_a), (args.second, args.start_b, args.end_b)]
        levels = [passage(src, start, end, temp / f"{i}.wav") for i, (src, start, end) in enumerate(sources)]
        # One constant gain per passage. Keep both below -1.5 dBTP without a limiter.
        target = min(-18.0, *(loudness - peak - 1.5 for loudness, peak in levels))
        result = temp / "pair.wav"
        with wave.open(str(result), "wb") as joined:
            joined.setparams((2, 2, 48000, 0, "NONE", ""))
            for i, ((loudness, _), (_, start, end)) in enumerate(zip(levels, sources)):
                piece = temp / f"gain-{i}.wav"
                ffmpeg("-v", "error", "-i", temp / f"{i}.wav", "-af", f"volume={target-loudness:.4f}dB",
                       "-c:a", "pcm_s16le", piece)
                with wave.open(str(piece), "rb") as wav:
                    seconds = wav.getnframes() / wav.getframerate()
                    if abs(seconds - (end-start)) > 0.01:
                        raise ValueError(f"Passage {i+1} extends past the available audio ({seconds:.3f} s decoded)")
                    if i:
                        joined.writeframes(bytes(round(0.8 * 48000) * 4))
                    print(f"{'AB'[i]} {start:g}–{end:g} s, {loudness:.1f} LUFS, gain {target-loudness:+.1f} dB")
                    joined.writeframes(wav.readframes(wav.getnframes()))
        # A move out of the private work directory retains its Windows ACL.
        with tempfile.NamedTemporaryFile(suffix=".wav", dir=output.parent, delete=False) as temp_file:
            staged = Path(temp_file.name)
        try:
            shutil.copyfile(result, staged)
            staged.replace(output)
        finally:
            staged.unlink(missing_ok=True)
    print(f"B starts at {args.end_a-args.start_a+0.8:.2f} s in {output.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("first", "second"):
        parser.add_argument(key, type=Path)
        label = "a" if key == "first" else "b"
        parser.add_argument("start_" + label, type=float)
        parser.add_argument("end_" + label, type=float)
    parser.add_argument("output", type=Path)
    try:
        compare(parser.parse_args())
    except subprocess.CalledProcessError as exc:
        parser.exit(1, (exc.stderr or str(exc)) + "\n")
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")

