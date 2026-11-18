"""Attach a complete song to a finished picture, preserving the original performance.

python mux_original.py picture.mp4 master.m4a final.mp4
AAC, MP3 and ALAC are copied to MP4. Other source codecs are encoded to AAC once.
"""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

FFMPEG = os.environ.get("VC_FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("VC_FFPROBE") or str(Path(FFMPEG).with_name(
    "ffprobe" + Path(FFMPEG).suffix))


def probe(path, selector):
    cmd = [FFPROBE, "-v", "error", "-select_streams", selector, "-show_entries",
           "stream=codec_name,duration,avg_frame_rate:format=duration", "-of", "json", str(path)]
    report = json.loads(subprocess.check_output(cmd))
    if not report["streams"]:
        raise ValueError(f"No {selector} stream in {path}")
    stream = report["streams"][0]
    seconds = float(stream.get("duration") or report["format"]["duration"])
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError(f"No usable duration in {path}")
    return stream, seconds


def mux(picture, master, output):
    if output.suffix.lower() != ".mp4" or output.resolve() in (picture.resolve(), master.resolve()):
        raise ValueError("Choose a separate .mp4 output path")
    video, video_sec = probe(picture, "V:0")
    audio, song_sec = probe(master, "a:0")
    num, den = map(float, video["avg_frame_rate"].split("/"))
    if num <= 0 or den <= 0:
        raise ValueError("Picture frame rate is missing")
    frame = den / num
    if abs(video_sec - song_sec) > frame + 0.002:
        raise ValueError(f"Picture {video_sec:.3f} s, song {song_sec:.3f} s. "
                         "Render the picture to the full song length (within one frame), then retry.")
    copy_audio = audio["codec_name"] in {"aac", "mp3", "alac"}
    acodec = ["-c:a", "copy"] if copy_audio else ["-c:a", "aac", "-b:a", "256k"]
    output.parent.mkdir(parents=True, exist_ok=True)
    # A sibling inherits the delivery folder's ACLs on Windows.
    with tempfile.NamedTemporaryFile(suffix=".mp4", dir=output.parent, delete=False) as temp:
        joined = Path(temp.name)
    try:
        subprocess.run([FFMPEG, "-nostdin", "-v", "error", "-y", "-i", str(picture), "-i", str(master),
                        "-map", "0:V:0", "-map", "1:a:0", "-map_metadata", "-1",
                        "-c:v", "copy", *acodec, "-movflags", "+faststart", str(joined)], check=True)
        _, final_sec = probe(joined, "a:0")
        if abs(final_sec - song_sec) > max(frame, 0.05):
            raise ValueError(f"Muxed audio duration {final_sec:.3f} s differs from source {song_sec:.3f} s")
        joined.replace(output)
    finally:
        joined.unlink(missing_ok=True)
    mode = "original audio packets copied" if copy_audio else f"{audio['codec_name']} encoded once to AAC"
    print(f"{song_sec:.3f} s · {mode} · {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("picture", "master", "output"):
        parser.add_argument(key, type=Path)
    args = parser.parse_args()
    try:
        mux(args.picture, args.master, args.output)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + "\n")

