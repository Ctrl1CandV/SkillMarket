"""Rebuild narration and picture cues together; Python stdlib + FFmpeg.

Without --takes, Windows' installed Mandarin voice reads each line. To use an
actor or another platform, record one WAV per spoken cue using --print-script.
"""
import argparse
import base64
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave

BASE = Path(__file__).resolve().parent
NUM = "零一二三四五六七八九"
FPS = 24
FFMPEG = os.environ.get("VC_FFMPEG", "ffmpeg")


def trace(coin):
    if type(coin) is not int or not 1 <= coin <= 9:
        raise ValueError("example and practice must be between 1 and 9")
    group, position = divmod(coin - 1, 3)
    candidates = list(range(3 * group + 1, 3 * group + 4))
    side = ["左盘高", "右盘高", "两盘一样高"]
    reasons = [
        "两盘枚数相同。左边被抬高，轻币就在左盘的三枚里。",
        "两盘枚数相同。右边被抬高，轻币就在右盘的三枚里。",
        "天平两边一样重，所以轻币就在留在盘外的三枚里。",
    ]
    a, b, _ = [NUM[n] for n in candidates]
    return dict(answer=coin, group=group, position=position, coins=candidates,
                first="看横梁，" + side[group], first_short=side[group],
                reason=reasons[group], a=a, b=b, second=side[position],
                candidates="、".join(NUM[n] + "号" for n in candidates),
                test=[f"{a}号和{b}号上盘，左盘高", f"{a}号和{b}号上盘，右盘高",
                      f"{a}号和{b}号一样重"][position],
                proof=[f"左盘升高，盘里只有{a}号。",
                       f"右盘升高，盘里只有{b}号。",
                       "天平上的两枚一样重，轻的就是留在盘外的那一枚。"][position])


def variant_coin(value, field):
    sides = ["左盘高", "右盘高", "两盘平"]
    if not isinstance(value, list) or len(value) != 2 or any(side not in sides for side in value):
        raise ValueError(f"{field} 应按 [第一称, 第二称] 填写，取值仅为：左盘高 / 右盘高 / 两盘平")
    return 3 * sides.index(value[0]) + sides.index(value[1]) + 1


def read_plan(variant=None):
    data = json.loads((BASE / "lesson.json").read_text(encoding="utf-8"))
    if variant is not None:
        edits = json.loads(variant.read_text(encoding="utf-8-sig"))
        required = {"example", "practice", "thinkingSeconds", "ask"}
        if not isinstance(edits, dict) or set(edits) != required:
            raise ValueError("变体需要四个字段：example, practice, thinkingSeconds, ask")
        for name in ["example", "practice"]:
            data[name] = variant_coin(edits[name], name)
        data["thinkingSeconds"] = edits["thinkingSeconds"]
        if not isinstance(edits["ask"], str) or "{q_test}" not in edits["ask"]:
            raise ValueError("ask 应是一句含有 {q_test} 的提问")
        for cue in data["cues"]:
            if cue[0] == "ask":
                cue[1] = edits["ask"]
    example, practice = trace(data["example"]), trace(data["practice"])
    fields = {}
    for pre, case in [("e", example), ("q", practice)]:
        fields.update({f"{pre}_{k}": v for k, v in case.items()})
        fields[f"{pre}_answer"] = NUM[case["answer"]]
    script = [(key, line.format(**fields)) for key, line in data["cues"]]
    pause = float(data["thinkingSeconds"])
    if not math.isfinite(pause) or pause <= 0:
        raise ValueError("thinkingSeconds must be a positive finite duration")
    return example, practice, pause, script


def synthesize(script, temp):
    voices = temp / "lines.json"
    voices.write_text(json.dumps(dict(script), ensure_ascii=False), encoding="utf-8")
    command = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$syn = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voice = $syn.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'zh-CN' } | Select-Object -First 1
if (-not $voice) { throw 'No zh-CN voice. Supply your recordings with --takes.' }
$syn.SelectVoice($voice.VoiceInfo.Name)
$syn.Rate = 1
$lines = Get-Content -Raw -Encoding utf8 -LiteralPath $env:LESSON_LINES | ConvertFrom-Json
foreach ($line in $lines.PSObject.Properties) {
  if ($line.Value) {
    $file = Join-Path (Split-Path $env:LESSON_LINES) ($line.Name + '.wav')
    $syn.SetOutputToWaveFile($file)
    $syn.Speak([string]$line.Value)
    $syn.SetOutputToNull()
  }
}
$syn.Dispose()
"""
    encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")
    shell = shutil.which("pwsh") or "powershell.exe"
    subprocess.run([shell, "-NoProfile", "-EncodedCommand", encoded],
                   env={**os.environ, "LESSON_LINES": str(voices)}, check=True)


def build(takes, dest, variant):
    example, practice, pause, script = read_plan(variant)
    dest.mkdir(parents=True, exist_ok=True)
    rate = 24000
    with tempfile.TemporaryDirectory() as work:
        temp = Path(work)
        if takes is None:
            synthesize(script, temp)
        source = takes or temp
        mix = bytearray()
        cues = []
        for name, line in script:
            start = len(mix) / (rate * 2)
            audio = b""
            if line:
                audio = subprocess.check_output([
                    FFMPEG, "-hide_banner", "-loglevel", "error", "-i", str(source / (name + ".wav")),
                    "-af", "silenceremove=start_periods=1:start_threshold=-55dB:start_silence=0.035",
                    "-ar", str(rate), "-ac", "1", "-f", "s16le", "pipe:1"])
            voice_end = start + len(audio) / (rate * 2)
            if line and len(audio) < rate // 4:
                raise ValueError(f"No usable voice in {name}.wav")
            frames = math.ceil((voice_end - start + (0.34 if line else pause)) * FPS)
            if name in ("found", "solve", "rule"):
                frames += 16
            mix.extend(audio)
            mix.extend(bytes(frames * (rate // FPS) * 2 - len(audio)))
            cues.append(dict(id=name, text=line, start=start, voiceEnd=voice_end, end=len(mix) / (rate * 2)))
        wav = temp / "narration.wav"
        with wave.open(str(wav), "wb") as file:
            file.setparams((1, 2, rate, 0, "NONE", "not compressed"))
            file.writeframes(mix)
        subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav),
                        "-af", "loudnorm=I=-17:TP=-2:LRA=11", "-ar", "48000",
                        "-c:a", "aac", "-b:a", "80k", str(dest / "voice.m4a")], check=True)
    timeline = dict(width=1280, height=720, fps=FPS, duration=cues[-1]["end"],
                    example=example, practice=practice, cues=cues)
    (dest / "timing.js").write_text("window.LESSON = " + json.dumps(timeline, indent=2, ensure_ascii=False) + ";\n", encoding="utf-8")
    if dest.resolve() != BASE:
        for name in ["index.html", "scene.js"]:
            shutil.copy2(BASE / name, dest / name)
    for cue in cues:
        print(f"{cue['start']:6.2f}–{cue['end']:6.2f}  {cue['id']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--takes", type=Path, help="directory of recordings, e.g. ask.wav")
    parser.add_argument("--print-script", action="store_true")
    parser.add_argument("--out", type=Path, default=BASE)
    parser.add_argument("--variant", type=Path, help="four-field card describing scale outcomes")
    options = parser.parse_args()
    if options.print_script:
        for cue_id, sentence in read_plan(options.variant)[3]:
            if sentence:
                print(cue_id, sentence)
    else:
        build(options.takes, options.out, options.variant)
