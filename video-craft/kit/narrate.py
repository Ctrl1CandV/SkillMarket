"""Render narration, one WAV per cue, in one consistent voice — with GPU safety guard and word-level timestamps.

    python narrate.py cues.json voice/ [--voice teacher] [--takes 3] [--engine voxcpm|edge] [--device auto|cuda|cpu]

cues.json is {"id": "spoken line", ...} or a spot.json with a "voice" list of {"id", "words"}.
Outputs <id>.wav plus vo.js (clip durations) and words.json / words.js (word-level [t0, t1] timestamps).

Engines
  voxcpm  local VoxCPM (pip install voxcpm; GPU recommended). Every cue clones the same voice card, so the
          whole film has one speaker. Checks GPU utilization and free VRAM before allocating CUDA; if the GPU
          is busy (>=75% util) or low on free VRAM (<4 GiB for 1.5, <7 GiB for 2), exits with code 3 unless
          --force-gpu or --device cpu is given.
  edge    Microsoft's online voices through edge-tts (zero GPU; captures native WordBoundary timestamps).
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
from contextlib import contextmanager
from tempfile import NamedTemporaryFile, TemporaryDirectory, gettempdir
import time
import wave

from gpu import VOXCPM15_SAFE_MIB, VOXCPM2_SAFE_MIB, probe_gpu, resolve_cached_model

FFMPEG = os.getenv("VC_FFMPEG", "ffmpeg")
VOICES = Path(__file__).resolve().parent / "voices"


@contextmanager
def gpu_narrate_lock(timeout_sec=300):
    """Serialize local GPU TTS across concurrent narrate.py processes so parallel builds never OOM each other."""
    lock_path = Path(gettempdir()) / "video-craft-gpu.lock"
    fh = open(lock_path, "a+b")
    deadline = time.monotonic() + timeout_sec
    locked = False
    try:
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
                break
            except OSError:
                if time.monotonic() >= deadline:
                    break
                time.sleep(1.5)
        yield
    finally:
        if locked:
            try:
                if os.name == "nt":
                    import msvcrt
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        fh.close()


def read_cues(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError('Expected a JSON object mapping cue ids to text, or a spot.json with a voice list.')
    is_spot = isinstance(data.get("voice"), list)
    rows = ([(item["id"], item["words"]) for item in data["voice"]]
            if is_spot else list(data.items()))
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
    return cues, is_spot


_CONNECTORS = {
    "因此", "所以", "不过", "但是", "然而", "其实", "注意", "记住", "首先", "其次",
    "接着", "然后", "最后", "同时", "反之", "结果", "可见", "比如", "例如", "总之",
}

_AI_CLICHE_PATTERNS = [
    (re.compile(r"凭什么[？?]?|差在哪(?:里|儿)?[？?]?|到底怎么回事[？?]?|为什么这么说[？?]?"),
     "AI 反问噱头腔（如“凭什么？”“差在哪？”），请改成自然完整的设问句（如“这两种反应为什么会差这么多呢？”）"),
    (re.compile(r"(?:一|两|二|三|四)个(?:坑|关键|重点|核心|要点|细节|误区)"),
     "提纲报幕起手（如“两个坑”“三个关键”），请融进自然口语过渡（如“考场上最容易算错的地方主要有两个，第一是……”）"),
    (re.compile(r"一句话总结|总结一下[：:]|口诀[：:]|记住[：:]|划重点|核心在于|归根结底|换句话说|不难发现|值得注意的是"),
     "AI 总结套话或冒号喊口号（如“口诀：”“记住：”“核心在于”），请直接用平实自然的老师口吻把道理说清"),
    (re.compile(r"\b(?:cwnd|ssthresh|dupACK|ack|rtt)\b"),
     "夹杂未转译的代码/协议缩写（TTS 会生硬拼读字母），画面写符号即可，口播请说中文全称（如“拥塞窗口”“慢启动阈值”“重复确认”“往返时间”）"),
]

_NUM_ROLLCALL_RE = re.compile(r"[零一二三四五六七八九十百千万两\d]+(?:、[零一二三四五六七八九十百千万两\d]+){2,}")


def _han_count(s: str) -> int:
    return len(re.findall(r"[一-鿿]", s))


def lint_cues(cues: dict, is_spot: bool, args) -> list[str]:
    """Check Chinese lecture narration for choppy, telegraphic, or AI-flavored prose before TTS synthesis."""
    style = getattr(args, "style", "auto")
    if getattr(args, "allow_terse", False) or style == "free":
        return []
    lang = args.language or guess_language(cues.values())
    if lang != "zh":
        return []
    voice_str = str(args.voice or "teacher")
    is_teacher = (args.voice is None or voice_str == "teacher" or "Yunxi" in voice_str) and not args.design
    if style == "auto" and (is_spot or not is_teacher):
        return []

    issues = []
    cue_lengths = []
    all_clauses = []
    short4_non_conn = 0
    total_colons = 0

    for key, line in cues.items():
        hlen = _han_count(line)
        cue_lengths.append((key, hlen, line))
        total_colons += line.count("：") + line.count(":")

        if "；" in line or ";" in line:
            issues.append(
                f"  - [{key}] 含分号“；”（书面并列排比腔，配音会生硬断气）：{line!r}\n"
                f"    → 改法：拆成两句有自然因果/转折连词（“因为……”“可一旦……”“而另一边……”）的完整口语整句。"
            )
        if _NUM_ROLLCALL_RE.search(line):
            issues.append(
                f"  - [{key}] 含顿号报数串（如“一、二、四、八”，TTS 会像点名一样机械蹦字）：{line!r}\n"
                f"    → 改法：把数字融进动作描述里（如“从一翻倍到二和四，三个往返就推到了阈值八”或“从八一路稳步加一涨到十二”）。"
            )
        if re.search(r"\d", line):
            issues.append(
                f"  - [{key}] 含阿拉伯数字（易导致小数/比值误读）：{line!r}\n"
                f"    → 改法：口播台词一律写成准确中文读法（如“四点五”“十二”“四比三”）。"
            )
        for pat, hint in _AI_CLICHE_PATTERNS:
            m = pat.search(line)
            if m:
                issues.append(f"  - [{key}] 检测到 {hint}（命中：{m.group(0)!r}）")

        clauses = [c.strip() for c in re.split(r"[，,。？！?!：:；;]+", line) if _han_count(c) > 0]
        all_clauses.extend(clauses)
        cue_short4 = [c for c in clauses if _han_count(c) <= 4 and c not in _CONNECTORS]
        short4_non_conn += len(cue_short4)
        if len(clauses) >= 4 and len(cue_short4) >= 3:
            issues.append(
                f"  - [{key}] 四字以内碎短句过多（{cue_short4}），听感破碎像念电报：{line!r}\n"
                f"    → 改法：补全主语、谓语和自然连接词，合并成舒展连贯的讲台长句。"
            )

    if len(cues) >= 4:
        sorted_lens = sorted(x[1] for x in cue_lengths)
        median_len = sorted_lens[len(sorted_lens) // 2]
        too_short = [(k, n) for k, n, _ in cue_lengths if n < 26]
        under_32 = [(k, n) for k, n, _ in cue_lengths if n < 32]
        if median_len < 36 or too_short or len(under_32) > 1:
            short_desc = ", ".join(f"{k}({n}字)" for k, n in under_32) or "无"
            issues.append(
                f"  - [整稿过短过碎] 当前每条 cue 中位字数仅 {median_len} 字（偏短条目：{short_desc}）。\n"
                f"    → 改法：讲题配音切忌拆成十几二十字的口号短促句！请合并/扩写为每条 42–75 个汉字（2–3 句完整、舒展、像真老师在讲台上娓娓道来的整话，全片约 6–8 条）。"
            )
        if total_colons > 2:
            issues.append(
                f"  - [冒号报幕腔] 全稿使用了 {total_colons} 处冒号“：”（上限 2 处）。口播不是念 PPT 提纲，请把“XX：……”改成自然衔接的句子。"
            )
        if all_clauses:
            mean_clause = sum(_han_count(c) for c in all_clauses) / len(all_clauses)
            short4_ratio = short4_non_conn / len(all_clauses)
            if mean_clause < 7.0 or short4_ratio > 0.20:
                issues.append(
                    f"  - [节奏蹦词感] 平均分句长度仅 {mean_clause:.1f} 字，≤4 字碎词占比 {short4_ratio:.0%}（要求平均分句 ≥7.0 字且碎词占比 ≤20%）。\n"
                    f"    → 改法：少打碎逗号，删掉“阈值八，到八碰线，只是轻堵，减半够用”这类四字缩略语，用完整自然的现代汉语口语把因果讲透。"
                )

    return issues


def pcm16(samples):
    """float list/array in -1..1 → bytes of little-endian int16"""
    out = array("h", (max(-32768, min(32767, int(round(x * 32767)))) for x in samples))
    if sys.byteorder == "big":
        out.byteswap()
    return out.tobytes()


def trim(raw, rate, below_peak_db=40, floor_db=-60):
    """Trim the outer edges only, keeping every pause inside the line. Returns (pcm bytes, longest inner gap, start_sec)."""
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
    return raw[start * 2:end * 2], max(gaps, default=0), start / rate


def write_wav(path, pcm, rate):
    with wave.open(str(path), "wb") as w:
        w.setparams((1, 2, rate, 0, "NONE", ""))
        w.writeframes(pcm)


def atomic_write_text(target: Path, content: str):
    with NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=target.parent, delete=False) as sibling:
        sibling.write(content)
        staged = Path(sibling.name)
    try:
        staged.replace(target)
    finally:
        staged.unlink(missing_ok=True)


# ---------------------------------------------------------------- choosing among takes & word alignment
def guess_language(texts):
    joined = "".join(texts)
    han = len(re.findall(r"[一-鿿]", joined))
    letters = len(re.findall(r"[A-Za-z]", joined))
    return "zh" if han >= letters else "en"


def plain(s, language):
    s = s.lower()
    if language == "zh":
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
    """Runs in its own CPU int8 process: avoids Windows torch+CTranslate2 OpenMP clash and zero GPU contention."""
    from faster_whisper import WhisperModel
    data = json.loads(Path(job).read_text(encoding="utf-8"))
    w_ref = os.getenv("VC_WHISPER") or resolve_cached_model([
        "models--mobiuslabsgmbh--faster-whisper-large-v3-turbo",
        "models--Systran--faster-whisper-large-v3",
    ]) or "large-v3-turbo"
    model = WhisperModel(w_ref, device="cpu", compute_type="int8")
    out = {}
    for item in data["takes"]:
        segs, _ = model.transcribe(
            item["path"],
            language=data["language"],
            beam_size=5,
            vad_filter=False,
            word_timestamps=True,
            initial_prompt="以下是普通话的句子。" if data["language"] == "zh" else None,
        )
        segs = list(segs)
        words = [
            {"w": w.word.strip(), "t0": round(float(w.start), 3), "t1": round(float(w.end), 3)}
            for seg in segs for w in (seg.words or []) if w.word and w.word.strip()
        ]
        out[item["path"]] = {"text": "".join(x.text for x in segs), "words": words}
    Path(job).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")


def heard(rendered, temp, language):
    """{take path: {"text": str, "words": list}} or {} when faster-whisper is unavailable."""
    takes_to_check = [{"path": str(t[0])} for _, _, takes, _ in rendered for t in takes]
    if not takes_to_check:
        return {}
    job = temp / "transcribe.json"
    job.write_text(json.dumps({"language": language, "takes": takes_to_check}), encoding="utf-8")
    run = subprocess.run([sys.executable, __file__, "--transcribe", str(job)], capture_output=True, text=True)
    if run.returncode:
        last = (run.stderr.strip().splitlines() or ["unknown error"])[-1]
        print(f"(no faster-whisper check: {last})", flush=True)
        return {}
    return json.loads(job.read_text(encoding="utf-8"))


def transcript_text(entry):
    if isinstance(entry, dict):
        return entry.get("text", "")
    return entry or ""


def transcript_words(entry):
    if isinstance(entry, dict):
        return entry.get("words") or []
    return []


def pick(takes, text, transcripts, language):
    if len(takes) == 1:
        return 0
    lens = sorted(t[1] for t in takes)
    median = lens[len(lens) // 2]
    scores = []
    for t in takes:
        path, secs, gap = t[0], t[1], t[2]
        err = char_errors(text, transcript_text(transcripts.get(str(path))), language) if str(path) in transcripts else 0.0
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
    if args.device == "cpu":
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
    model_id = args.model or os.getenv("VC_VOXCPM")
    if not model_id:
        model_id = resolve_cached_model(["OpenBMB--VoxCPM2", os.path.join("OpenBMB", "VoxCPM2"), "models--openbmb--VoxCPM2"]) if args.design else (
            resolve_cached_model(["OpenBMB--VoxCPM1.5", os.path.join("OpenBMB", "VoxCPM1.5"), "models--openbmb--VoxCPM1.5"]) or "openbmb/VoxCPM1.5"
        )
    need_mib = VOXCPM2_SAFE_MIB if (args.design or "voxcpm2" in str(model_id).lower()) else VOXCPM15_SAFE_MIB

    with gpu_narrate_lock():
        if args.device != "cpu" and not args.force_gpu:
            g = probe_gpu(samples=3, interval=0.35)
            for _ in range(3):
                if not (g.get("available") and (g.get("busy") or g.get("memory_free_mib", 0) < need_mib)):
                    break
                time.sleep(12.0)
                g = probe_gpu(samples=3, interval=0.35)
            if g.get("available"):
                if g.get("busy") or g.get("memory_free_mib", 0) < need_mib:
                    sys.stderr.write(
                        f"GPU resource guard triggered on {g.get('name')}: "
                        f"utilization {g.get('utilization_percent')}%, free VRAM {g.get('memory_free_mib')} MiB "
                        f"(need >= {need_mib} MiB and < 75% util).\n"
                        f"Action: in an interactive session, inform the user and ask whether to wait, switch to "
                        f"`--engine edge` (zero GPU, exports word timestamps), run `--device cpu`, or pass `--force-gpu`.\n"
                    )
                    raise SystemExit(3)
            elif args.device == "cuda":
                raise SystemExit(f"CUDA requested, but GPU probe reported state={g.get('state')}: {g.get('note', '')}")

        try:
            import torch
            from voxcpm import VoxCPM
        except ImportError:
            raise SystemExit("VoxCPM is not installed here (pip install voxcpm). Use --engine edge, or supply recorded takes.")

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
                pcm, gap, _ = trim(pcm16(wav.tolist()), rate)
                path = temp / f"{key}.take{k}.wav"
                write_wav(path, pcm, rate)
                out.append((path, len(pcm) / (2 * rate), gap, None))
            yield key, line, out, rate


def _parse_vtt_words(vtt_path: Path):
    if not vtt_path.is_file():
        return []
    ts_re = re.compile(r"(\d+):(\d+):(\d+[.,]\d+)\s*-->\s*(\d+):(\d+):(\d+[.,]\d+)")
    def sec(h, m, s):
        return int(h) * 3600 + int(m) * 60 + float(s.replace(",", "."))
    out = []
    lines = vtt_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    i = 0
    while i < len(lines):
        m = ts_re.search(lines[i])
        if m:
            t0 = sec(m.group(1), m.group(2), m.group(3))
            t1 = sec(m.group(4), m.group(5), m.group(6))
            i += 1
            txt = []
            while i < len(lines) and lines[i].strip():
                txt.append(lines[i].strip())
                i += 1
            joined = " ".join(txt).strip()
            if joined:
                out.append({"w": joined, "t0": t0, "t1": t1})
        i += 1
    return out


def edge_takes(cues, temp, args):
    rate = 24000
    is_en = (args.language or guess_language(cues.values())) == "en"
    voice_map = {"teacher": "zh-CN-YunxiNeural", "story": "zh-CN-XiaoxiaoNeural", "promo": "zh-CN-YunjianNeural"}
    fallback = "en-US-AriaNeural" if is_en else voice_map.get(args.voice or "", "zh-CN-YunxiNeural")
    voice = args.voice if args.voice and "Neural" in args.voice else fallback
    try:
        import edge_tts
        has_mod = True
    except ImportError:
        edge_tts = None
        has_mod = False
        edge_cli = shutil.which("edge-tts")
        if not edge_cli:
            raise SystemExit("Install edge-tts in this Python environment or on PATH, or supply recorded takes.")

    async def one(line, mp3):
        for attempt in range(3):
            try:
                audio_bytes = bytearray()
                boundaries = []
                try:
                    comm = edge_tts.Communicate(line, voice, rate=args.rate, boundary="WordBoundary")
                except TypeError:
                    comm = edge_tts.Communicate(line, voice, rate=args.rate)
                async for chunk in comm.stream():
                    ctype = chunk.get("type")
                    if ctype == "audio":
                        audio_bytes.extend(chunk["data"])
                    elif ctype in ("WordBoundary", "SentenceBoundary") and chunk.get("text", "").strip():
                        t0 = chunk["offset"] / 1e7
                        t1 = (chunk["offset"] + chunk["duration"]) / 1e7
                        boundaries.append({"w": chunk["text"].strip(), "t0": t0, "t1": t1})
                mp3.write_bytes(bytes(audio_bytes))
                return boundaries
            except (OSError, RuntimeError, edge_tts.exceptions.EdgeTTSException) as error:
                if attempt == 2:
                    raise RuntimeError(f"Voice request failed: {error}") from error
                await asyncio.sleep(1.5 * (attempt + 1))
        return []

    for key, line in cues.items():
        mp3 = temp / f"{key}.received.mp3"
        if has_mod:
            raw_words = asyncio.run(one(line, mp3))
        else:
            vtt = temp / f"{key}.received.vtt"
            subprocess.run([edge_cli, f"--voice={voice}", f"--rate={args.rate}", "--text", line,
                            f"--write-media={mp3}", f"--write-subtitles={vtt}"], check=True)
            raw_words = _parse_vtt_words(vtt)
        raw = subprocess.check_output([FFMPEG, "-nostdin", "-v", "error", "-i", str(mp3),
                                       "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"])
        pcm, gap, start_sec = trim(raw, rate)
        dur = len(pcm) / (2 * rate)
        path = temp / f"{key}.take0.wav"
        write_wav(path, pcm, rate)
        words = [
            {
                "w": w["w"],
                "t0": round(max(0.0, w["t0"] - start_sec), 3),
                "t1": round(min(dur, max(0.02, w["t1"] - start_sec)), 3),
            }
            for w in raw_words
        ] if raw_words else None
        yield key, line, [(path, dur, gap, words)], rate


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) == 3 and sys.argv[1] == "--transcribe":
        return transcribe_all(sys.argv[2])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--engine", choices=["voxcpm", "edge"], help="default: voxcpm when installed, else edge")
    ap.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto", help="compute device for voxcpm")
    ap.add_argument("--force-gpu", action="store_true", help="bypass GPU busy / free-VRAM safety guard")
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
    ap.add_argument("--no-words", action="store_true", help="skip word-level timestamp extraction")
    ap.add_argument("--style", choices=["auto", "lesson", "free"], default="auto",
                    help="prose style gate: lesson enforces smooth, natural lecturer sentences (default for teacher voice); free skips prose check")
    ap.add_argument("--allow-terse", action="store_true", help="alias for --style free (allow short commercial/poetic fragments)")
    args = ap.parse_args()
    if args.device == "cpu":
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    cues, is_spot = read_cues(args.script)
    prose_issues = lint_cues(cues, is_spot, args)
    if prose_issues:
        sys.stderr.write(
            "Spoken script quality gate failed — the narration reads like choppy, staccato AI/outline copy:\n"
            + "\n".join(prose_issues)
            + "\n\nRewrite cues.json into warm, unhurried, conversational human lecturer sentences "
            "(42–75 Chinese chars per cue, 2–3 complete sentences, natural causal connectors, zero semicolons or roll-call lists), "
            "then re-run narrate.py. (For intentional short-copy ads/trailers only, pass --style free.)\n"
        )
        raise SystemExit(2)

    engine = args.engine
    if not engine:
        try:
            import voxcpm  # noqa: F401
            engine = "voxcpm"
        except ImportError:
            engine = "edge"
            print("VoxCPM not installed: using Microsoft Edge voices (flatter). See references/voice.md.", flush=True)
    args.output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=args.output) as scratch:
        temp = Path(scratch)
        ready = []
        source = voxcpm_takes if engine == "voxcpm" else edge_takes
        rendered = list(source(cues, temp, args))
        language = args.language or guess_language(cues.values())
        transcripts = heard(rendered, temp, language) if args.takes > 1 else {}

        chosen = []
        for key, line, takes, rate in rendered:
            if len(takes) > 1:
                print(f"{key}:", flush=True)
            best = pick(takes, line, transcripts, language)
            chosen.append((key, line, takes[best], rate, len(takes), best))

        if not args.no_words and args.takes == 1:
            need_whisper = [(key, line, [take], rate) for key, line, take, rate, _, _ in chosen if not take[3]]
            if need_whisper:
                transcripts.update(heard(need_whisper, temp, language))

        durs_out = {}
        words_out = {}
        for key, line, take, rate, total_takes, best in chosen:
            path, secs, gap, native_words = take
            name = f"{key}.{args.format}"
            final = temp / name
            if args.format == "wav":
                shutil.copyfile(path, final)
            else:
                subprocess.run([FFMPEG, "-nostdin", "-v", "error", "-y", "-i", str(path),
                                "-c:a", "libmp3lame", "-b:a", "160k", str(final)], check=True)
            ready.append(name)
            durs_out[key] = round(secs, 3)
            wlist = native_words if native_words is not None else transcript_words(transcripts.get(str(path)))
            words_out[key] = {"duration": round(secs, 3), "text": line, "words": wlist}
            flag = f"  ⚠ {gap:.1f} s pause inside — listen" if gap > 1.0 else ""
            wtag = f", {len(wlist)} word cues" if wlist else ""
            print(f"{key}: {secs:.2f} s{f' (take {best + 1} of {total_takes})' if total_takes > 1 else ''}{wtag}{flag}", flush=True)

        for name in ready:
            with NamedTemporaryFile(dir=args.output, delete=False) as sibling:
                staged = Path(sibling.name)
            try:
                shutil.copyfile(temp / name, staged)
                staged.replace(args.output / name)
            finally:
                staged.unlink(missing_ok=True)

        atomic_write_text(
            args.output / "vo.js",
            f"// voice-over clip lengths in seconds, measured by narrate.py\nexport default {json.dumps(durs_out, indent=2)};\n",
        )
        if not args.no_words:
            blob = json.dumps(words_out, ensure_ascii=False, indent=2)
            atomic_write_text(args.output / "words.json", blob + "\n")
            atomic_write_text(
                args.output / "words.js",
                f"// cue durations and word-level timestamps in seconds, exported by narrate.py\nexport default {blob};\n",
            )


if __name__ == "__main__":
    main()
