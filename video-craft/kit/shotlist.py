"""List the shots of a rendered film and flag editing patterns worth a second look.

    python shotlist.py film.mp4 [--song songmap.json [--offset T0]] [--json out/shots.json]

Reports cut times, the spread of shot lengths, runs of shots with the same length, cuts that only enlarge
the previous image, black or white stretches, and stretches where nothing moves. With --song it also says
how far each cut lands from the nearest beat and bar of the recording; a film cut from the middle of the song
needs --offset with the song time of its first frame. Every flag is a question for the
editor, not a verdict: a held shot, a hard cut to black or a push-in can all be right for the piece.
Needs FFmpeg and NumPy.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

FFMPEG = os.getenv("VC_FFMPEG", "ffmpeg")
FFPROBE = os.getenv("VC_FFPROBE") or str(Path(FFMPEG).with_name("ffprobe" + Path(FFMPEG).suffix))
W, H = 128, 72


def probe_fps(path):
    out = subprocess.check_output([FFPROBE, "-v", "error", "-select_streams", "v:0",
                                   "-show_entries", "stream=avg_frame_rate", "-of", "csv=p=0", str(path)], text=True)
    num, _, den = out.strip().split()[0].strip(",").partition("/")
    return float(num) / float(den or 1)


def frames(path):
    raw = subprocess.check_output([FFMPEG, "-nostdin", "-v", "error", "-i", str(path), "-map", "0:v:0",
                                   "-vf", f"scale={W}:{H}:flags=area,format=gray", "-f", "rawvideo", "-"])
    return np.frombuffer(raw, dtype=np.uint8).reshape(-1, H, W).astype(np.float32) / 255


def find_cuts(v, fps):
    diff = np.abs(np.diff(v, axis=0)).mean(axis=(1, 2))
    hist = np.stack([np.histogram(f, bins=16, range=(0, 1))[0] for f in v]).astype(np.float32) / (W * H)
    hdiff = np.abs(np.diff(hist, axis=0)).sum(axis=1) / 2
    score = diff * 4 + hdiff
    cuts = []
    for i in range(len(score)):
        lo, hi = max(0, i - 6), min(len(score), i + 7)
        local = np.median(np.r_[score[lo:i], score[i + 1:hi]]) if hi - lo > 1 else 0
        if score[i] > 0.12 and score[i] > 3.5 * local + 0.04 and score[i] == score[lo:hi].max():
            cuts.append(i + 1)  # first frame of the new shot
    return cuts, diff


def enlarged_from(prev, cur):
    """How well `cur` matches a centred-anywhere crop of `prev` blown up 1.15-2.6x (1 = identical)."""
    def norm(a):
        a = a - a.mean()
        return a / (np.linalg.norm(a) + 1e-6)
    target = norm(cur)
    best = (-1.0, 1.0)
    ys, xs = np.mgrid[0:H, 0:W]
    for s in np.arange(1.15, 2.65, 0.15):
        ch, cw = H / s, W / s
        for cy in np.linspace(ch / 2, H - ch / 2, 5):
            for cx in np.linspace(cw / 2, W - cw / 2, 7):
                sy = np.clip((cy - ch / 2 + ys / s).astype(int), 0, H - 1)
                sx = np.clip((cx - cw / 2 + xs / s).astype(int), 0, W - 1)
                score = float((norm(prev[sy, sx]) * target).sum())
                if score > best[0]:
                    best = (score, s)
    return best


def spans(mask, fps, min_len):
    out, start = [], None
    for i, m in enumerate(np.r_[mask, False]):
        if m and start is None:
            start = i
        elif not m and start is not None:
            if (i - start) / fps >= min_len:
                out.append((start / fps, i / fps))
            start = None
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("film", type=Path)
    ap.add_argument("--mode", choices=["general", "lesson"], default="general",
                    help="'lesson' checks localized board/diagram motion and allows natural formula reading holds")
    ap.add_argument("--song", type=Path, help="songmap.json of the recording used in the film")
    ap.add_argument("--offset", type=float, default=0.0,
                    help="song seconds at film 0, when the film uses an excerpt (the T0 of the scene)")
    ap.add_argument("--json", type=Path, help="write the shot list as JSON")
    args = ap.parse_args()

    fps = probe_fps(args.film)
    v = frames(args.film)
    dur = len(v) / fps
    cuts, motion = find_cuts(v, fps)
    edges = [0] + cuts + [len(v)]
    shots = []
    for a, b in zip(edges[:-1], edges[1:]):
        mid = v[(a + b) // 2]
        shots.append({"t0": round(a / fps, 3), "t1": round(b / fps, 3), "len": round((b - a) / fps, 3),
                      "luma": round(float(v[a:b].mean()), 3)})
    lens = np.array([s["len"] for s in shots])
    mm = lambda t: f"{int(t // 60)}:{t % 60:05.2f}"

    print(f"{args.film.name}: {dur:.2f} s, {fps:g} fps, {len(shots)} shots, "
          f"median {np.median(lens):.2f} s, shortest {lens.min():.2f} s, longest {lens.max():.2f} s")
    buckets = [(0, 1), (1, 2), (2, 3), (3, 4.5), (4.5, 6), (6, 10), (10, 1e9)]
    print("shot lengths: " + "  ".join(f"{a:g}-{b:g}s:{int(((lens >= a) & (lens < b)).sum())}" if b < 1e8 else
                                       f">{a:g}s:{int((lens >= a).sum())}" for a, b in buckets))

    flags = []
    # runs of near-equal lengths
    run = [0]
    for i in range(1, len(shots) + 1):
        if i < len(shots) and abs(lens[i] - lens[run[0]]) <= max(0.08, 0.04 * lens[run[0]]):
            run.append(i)
            continue
        if len(run) >= 4:
            flags.append(f"{mm(shots[run[0]]['t0'])}–{mm(shots[run[-1]]['t1'])}: {len(run)} shots in a row of "
                         f"{lens[run[0]]:.2f} s. Does the music or action change inside this run? Let the "
                         f"phrase, a held note or a finished action set each length.")
        run = [i]
    same_len = max((np.isclose(lens, x, atol=0.05).sum() for x in lens), default=0)
    if len(shots) >= 12 and same_len / len(shots) > 0.5:
        flags.append(f"{same_len} of {len(shots)} shots share one length. The cut follows a grid, not the song.")

    # enlarged repeats
    enlarged = []
    for k in range(1, len(shots)):
        a0, b0 = int(shots[k - 1]["t0"] * fps), int(shots[k - 1]["t1"] * fps)
        a1 = int(shots[k]["t0"] * fps)
        prev, cur = v[max(a0, b0 - 2)], v[min(len(v) - 1, a1 + 1)]
        if prev.std() < 0.02 or cur.std() < 0.02:
            continue
        score, scale = enlarged_from(prev, cur)
        if score > 0.8:
            enlarged.append(k)
            shots[k]["enlarges_previous"] = round(scale, 2)
    if enlarged:
        where = ", ".join(mm(shots[k]["t0"]) for k in enlarged[:12]) + (" …" if len(enlarged) > 12 else "")
        flags.append(f"{len(enlarged)} cuts only enlarge the previous image ({where}). A cut-in earns its place "
                     f"with new detail, a new angle or a change in what the subject does.")

    luma = v.mean(axis=(1, 2))
    for t0, t1 in spans(luma < 0.035, fps, 0.5):
        flags.append(f"{mm(t0)}–{mm(t1)}: black for {t1 - t0:.1f} s")
    for t0, t1 in spans(luma > 0.93, fps, 0.5):
        flags.append(f"{mm(t0)}–{mm(t1)}: white for {t1 - t0:.1f} s")
    black_total = float((luma < 0.035).sum() / fps)
    # Stillness: compare each frame with the one a second earlier (grain and drifting dust average out),
    # never across a cut. In 'lesson' mode, localized vector/formula motion in any 8×4 tile counts as active,
    # and up to 4.5 s of steady reading hold is normal while the narrator finishes a step.
    lag = max(1, int(round(fps)))
    changed = np.ones(len(v), dtype=bool)
    if len(v) > lag:
        delta = np.abs(v[lag:] - v[:-lag]) > 4 / 255
        share = delta.mean(axis=(1, 2))
        if args.mode == "lesson":
            # W=128 (8×16), H=72 (4×18): max active pixel share in any localized board region
            tiles = delta.reshape(-1, 4, 18, 8, 16).mean(axis=(2, 4)).max(axis=(1, 2))
            changed[lag:] = (share >= 0.03) | (tiles >= 0.08)
        else:
            changed[lag:] = share >= 0.07
        for c in cuts:
            changed[c:c + lag] = True
    still = ~changed & (luma >= 0.035)
    merged = []
    for t0, t1 in spans(still, fps, 1.0):
        t0 = max(0.0, t0 - lag / fps)
        if merged and t0 <= merged[-1][1] + 0.05:
            merged[-1][1] = max(merged[-1][1], t1)
        else:
            merged.append([t0, t1])
    min_hold = 4.5 if args.mode == "lesson" else 2.0
    for t0, t1 in merged:
        if t1 - t0 >= min_hold:
            flags.append(f"{mm(t0)}–{mm(t1)}: little changes for {t1 - t0:.1f} s. A held look, or did the shot "
                         f"stop after its last move? Give the camera, light or subject something to do, or cut sooner.")

    if args.song:
        song = json.loads(args.song.read_text(encoding="utf-8"))
        beats = np.array(song["beats"])
        bars = np.array(song["downbeats"])
        offs = []
        for s in shots[1:]:
            t = s["t0"] + args.offset
            db = t - beats[np.argmin(np.abs(beats - t))]
            bb = t - bars[np.argmin(np.abs(bars - t))]
            s["from_beat"], s["from_bar"] = round(db, 3), round(bb, 3)
            offs.append(db)
        offs = np.abs(np.array(offs)) if offs else np.zeros(1)
        on = int((offs <= 1.5 / fps).sum())
        print(f"cuts within 1.5 frames of a beat: {on} of {len(offs)}; median distance {np.median(offs) * 1000:.0f} ms")
        late = [s for s in shots[1:] if abs(s["from_beat"]) > 0.12]
        if late:
            flags.append(f"{len(late)} cuts sit more than 120 ms off the beat, e.g. "
                         + ", ".join(f"{mm(s['t0'])} ({s['from_beat'] * 1000:+.0f} ms)" for s in late[:6])
                         + ". Fine for a cut on a vocal or an action; check the rest by ear.")

    print(f"black in total: {black_total:.1f} s")
    print("\nshots:")
    for k, s in enumerate(shots):
        extra = f"  enlarged ×{s['enlarges_previous']}" if "enlarges_previous" in s else ""
        beat = f"  beat {s['from_beat'] * 1000:+.0f} ms" if "from_beat" in s else ""
        print(f"  {k + 1:3d}  {mm(s['t0'])}  {s['len']:6.2f} s  luma {s['luma']:.2f}{beat}{extra}")
    print("\nlook again at:" if flags else "\nnothing flagged")
    for f in flags:
        print("  - " + f)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({"fps": fps, "duration": dur, "shots": shots, "flags": flags},
                                        ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
