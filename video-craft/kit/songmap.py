"""Map a recording for picture editing: tempo, beats, bars, sections, energy, hits and sung lines.

    python songmap.py song.m4a out/song [--lyrics] [--language en] [--bpm 120] [--meter 4] [--fps 30]

Writes into the output folder:
  songmap.json  everything below, in seconds of the supplied file
  songmap.js    the same data as an ES module: import SONG from './out/song/songmap.js'
  songmap.md    a section table with loudness, character and the lines sung in each section
  songmap.png   an overview to look at (needs Pillow; skipped without it)

Scenes read songmap.json through kit.js (`songAt`, `envAt`, `pulse`) so light, cuts and motion can follow
the actual recording. Beat and section detection are estimates: listen at the boundaries you cut on.
--lyrics transcribes the vocal with faster-whisper (pip install faster-whisper; the model downloads once,
or set VC_WHISPER to a local model folder). Treat the words as a draft and correct them against the
official lyrics before you put text on screen. Needs FFmpeg and NumPy.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

SR = 22050
HOP = 512
NFFT = 2048
FFMPEG = os.getenv("VC_FFMPEG", "ffmpeg")


def decode(path, rate=SR):
    raw = subprocess.check_output([FFMPEG, "-nostdin", "-v", "error", "-i", str(path), "-map", "0:a:0",
                                   "-ac", "1", "-ar", str(rate), "-f", "f32le", "-"])
    audio = np.frombuffer(raw, dtype=np.float32).copy()
    if not audio.size:
        raise SystemExit(f"No audio decoded from {path}")
    return audio


def spectrogram(y):
    pad = np.pad(y, (NFFT // 2, NFFT // 2))
    n = 1 + (len(pad) - NFFT) // HOP
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n)[:, None]
    win = np.hanning(NFFT).astype(np.float32)
    mags = []
    for start in range(0, n, 2048):  # chunk to bound memory on long songs
        mags.append(np.abs(np.fft.rfft(pad[idx[start:start + 2048]] * win, axis=1)).astype(np.float32))
    return np.vstack(mags)


def smooth(x, width):
    width = max(1, int(width))
    if width == 1:
        return x
    k = np.hanning(width + 2)[1:-1]
    k /= k.sum()
    return np.convolve(x, k, mode="same")


def moving(x, width, fn=np.mean):
    half = max(1, int(width) // 2)
    out = np.empty_like(x)
    for i in range(len(x)):
        out[i] = fn(x[max(0, i - half):i + half + 1])
    return out


def flux(logmag, band):
    d = np.diff(logmag[:, band], axis=0, prepend=logmag[:1, band])
    return np.maximum(d, 0).mean(axis=1)


def peaks(env, fps, min_gap=0.09, k=1.5):
    """Onset times from one envelope: local maxima above a moving median plus k * spread."""
    base = moving(env, fps * 0.6, np.median)
    spread = np.median(np.abs(env - base)) + 1e-9
    gap = max(1, int(min_gap * fps))
    hits = []
    for i in range(1, len(env) - 1):
        if env[i] >= env[i - 1] and env[i] > env[i + 1] and env[i] > base[i] + k * spread:
            if hits and i - hits[-1][0] < gap:
                if env[i] > hits[-1][1]:
                    hits[-1] = (i, env[i])
                continue
            hits.append((i, env[i]))
    if not hits:
        return []
    top = max(v for _, v in hits)
    return [(i / fps, float(v / top)) for i, v in hits]


def tempo(onset, fps, lo=60, hi=190, prior=120):
    o = onset - onset.mean()
    ac = np.correlate(o, o, mode="full")[len(o) - 1:]
    lags = np.arange(int(fps * 60 / hi), int(fps * 60 / lo) + 1)
    bpms = 60 * fps / lags
    weight = np.exp(-0.5 * (np.log2(bpms / prior)) ** 2)
    score = ac[lags] * weight
    lag = lags[int(np.argmax(score))]
    # parabolic refinement around the best lag
    if 1 <= lag < len(ac) - 1:
        a, b, c = ac[lag - 1], ac[lag], ac[lag + 1]
        shift = 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
        return 60 * fps / (lag + float(np.clip(shift, -0.5, 0.5)))
    return 60 * fps / lag


def track_beats(onset, fps, bpm, tightness=100.0):
    """Dynamic-programming beat tracker (Ellis 2007)."""
    period = 60 * fps / bpm
    local = smooth(onset / (onset.std() + 1e-9), period / 16)
    n = len(local)
    score = local.copy()
    back = -np.ones(n, dtype=int)
    lo_off, hi_off = int(round(2 * period)), int(round(period / 2))
    for i in range(n):
        lo, hi = max(0, i - lo_off), i - hi_off
        if hi <= lo:
            continue
        prev = np.arange(lo, hi)
        cand = score[prev] - tightness * np.log((i - prev) / period) ** 2
        j = int(np.argmax(cand))
        if cand[j] > 0:
            score[i] = local[i] + cand[j]
            back[i] = prev[j]
    tail = int(n - 2 * period)
    i = tail + int(np.argmax(score[tail:])) if tail > 0 else int(np.argmax(score))
    beats = []
    while i >= 0:
        beats.append(i)
        i = back[i]
    return np.array(beats[::-1]) / fps


def fit_grid(onset, fps, bpm, first, last, spread=0.04):
    """Best constant-tempo grid near bpm: fold the onset curve at each candidate period, keep the sharpest."""
    t = np.arange(len(onset)) / fps
    keep = (t >= first) & (t <= last)
    t, w = t[keep], onset[keep]
    best = (0.0, bpm, 0.0)
    for cand in np.arange(bpm * (1 - spread), bpm * (1 + spread), 0.01):
        period = 60 / cand
        bins = 120
        hist = np.bincount(((t % period) / period * bins).astype(int) % bins, weights=w, minlength=bins)
        hist = np.convolve(np.r_[hist[-2:], hist, hist[:2]], np.ones(5) / 5, mode="valid")
        k = int(np.argmax(hist))
        score = hist[k] / (hist.mean() + 1e-9)
        if score > best[0]:
            best = (score, cand, (k + 0.5) / bins * period)
    _, bpm, phase = best
    period = 60 / bpm
    start = phase + np.ceil((first - 0.05 - phase) / period) * period
    return bpm, np.arange(start, last + 0.05, period)


def chroma_bands(mag, freqs):
    pitch = np.zeros((mag.shape[0], 12), dtype=np.float32)
    ok = (freqs > 60) & (freqs < 5000)
    pc = (np.round(12 * np.log2(freqs[ok] / 440.0)) + 9) % 12
    power = mag[:, ok] ** 2
    for k in range(12):
        pitch[:, k] = power[:, pc == k].sum(axis=1)
    pitch = np.log1p(pitch / (pitch.max() + 1e-9) * 1000)
    edges = np.geomspace(40, 10000, 21)
    timbre = np.stack([np.log1p(mag[:, (freqs >= a) & (freqs < b)].mean(axis=1) * 100)
                       for a, b in zip(edges[:-1], edges[1:])], axis=1)
    return pitch, timbre


def novelty(ssm, half):
    n = len(ssm)
    g = np.exp(-0.5 * (np.linspace(-1.5, 1.5, 2 * half)) ** 2)
    kern = np.outer(g, g) * np.outer(np.r_[-np.ones(half), np.ones(half)], np.r_[-np.ones(half), np.ones(half)])
    padded = np.pad(ssm, half, mode="edge")
    return np.array([(padded[i:i + 2 * half, i:i + 2 * half] * kern).sum() for i in range(n)])


def sections(bars, feats, loud, min_bars=4, max_bars=16):
    f = feats - feats.mean(axis=0)
    f /= f.std(axis=0) + 1e-9
    f /= np.linalg.norm(f, axis=1, keepdims=True) + 1e-9
    ssm = f @ f.T
    if len(bars) < 2 * min_bars:
        return [(0, len(bars))], ssm
    nov = novelty(ssm, min_bars) + 0.6 * np.abs(np.diff(loud, prepend=loud[0])) / (loud.std() + 1e-9)
    nov = (nov - nov.mean()) / (nov.std() + 1e-9)
    # Songs change on 4-bar phrases. Find the phrase offset where changes cluster and favour it.
    offset = int(np.argmax([nov[o::4].mean() for o in range(4)]))
    on_phrase = (np.arange(len(nov)) - offset) % 4 == 0
    nov = nov + 0.6 * on_phrase
    is_peak = lambda i: nov[i] == nov[max(0, i - 2):i + 3].max()
    cand = sorted((i for i in range(min_bars, len(nov) - min_bars + 1) if is_peak(i) and nov[i] > 0.3),
                  key=lambda i: -nov[i])
    chosen = []
    for i in cand:
        if all(abs(i - j) >= min_bars for j in chosen):
            chosen.append(i)
    # Long stretches of one texture still change every 8-16 bars; split them at their strongest change.
    edges = sorted([0, len(bars)] + chosen)
    changed = True
    while changed:
        changed = False
        for a, b in zip(edges[:-1], edges[1:]):
            if b - a > max_bars:
                inner = range(a + min_bars, b - min_bars + 1)
                split = max(inner, key=lambda i: (nov[i], -abs((i - a) % 4)))
                edges = sorted(edges + [split])
                changed = True
                break
    return [(a, b) for a, b in zip(edges[:-1], edges[1:])], ssm


def label_sections(spans, ssm):
    labels, reps = [], []
    for a, b in spans:
        best, best_sim = None, 0.0
        for lab, (ra, rb) in reps:
            n = min(b - a, rb - ra)
            sim = float(np.mean([ssm[a + k, ra + k] for k in range(n)])) if n else 0.0
            if sim > best_sim:
                best, best_sim = lab, sim
        if best is not None and best_sim > 0.55:
            labels.append(best)
        else:
            lab = chr(ord("A") + len(reps)) if len(reps) < 26 else f"S{len(reps)}"
            reps.append((lab, (a, b)))
            labels.append(lab)
    return labels


def transcribe(path, language):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("--lyrics needs faster-whisper (pip install faster-whisper); continuing without words", file=sys.stderr)
        return None
    model_ref = os.getenv("VC_WHISPER", "large-v3-turbo")
    try:                                   # ask CTranslate2, not torch: both in one process can crash on Windows
        import ctranslate2
        cuda = ctranslate2.get_cuda_device_count() > 0
    except Exception:
        cuda = False
    model = WhisperModel(model_ref, device="cuda" if cuda else "cpu", compute_type="float16" if cuda else "int8")
    audio = decode(path, 16000)
    segs, info = model.transcribe(audio, language=language, beam_size=5, temperature=0, word_timestamps=True,
                                  vad_filter=False, condition_on_previous_text=False)
    lines, dropped = [], []
    filler = {"thank you", "thank you.", "thanks for watching", "thanks for watching!", "you", "bye", "bye."}
    for s in segs:
        text = s.text.strip()
        if not text:
            continue
        # Whisper invents text over instrumental passages: stage directions, sign-offs, endless loops.
        bracketed = text[0] in "([*♪" or text.lower().rstrip("!.") + "." in {f + "." for f in ("piano plays softly", "music")}
        looping = s.compression_ratio > 2.4
        unlikely = s.no_speech_prob > 0.6 and s.avg_logprob < -0.8
        if bracketed or unlikely or text.lower() in filler:
            dropped.append([round(s.start, 2), text[:40]])
            continue
        words = [{"t0": round(w.start, 2), "t1": round(w.end, 2), "w": w.word.strip()} for w in (s.words or [])]
        if looping:
            first = text.split(",")[0].split()[0].strip(".!?") if text.split() else text
            text = f"{first} … (repeated, check by ear)"
            words = words[:1]
        lines.append({"t0": round(s.start, 2), "t1": round(s.end, 2), "text": text, "words": words})
    return {"language": info.language, "source": f"faster-whisper {model_ref}, unchecked draft",
            "lines": lines, "dropped_as_unlikely": dropped}


def accents(hit_list, beat, window):
    """The hits worth a visible response: at most one per beat (the strongest), and only those in the top
    15 % of the hits around them (`window` seconds), so a busy chorus still gives about one accent a bar."""
    if not hit_list:
        return []
    arr = np.array(hit_list, dtype=float)
    out = []
    for t, v in arr:
        if v < arr[np.abs(arr[:, 0] - t) < beat / 2, 1].max():
            continue
        hood = arr[np.abs(arr[:, 0] - t) < window / 2, 1]
        if v >= np.percentile(hood, 85):
            out.append([round(float(t), 3), round(float(v), 2)])
    return out


def to_unit(db, floor=-42.0):
    return np.clip((db - floor) / -floor, 0, 1)


def overview(path, out, dur, env_fps, rms, low, high, beats, downbeats, secs, lyrics):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow not installed: skipped songmap.png", file=sys.stderr)
        return
    W, H, top = 2400, 520, 70
    img = Image.new("RGB", (W, H), (20, 22, 26))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("msyh.ttc", 18)
    except OSError:
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 16)
        except OSError:
            font = ImageFont.load_default()
    x = lambda t: int(t / dur * (W - 20)) + 10
    palette = [(70, 110, 160), (170, 90, 80), (90, 150, 110), (160, 140, 70), (120, 90, 160), (70, 150, 160)]
    for s in secs:
        c = palette[(ord(s["label"][0]) - 65) % len(palette)]
        d.rectangle([x(s["t0"]), top, x(s["t1"]), H - 120], fill=tuple(int(v * 0.45) for v in c))
        d.text((x(s["t0"]) + 4, top + 4), f'{s["label"]} {s["character"]}', fill=(235, 235, 235), font=font)
    base, span = H - 120, H - 120 - top - 40
    k = max(1, int(env_fps))  # one-second smoothing keeps the overview readable
    for arr, col, wid in ((low, (240, 140, 90), 2), (high, (120, 200, 240), 2), (rms, (245, 245, 245), 3)):
        sm = np.convolve(arr, np.ones(k) / k, mode="same")
        pts = [(x(i / env_fps), base - sm[i] * span) for i in range(0, len(sm), 2)]
        d.line(pts, fill=col, width=wid)
    for b in beats:
        d.line([x(b), base, x(b), base + 6], fill=(120, 120, 120))
    for b in downbeats:
        d.line([x(b), base, x(b), base + 14], fill=(220, 220, 220))
    for t in range(0, int(dur) + 1, 10):
        d.line([x(t), top - 12, x(t), top], fill=(150, 150, 150))
        d.text((x(t) + 2, top - 34), f"{t // 60}:{t % 60:02d}", fill=(170, 170, 170), font=font)
    if lyrics:
        for k, line in enumerate(lyrics["lines"]):
            y = base + 24 + (k % 4) * 22
            d.line([x(line["t0"]), y, x(line["t1"]), y], fill=(230, 200, 120), width=3)
            d.text((x(line["t0"]), y + 2), line["text"][:28], fill=(230, 200, 120), font=font)
    d.text((10, 8), f"{Path(path).name}  white=loudness  orange=low band  blue=high band  long ticks=bars",
           fill=(200, 200, 200), font=font)
    img.save(out)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--lyrics", action="store_true", help="transcribe sung lines with faster-whisper")
    ap.add_argument("--language", default=None, help="language code for --lyrics, e.g. zh or en")
    ap.add_argument("--bpm", type=float, default=None, help="override the tempo estimate")
    ap.add_argument("--meter", type=int, default=4, help="beats per bar")
    ap.add_argument("--fps", type=float, default=30, help="sample rate of the energy curves in the JSON")
    args = ap.parse_args()

    y = decode(args.audio)
    dur = len(y) / SR
    mag = spectrogram(y)
    fps = SR / HOP
    freqs = np.fft.rfftfreq(NFFT, 1 / SR)
    logmag = np.log1p(100 * mag / (mag.max() + 1e-9))

    bands = {"low": (freqs >= 30) & (freqs < 150), "mid": (freqs >= 150) & (freqs < 2500),
             "high": (freqs >= 2500) & (freqs < 11000)}
    onset = np.maximum(np.diff(logmag, axis=0, prepend=logmag[:1]), 0).mean(axis=1)
    band_onsets = {k: flux(logmag, b) for k, b in bands.items()}

    frame_db = 10 * np.log10((mag ** 2).mean(axis=1) + 1e-12)
    frame_db -= frame_db.max()
    sound = np.where(frame_db > -45)[0]
    first, last = sound[0] / fps, sound[-1] / fps

    bpm = args.bpm or tempo(onset, fps)
    tracked = track_beats(onset, fps, bpm)
    tracked = tracked[(tracked >= first - 0.05) & (tracked <= last + 0.05)]
    # Most produced songs keep one tempo. Prefer a fitted grid when the tracked beats sit on it;
    # otherwise keep the tracked beats (rubato, live takes, tempo changes).
    grid_bpm, grid = fit_grid(onset, fps, bpm, first, last, 0.005 if args.bpm else 0.04)
    if len(tracked) > 8:
        period = 60 / grid_bpm
        dev = np.abs(((tracked - grid[0]) / period + 0.5) % 1 - 0.5)
        steady = float(np.median(dev)) < 0.12
    else:
        steady = True
    beats, bpm = (grid, grid_bpm) if steady else (tracked, 60 / float(np.median(np.diff(tracked))))
    tempo_kind = "steady grid" if steady else "tracked, tempo varies"

    # downbeat phase: where the low band hits hardest
    low_env = smooth(band_onsets["low"], 3)
    strength = [low_env[np.clip((beats[p::args.meter] * fps).astype(int), 0, len(low_env) - 1)].mean()
                for p in range(args.meter)]
    phase = int(np.argmax(strength))
    downbeats = beats[phase::args.meter]
    bar_edges = np.r_[0.0, downbeats, dur] if downbeats.size and downbeats[0] > 0.3 else np.r_[downbeats, dur]
    bar_edges = np.unique(np.round(bar_edges, 4))

    pitch, timbre = chroma_bands(mag, freqs)
    rows, loud = [], []
    for a, b in zip(bar_edges[:-1], bar_edges[1:]):
        i, j = int(a * fps), max(int(a * fps) + 1, int(b * fps))
        rows.append(np.r_[pitch[i:j].mean(axis=0), timbre[i:j].mean(axis=0) * 1.5])
        a0 = min(max(i, int(first * fps)), j - 1)               # only where there is sound: not the silence
        k = max(a0 + 1, min(j, int(last * fps) + 1))           # before the first note or after the last
        loud.append(np.maximum(frame_db[a0:k], -60).mean())    # floor: digital silence would swamp the mean
    feats, loud = np.array(rows), np.array(loud)
    spans, ssm = sections(bar_edges[:-1], feats, loud)
    labels = label_sections(spans, ssm)
    # a section's loudness ignores bars after the sound has ended (the tail of the file)
    heard = bar_edges[:-1] < last - 0.25
    sec_db = [float(loud[a:b][heard[a:b]].mean() if heard[a:b].any() else loud[a:b].mean()) for a, b in spans]
    lo_q, hi_q = np.percentile(sec_db, 30), np.percentile(sec_db, 70)
    secs = []
    for k, ((a, b), lab, db) in enumerate(zip(spans, labels, sec_db)):
        prev = sec_db[k - 1] if k else db
        character = ("peak" if db >= hi_q else "quiet" if db <= lo_q else "mid")
        if k and db - prev > 3:
            character += ", lifts"
        elif k and prev - db > 3:
            character += ", drops"
        t0 = float(bar_edges[a])
        # index into downbeats of the section's first bar (None when it starts on the pickup before bar 0)
        near = int(np.argmin(np.abs(downbeats - t0))) if downbeats.size else -1
        bar = near if near >= 0 and abs(downbeats[near] - t0) < 0.02 else None
        secs.append({"t0": round(t0, 3), "t1": round(float(bar_edges[b]), 3), "bar": bar,
                     "bars": b - a, "label": lab, "db": round(db, 1), "character": character})

    # energy curves sampled at the film frame rate, 0..1 over a 42 dB window below the loudest frame
    env_fps = args.fps
    times = np.arange(0, dur, 1 / env_fps)
    def curve(db_frames):
        sm = smooth(db_frames, fps / env_fps * 2)
        return np.round(to_unit(np.interp(times, np.arange(len(sm)) / fps, sm)), 3)
    band_db = {k: 10 * np.log10((mag[:, b] ** 2).mean(axis=1) + 1e-12) for k, b in bands.items()}
    band_db = {k: v - v.max() for k, v in band_db.items()}
    rms, low, high = curve(frame_db), curve(band_db["low"]), curve(band_db["high"])

    hits = {k: [[round(t, 3), round(v, 2)] for t, v in peaks(smooth(e, 2), fps, 0.09 if k != "low" else 0.12)]
            for k, e in band_onsets.items()}
    bar_len = 60 / bpm * args.meter
    accent = {k: accents(hits[k], 60 / bpm, 8 * bar_len) for k in ("low", "high")}
    lyrics = transcribe(args.audio, args.language) if args.lyrics else None

    args.out.mkdir(parents=True, exist_ok=True)
    data = {
        "source": args.audio.name, "duration": round(dur, 3), "sound": [round(first, 3), round(last, 3)],
        "bpm": round(bpm, 2), "tempo": tempo_kind, "meter": args.meter,
        "beats": [round(float(b), 3) for b in beats], "downbeats": [round(float(b), 3) for b in downbeats],
        "sections": secs, "hits": hits, "accents": accent,
        "env": {"fps": env_fps, "rms": rms.tolist(), "low": low.tolist(), "high": high.tolist()},
        "lyrics": lyrics,
        "note": "Estimates from the recording. Listen at every boundary you cut on; correct auto lyrics.",
    }
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    (args.out / "songmap.json").write_text(blob, encoding="utf-8")
    # pages open from file:// cannot fetch JSON; they import this module instead
    (args.out / "songmap.js").write_text("export default " + blob + ";\n", encoding="utf-8")

    mm = lambda t: f"{int(t // 60)}:{t % 60:05.2f}"
    md = [f"# {args.audio.name}", "",
          f"{dur:.2f} s · {bpm:.2f} BPM, {tempo_kind} · first beat {beats[0]:.3f} s · one bar = {60 / bpm * args.meter:.3f} s · sound {first:.2f}–{last:.2f} s",
          "", "| # | from | to | first bar | bars | same as | loudness | character | sung in this section |",
          "|---|---|---|---|---|---|---|---|---|"]
    for k, s in enumerate(secs):
        # a line belongs to the section that holds its middle
        sung = " / ".join(l["text"] for l in (lyrics or {}).get("lines", [])
                          if s["t0"] <= (l["t0"] + l["t1"]) / 2 < s["t1"]) or "—"
        first_of = next((m for m, q in enumerate(secs) if q["label"] == s["label"]), k)
        same = f"#{first_of + 1}" if first_of != k else ""
        bar = "pickup" if s["bar"] is None else s["bar"]
        md.append(f"| {k + 1} | {mm(s['t0'])} | {mm(s['t1'])} | {bar} | {s['bars']} | {same} | {s['db']} dB | {s['character']} | {sung} |")
    md += ["", "\"first bar\" is the index into `downbeats`: in a scene, `SONG.downbeats[n]` is that section's start. "
           "\"same as #n\" marks a section that sounds like an earlier one (a returning chorus, verse or riff). "
           "Loudness is the section mean relative to the loudest frame. Lyrics, when present, are an unchecked "
           "machine transcript."]
    (args.out / "songmap.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    overview(args.audio, args.out / "songmap.png", dur, env_fps, rms, low, high, beats, downbeats, secs, lyrics)
    print("\n".join(md[2:3] + md[4:4 + len(secs) + 2]))
    print(f"wrote {args.out / 'songmap.json'}")


if __name__ == "__main__":
    main()
