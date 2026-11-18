"""Compare the supplied master with the delivered MV; requires ffmpeg and NumPy."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import subprocess

import numpy as np


def read_audio(path):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path),
                                   "-map", "0:a:0", "-ar", "12000", "-ac", "2",
                                   "-f", "f32le", "pipe:1"])
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2)


def audio_timeline(path):
    probe = ["ffprobe", "-v", "error", "-of", "json"]
    audio = json.loads(subprocess.check_output([
        *probe, "-select_streams", "a:0", "-show_packets", "-show_data_hash", "sha256",
        "-show_entries", "packet=data_hash,pts,duration:stream=time_base,start_pts,duration_ts:format=start_time",
        str(path)]))
    video = json.loads(subprocess.check_output([
        *probe, "-select_streams", "V:0", "-show_entries", "stream=time_base,start_pts", str(path)]))
    stream, packets = audio["streams"][0], audio["packets"]
    tick = float(Fraction(stream["time_base"]))
    pts = np.array([int(p["pts"]) for p in packets], dtype=np.float64) * tick
    container_start = float(audio["format"].get("start_time", 0))
    audio_start = int(stream["start_pts"]) * tick if "start_pts" in stream else pts[0]
    # Some demuxers omit a packet's duration. Its next PTS (or the audio stream end) bounds it.
    stream_end = audio_start + float(stream.get("duration_ts", "nan")) * tick
    intervals = np.diff(pts, append=stream_end)
    durations = np.array([int(packet["duration"]) * tick if "duration" in packet else interval
                          for packet, interval in zip(packets, intervals)])
    if not np.isfinite(durations).all():
        raise ValueError(f"Cannot establish the final audio packet duration in {path}")
    picture_start = container_start
    if video["streams"]:
        picture = video["streams"][0]
        picture_start = int(picture["start_pts"]) * float(Fraction(picture["time_base"]))
    return {"hashes": [p["data_hash"] for p in packets], "tick": tick,
            "pts": pts - container_start, "durations": durations,
            "audio_from_container": audio_start - container_start,
            "audio_from_picture": audio_start - picture_start}


def compare_timing(source, film):
    # A different stream time base can round packet times by one tick at remux.
    tolerance = 1e-6  # ffprobe reports the container origin in microseconds
    if source["tick"] != film["tick"]:
        tolerance += min(0.001, max(source["tick"], film["tick"]))
    pts_delta = duration_delta = None
    if len(source["pts"]) == len(film["pts"]):
        pts_delta = float(np.max(np.abs(film["pts"] - source["pts"])))
        duration_delta = float(np.max(np.abs(film["durations"] - source["durations"])))
    container_offset = film["audio_from_container"] - source["audio_from_container"]
    picture_offset = film["audio_from_picture"] - source["audio_from_picture"]
    matches = (pts_delta is not None and pts_delta <= tolerance and duration_delta <= tolerance
               and abs(container_offset) <= tolerance and abs(picture_offset) <= tolerance)
    return {"audio_timeline_matches": bool(matches), "timing_tolerance_seconds": tolerance,
            "maximum_packet_pts_delta_seconds": pts_delta, "maximum_packet_duration_delta_seconds": duration_delta,
            "audio_start_delta_from_container_seconds": float(container_offset),
            "audio_start_delta_from_picture_seconds": float(picture_offset)}


def best_offset(source, film):
    # Use an energetic one-second passage so a silent intro cannot determine alignment.
    width, margin = 12000, 6000
    starts = range(margin, min(len(source), len(film)) - width - margin, width)
    if not starts:
        raise ValueError("Need more than two seconds of audio on each side to check alignment")
    start = max(starts, key=lambda i: np.mean(source[i:i + width] ** 2))
    needle = source[start:start + width].mean(axis=1)
    window = film[start - margin:start + width + margin].mean(axis=1)
    n = 1 << (len(window) + width - 1).bit_length()
    corr = np.fft.irfft(np.fft.rfft(window, n) * np.fft.rfft(needle[::-1], n), n)
    return int(np.argmax(corr[width - 1:len(window)])) - margin


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path)
    parser.add_argument("film", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    source, final = read_audio(args.master), read_audio(args.film)
    master_timeline, film_timeline = audio_timeline(args.master), audio_timeline(args.film)
    ident = master_timeline["hashes"] == film_timeline["hashes"]
    timing = compare_timing(master_timeline, film_timeline)
    lag = best_offset(source, final)
    a, b = source[max(0, -lag):], final[max(0, lag):]
    length = min(len(a), len(b))
    scores = []
    for i in range(0, length, 36000):
        x = a[i:min(i + 36000, length)].astype(np.float64)
        y = b[i:min(i + 36000, length)].astype(np.float64)
        strength = np.linalg.norm(x)
        if strength > 1e-4 * np.sqrt(x.size):
            corr = np.sum(x * y) / max(1e-12, strength * np.linalg.norm(y))
            scores.append(float(np.clip(corr, -1, 1)))
    lowest = min(scores) if scores else None
    same_recording = (ident and timing["audio_timeline_matches"] and len(source) == len(final) and lag == 0
                      and lowest is not None and lowest >= 1 - 1e-6)
    report = {"passed": same_recording, "identical_audio_packets": ident, **timing, "analysis_rate": 12000,
              "source_seconds": len(source) / 12000, "film_audio_seconds": len(final) / 12000,
              "film_offset_samples": lag, "film_offset_seconds": lag / 12000,
              "three_second_windows": len(scores), "minimum_window_correlation": lowest,
              "median_window_correlation": float(np.median(scores)) if scores else None}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    if not same_recording:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
