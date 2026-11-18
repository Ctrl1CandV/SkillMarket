"""Voice A/B for video-craft 0.7: shipped Edge voice vs VoxCPM1.5 (small) vs VoxCPM2 (large).

Each role first gets one voice card: a short reference read made once with VoxCPM2 voice design.
B and C then clone that same card, so the comparison is between models, not between voices.
Every passage is generated as one paragraph, the way a narrator reads, not sentence by sentence.

    python make_ab.py cards   --v2 <VoxCPM2 dir>               # design the cards (2 tries each)
    python make_ab.py takes   --v15 <VoxCPM1.5 dir> --v2 <dir>  # B and C for each passage
    python make_ab.py edge                                      # A: the shipped Edge voices
    python make_ab.py check                                     # transcribe, loudness-match, page data
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
EX = HERE.parents[3] / "video-craft" / "examples"

ROLES = {
    "teacher": {
        "design": "一位三十岁左右的女性老师，声音温暖清澈，语速从容，像在给朋友讲一道有意思的题",
        "card": "我们先别急着算。看看这道题到底在问什么，其实换个角度，答案就藏在图里。",
        "edge": "zh-CN-XiaoxiaoNeural",
    },
    "promo": {
        "design": "年轻男性，声音干净明亮，有活力，语速稍快，自信但不夸张",
        "card": "这是我们做了很久的一个小工具。打开就能用，不用学，也不用等。",
        "edge": "zh-CN-YunxiNeural",
    },
    "story": {
        "design": "中年男性，声音低沉温和，语速缓慢，带一点回忆的感情",
        "card": "很多年以后，他还记得那个下午。风从河面上吹过来，带着一点潮湿的味道。",
        "edge": "zh-CN-YunjianNeural",
    },
}

PASSAGES = {
    "lesson": ("teacher", "九枚硬币里，有一枚轻一些，其余八枚一样重。只有一架天平。怎样只称两次，就找出那枚轻币？"
                          "先把硬币分成三堆，每堆三枚。一到三号放左盘，四到六号放右盘。留下一堆。"),
    "spot": ("promo", "今晚，开场提前十五分钟。灯光几点到？音响呢？用倒场，改一个开场时间。灯光、音响、入场，全都跟着走。"),
    "story": ("story", "那年冬天，海边的灯塔还亮着。每天傍晚，他都会爬上去，看最后一艘船回港。"
                       "后来船不来了，他还是去，只是看得更久一些。"),
}


def load(path):
    from voxcpm import VoxCPM
    t = time.time()
    m = VoxCPM.from_pretrained(str(path), load_denoiser=False, optimize=False)
    print(f"loaded {Path(path).name} in {time.time() - t:.0f} s", flush=True)
    return m


def save(model, wav, path):
    import soundfile as sf
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), wav, model.tts_model.sample_rate)


def speak(model, text, out, **kw):
    t = time.time()
    wav = model.generate(text=text, cfg_value=2.0, inference_timesteps=10, normalize=False,
                         denoise=False, retry_badcase=True, **kw)
    save(model, wav, out)
    secs = len(wav) / model.tts_model.sample_rate
    print(f"  {out.relative_to(OUT)}: {secs:.1f} s audio in {time.time() - t:.1f} s", flush=True)
    return secs, time.time() - t


def cmd_cards(args):
    import torch
    m = load(args.v2)
    for role, r in ROLES.items():
        for k in range(args.tries):
            torch.manual_seed(1000 + k)
            speak(m, f"({r['design']}){r['card']}", OUT / "cards" / f"{role}-{k}.wav")


def cmd_takes(args):
    import torch
    chosen = json.loads((OUT / "cards" / "chosen.json").read_text(encoding="utf-8"))
    stats = {}
    for tag, path in (("B", args.v15), ("C", args.v2)):
        if not path:
            continue
        m = load(path)
        for name, (role, text) in PASSAGES.items():
            card = OUT / "cards" / f"{role}-{chosen[role]}.wav"
            for k in range(args.tries):
                torch.manual_seed(2000 + k)
                secs, took = speak(m, text, OUT / "takes" / f"{name}-{tag}-{k}.wav",
                                   prompt_wav_path=str(card), prompt_text=ROLES[role]["card"])
                stats[f"{name}-{tag}-{k}"] = {"audio": round(secs, 2), "took": round(took, 2)}
        del m
        torch.cuda.empty_cache()
    (OUT / "takes" / "speed.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")


def cmd_edge(args):
    import edge_tts
    async def run():
        for name, (role, text) in PASSAGES.items():
            mp3 = OUT / "takes" / f"{name}-A-0.mp3"
            mp3.parent.mkdir(parents=True, exist_ok=True)
            rate = "-4%" if name == "lesson" else "+0%"
            await edge_tts.Communicate(text, ROLES[role]["edge"], rate=rate).save(str(mp3))
            print("  ", mp3.name, flush=True)
    asyncio.run(run())


def pitch(path):
    """median F0 of voiced 40 ms frames, by autocorrelation (70-400 Hz)"""
    import numpy as np
    raw = subprocess.check_output(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "16000",
                                   "-f", "f32le", "-"])
    x = np.frombuffer(raw, dtype=np.float32)
    n, hop = 640, 160
    loud = np.sqrt(np.mean(x ** 2)) * 0.6
    out = []
    for i in range(0, len(x) - n, hop):
        f = x[i:i + n] - x[i:i + n].mean()
        if np.sqrt(np.mean(f ** 2)) < loud:
            continue
        ac = np.correlate(f, f, "full")[n - 1:]
        lo, hi = 16000 // 400, 16000 // 70
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.45 * ac[0]:
            out.append(16000 / k)
    return float(np.median(out)) if out else 0.0


def cmd_check(args):
    """Transcribe every take, score how many characters it got wrong, loudness-match to -16 LUFS."""
    from faster_whisper import WhisperModel
    import re
    model = WhisperModel(os.environ["VC_WHISPER"], device="cpu", compute_type="int8")
    # numbers come back as digits from the recogniser; leave them out of the comparison
    strip = lambda s: re.sub(r"[0-9零一二三四五六七八九十]", "", re.sub(r"[^一-鿿0-9A-Za-z]", "", s))

    def cer(ref, hyp):
        ref, hyp = strip(ref), strip(hyp)
        d = list(range(len(hyp) + 1))
        for i, a in enumerate(ref, 1):
            prev, d[0] = d[0], i
            for j, b in enumerate(hyp, 1):
                prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (a != b))
        return d[-1] / max(1, len(ref))

    rows = []
    files = sorted((OUT / "takes").glob("*.wav")) + sorted((OUT / "takes").glob("*.mp3")) + sorted((OUT / "cards").glob("*.wav"))
    for f in files:
        name = f.stem
        if f.parent.name == "cards":
            role = name.rsplit("-", 1)[0]
            ref = ROLES[role]["card"]
        else:
            ref = PASSAGES[name.split("-")[0]][1]
        segs, _ = model.transcribe(str(f), language="zh", beam_size=5, vad_filter=False,
                                   initial_prompt="以下是普通话的句子。")
        hyp = "".join(s.text for s in segs)
        norm = OUT / "listen" / (f"{f.parent.name}-{name}.m4a")
        norm.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(f), "-af",
                        "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000", "-c:a", "aac", "-b:a", "192k",
                        str(norm)], check=True)
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                             "-of", "csv=p=0", str(norm)], text=True))
        f0 = pitch(f)
        rate = len(strip(ref)) / dur
        rows.append({"file": norm.name, "src": f"{f.parent.name}/{f.name}", "dur": round(dur, 2),
                     "cer": round(cer(ref, hyp), 3), "f0": round(f0), "cps": round(rate, 2), "heard": hyp.strip()})
        print(f"{rows[-1]['src']:28s} {dur:5.1f} s  {rate:4.1f} char/s  f0 {f0:4.0f} Hz  cer {rows[-1]['cer']:.3f}  {hyp.strip()}", flush=True)
    (OUT / "check.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["cards", "takes", "edge", "check"])
    ap.add_argument("--v15")
    ap.add_argument("--v2")
    ap.add_argument("--tries", type=int, default=2)
    args = ap.parse_args()
    {"cards": cmd_cards, "takes": cmd_takes, "edge": cmd_edge, "check": cmd_check}[args.step](args)


if __name__ == "__main__":
    main()
