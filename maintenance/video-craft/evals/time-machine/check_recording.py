"""Compare the supplied master with the delivered MV; requires ffmpeg and NumPy."""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np


def read_audio(path):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path),
                                   "-map", "0:a:0", "-ar", "12000", "-ac", "2",
                                   "-f", "f32le", "pipe:1"])
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2)


def packet_hashes(path):
    raw = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "a:0",
                                   "-show_packets", "-show_entries", "packet=data_hash",
                                   "-show_data_hash", "sha256", "-of", "json", str(path)])
    return [p["data_hash"] for p in json.loads(raw)["packets"]]


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
    ident = packet_hashes(args.master) == packet_hashes(args.film)
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
    same_recording = (ident and len(source) == len(final) and lag == 0
                      and lowest is not None and lowest >= 1 - 1e-6)
    report = {"passed": same_recording, "identical_audio_packets": ident, "analysis_rate": 12000,
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
