"""storyboard.py: checks, voice-over driven timeline, subtitle drafting. Standard library only."""
from contextlib import redirect_stdout
import copy
from importlib import import_module
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "video-craft"
sys.path.insert(0, str(SKILL / "scripts"))
sb = import_module("storyboard")
EXAMPLE = json.loads((SKILL / "assets/storyboard.example.json").read_text(encoding="utf-8"))


def write_wav(path, seconds, rate=16000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\0\0" * int(seconds * rate))


def codes(result, level=None):
    return [i["code"] for i in result["issues"] if level is None or i["level"] == level]


class CheckTests(unittest.TestCase):
    def test_example_is_clean(self):
        result = sb.check(EXAMPLE)
        self.assertEqual(codes(result, "error"), [])
        self.assertEqual(codes(result, "warn"), [])
        self.assertEqual(result["language"], "zh")
        self.assertAlmostEqual(result["total"], 38.0)

    def test_slide_like_storyboard_is_flagged(self):
        board = {
            "format": {"width": 1920, "height": 1080, "fps": 30},
            "language": "zh", "target_duration": 20,
            "shots": [
                {"id": "title", "duration": 3, "layout": "center-hero", "purpose": "标题", "hero": "标题",
                 "transition": "fade", "vo": "今天我们来详细聊一聊关于数据库索引的原理以及它在实际工程中的种种应用场景。"},
                {"id": "points", "duration": 12, "layout": "center-hero", "purpose": "要点", "hero": "列表",
                 "transition": "wipe", "onscreen": ["第一，索引能够极大地提升查询速度", "第二，索引会占用额外的存储空间",
                                                     "第三，写入时需要同步维护索引"]},
                {"id": "summary", "duration": 1, "layout": "center-hero", "transition": "zoom"},
            ],
        }
        result = sb.check(board)
        c = codes(result)
        self.assertIn("vo-fit", c)            # 37 字放不进 3 秒
        self.assertIn("layout-repeat", c)     # 三个相同构图
        self.assertIn("onscreen-amount", c)   # 屏幕文字整句堆叠
        self.assertIn("long-static", c)       # 12 秒没有节拍
        self.assertIn("end-hold", c)          # 结尾 1 秒
        self.assertIn("fields", c)            # summary 缺 purpose/hero
        self.assertIn("carry", c)
        self.assertIn("total", c)             # 16 秒 vs 目标 20 秒

    def test_redundant_onscreen_and_transition_vocabulary(self):
        board = copy.deepcopy(EXAMPLE)
        board["shots"][1]["onscreen"] = ["前一个月几乎看不出变化"]
        board["shots"][2]["transition"] = "spin"
        result = sb.check(board)
        self.assertIn("redundant", codes(result))
        self.assertTrue(any(i["code"] == "transition" and "spin" in i["msg"] for i in result["issues"]))

    def test_missing_duration_without_vo_is_error(self):
        board = {"shots": [{"id": "a", "purpose": "x", "hero": "x", "layout": "type"}]}
        result = sb.check(board)
        self.assertIn("duration", codes(result, "error"))

    def test_duplicate_and_non_ascii_ids(self):
        board = {"shots": [{"id": "镜头一", "duration": 2}, {"id": "镜头一", "duration": 2}]}
        result = sb.check(board)
        self.assertIn("id", codes(result, "warn"))
        self.assertIn("id", codes(result, "error"))

    def test_english_rate(self):
        board = {"language": "en", "shots": [
            {"id": "a", "duration": 2, "purpose": "x", "hero": "x", "layout": "type",
             "vo": "This sentence has exactly ten words in it for testing."}]}
        result = sb.check(board)
        self.assertEqual(result["language"], "en")
        self.assertIn("vo-fit", codes(result))  # 10 words / 2.5 = 4 s > 2 s


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "audio/vo").mkdir(parents=True)
        self.board_path = self.dir / "storyboard.json"
        self.board_path.write_text(json.dumps(EXAMPLE, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_measured_audio_extends_shots_and_frames_add_up(self):
        write_wav(self.dir / "audio/vo/s01-hook.wav", 5.0)     # longer than the planned 4 s
        write_wav(self.dir / "audio/vo/s02-setup.wav", 2.0)    # shorter: planned 5 s kept
        out = self.dir / "timeline.json"
        tl, warnings = sb.build_timeline(EXAMPLE, self.board_path, out, self.dir / "audio/vo")
        s1, s2 = tl["shots"][0], tl["shots"][1]
        self.assertAlmostEqual(s1["duration"], 0.2 + 5.0 + 0.35, places=3)
        self.assertFalse(s1["vo"]["estimated"])
        self.assertEqual(s1["vo"]["file"], "audio/vo/s01-hook.wav")
        self.assertAlmostEqual(s2["duration"], 5.0, places=3)
        self.assertAlmostEqual(s2["vo"]["start"], s2["start"] + 0.2, places=3)
        self.assertTrue(s2["vo"]["start_frame"] >= s2["from"])
        self.assertEqual(sum(s["durationInFrames"] for s in tl["shots"]), tl["duration_frames"])
        for a, b in zip(tl["shots"], tl["shots"][1:]):
            self.assertEqual(a["from"] + a["durationInFrames"], b["from"])
            self.assertAlmostEqual(a["end"], b["start"], places=4)
        self.assertEqual(tl["cuts"], [s["end"] for s in tl["shots"][:-1]])
        self.assertTrue(any("已延长" in w for w in warnings))
        # estimated shots are flagged as such
        self.assertTrue(tl["shots"][2]["vo"]["estimated"])
        self.assertIsNone(tl["shots"][2]["vo"]["file"])

    def test_beats_and_sfx_become_absolute(self):
        tl, _ = sb.build_timeline(EXAMPLE, self.board_path, self.dir / "t.json")
        s3 = tl["shots"][2]
        self.assertAlmostEqual(s3["beats"][-1]["at"], s3["start"] + 4.9, places=3)
        self.assertEqual(s3["sfx"][0]["name"], "hit")
        self.assertEqual(s3["sfx"][0]["frame"], int(round((s3["start"] + 4.9) * 30)))

    def test_last_shot_without_vo_keeps_planned_hold(self):
        tl, _ = sb.build_timeline(EXAMPLE, self.board_path, self.dir / "t.json")
        self.assertAlmostEqual(tl["shots"][-1]["duration"], 3.0, places=3)

    def test_cli_writes_file(self):
        out = self.dir / "sub/timeline.json"
        buf = io.StringIO()
        argv = sys.argv
        sys.argv = ["storyboard.py", "timeline", str(self.board_path), "--out", str(out)]
        try:
            with redirect_stdout(buf):
                sb.main()
        finally:
            sys.argv = argv
        self.assertTrue(out.is_file())
        self.assertIn("估算 6 段", buf.getvalue())


class SubtitleTests(unittest.TestCase):
    def timeline(self, text, duration=6.0, lang="zh"):
        return {"language": lang, "fps": 30, "shots": [
            {"id": "a", "start": 0.0, "end": duration + 0.6,
             "vo": {"text": text, "start": 0.2, "duration": duration, "estimated": False}}]}

    def test_lines_fit_and_punctuation_is_cleaned(self):
        text = "前一个月，几乎看不出变化，只到一点三五。但每天都在前一天的基础上再长一点，一年后，是三十七点八。"
        cues, warnings = sb.build_subtitles(self.timeline(text, 11.0))
        for c in cues:
            self.assertLessEqual(sb.display_width(c["text"]), 16)
            self.assertFalse(c["text"].endswith(("，", "。")))
            self.assertNotIn("，", c["text"])
        for a, b in zip(cues, cues[1:]):
            self.assertLess(a["end"], b["start"] + 1e-9)
            self.assertGreaterEqual(b["start"] - a["end"], 2 / 30 - 0.001)
        self.assertAlmostEqual(cues[0]["start"], 0.2, places=3)

    def test_question_mark_kept(self):
        cues, _ = sb.build_subtitles(self.timeline("每天进步百分之一，一年后是多少？", 3.5))
        self.assertTrue(cues[-1]["text"].endswith("？"))

    def test_long_clause_is_split_and_reported(self):
        text = "这是一句没有任何标点但是长度明显超过十六个汉字限制的旁白文字"
        cues, warnings = sb.build_subtitles(self.timeline(text, 7.0))
        self.assertGreaterEqual(len(cues), 2)
        self.assertTrue(all(sb.display_width(c["text"]) <= 16.5 for c in cues))
        self.assertTrue(any("没有标点的位置断行" in w for w in warnings))

    def test_latin_words_not_broken(self):
        text = "我们用 Remotion 和 HyperFrames 渲染视频，再用 ffmpeg 合成声音和字幕文件"
        cues, _ = sb.build_subtitles(self.timeline(text, 7.0))
        joined = " ".join(c["text"] for c in cues)
        for word in ("Remotion", "HyperFrames", "ffmpeg"):
            self.assertIn(word, joined)

    def test_english_cues(self):
        text = ("Every day you get one percent better, and after a year the curve has bent upward "
                "far beyond what most people would guess.")
        cues, _ = sb.build_subtitles(self.timeline(text, 8.0, "en"), max_chars=42)
        self.assertTrue(all(len(c["text"]) <= 42 for c in cues))

    def test_too_fast_is_reported(self):
        cues, warnings = sb.build_subtitles(self.timeline("一二三四五六七八九十一二三四五六", 1.0))
        self.assertTrue(any("阅读速度" in w or "0.83" in w for w in warnings))

    def test_vertical_default_is_14(self):
        tl = self.timeline("前一个月几乎看不出任何变化，只到一点三五。", 5.0)
        tl.update({"width": 1080, "height": 1920})
        cues, _ = sb.build_subtitles(tl)
        self.assertTrue(all(sb.display_width(c["text"]) <= 14 for c in cues))

    def test_srt_format(self):
        cues, _ = sb.build_subtitles(self.timeline("你好，世界。", 2.0))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.srt"
            sb.write_srt(cues, p)
            text = p.read_text(encoding="utf-8")
        self.assertRegex(text, r"^1\n00:00:00,200 --> 00:00:0\d,\d{3}\n")
        self.assertEqual(sb.srt_time(3661.5), "01:01:01,500")


if __name__ == "__main__":
    unittest.main()
