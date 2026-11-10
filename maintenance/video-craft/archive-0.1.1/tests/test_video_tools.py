"""video_qa.py and mix_audio.py: pure helpers always; end-to-end runs only when ffmpeg/ffprobe exist."""
from importlib import import_module
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "video-craft"
sys.path.insert(0, str(SKILL / "scripts"))
qa = import_module("video_qa")
mix = import_module("mix_audio")

FFMPEG = os.environ.get("VIDEO_CRAFT_FFMPEG") or shutil.which("ffmpeg")
FFPROBE = os.environ.get("VIDEO_CRAFT_FFPROBE") or shutil.which("ffprobe")
HAVE_FF = bool(FFMPEG and FFPROBE)


def box(kind, payload=b""):
    return struct.pack(">I4s", 8 + len(payload), kind) + payload


class PureHelperTests(unittest.TestCase):
    def test_mp4_box_order(self):
        with tempfile.TemporaryDirectory() as d:
            slow = Path(d) / "slow.mp4"
            slow.write_bytes(box(b"ftyp", b"isom") + box(b"mdat", b"\0" * 32) + box(b"moov", b"\0" * 8))
            fast = Path(d) / "fast.mp4"
            fast.write_bytes(box(b"ftyp", b"isom") + box(b"moov", b"\0" * 8) + box(b"mdat", b"\0" * 32))
            self.assertEqual(qa.mp4_top_boxes(slow), ["ftyp", "mdat", "moov"])
            self.assertEqual(qa.mp4_top_boxes(fast), ["ftyp", "moov", "mdat"])

    def test_flash_detection(self):
        fps = 30.0
        ys = [40.0] * 30 + [230.0] + [40.0] * 30          # one white frame
        ys += [40.0] * 5 + [200.0] * 40                   # a hard cut to a bright scene is not a flash
        yavg = [(i / fps, y) for i, y in enumerate(ys)]
        flashes = qa.find_flashes(yavg, fps)
        self.assertEqual(len(flashes), 1)
        self.assertAlmostEqual(flashes[0]["time"], 1.0, places=2)
        self.assertEqual(flashes[0]["kind"], "bright")

    def test_dark_dip_detection(self):
        ys = [180.0] * 10 + [16.0, 16.0] + [180.0] * 10
        flashes = qa.find_flashes([(i / 30.0, y) for i, y in enumerate(ys)], 30.0)
        self.assertEqual([f["kind"] for f in flashes], ["dark"])
        self.assertEqual(flashes[0]["frames"], 2)

    def test_load_timeline_uses_exact_frames(self):
        tl = {"fps": 30, "width": 1080, "height": 1920, "duration": 9.05,
              "shots": [{"id": "a", "start": 0, "end": 4.05, "from": 0, "durationInFrames": 121},
                        {"id": "b", "start": 4.05, "end": 9.05, "from": 121, "durationInFrames": 151}]}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.json"
            p.write_text(json.dumps(tl))
            loaded = qa.load_timeline(p)
        self.assertAlmostEqual(loaded["cuts"][0], 121 / 30.0)
        self.assertEqual(loaded["width"], 1080)

    def test_load_storyboard_accumulates(self):
        board = json.loads((SKILL / "assets/storyboard.example.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            p.write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
            loaded = qa.load_timeline(p)
        self.assertEqual(len(loaded["shots"]), 7)
        self.assertAlmostEqual(loaded["shots"][-1]["end"], 38.0)
        self.assertEqual(loaded["width"], 1080)

    def test_frame_seek_lands_inside_frame(self):
        seek, actual = qa.frame_seek_time(4.0, 30.0, 10.0)
        self.assertAlmostEqual(actual, 4.0)
        self.assertLess(seek, 4.0)
        self.assertGreater(seek, 4.0 - 1 / 30.0)
        _, last = qa.frame_seek_time(99.0, 30.0, 10.0)
        self.assertAlmostEqual(last, 299 / 30.0)

    def test_sheet_times_from_timeline(self):
        tl = {"shots": [{"id": "a", "start": 0.0, "end": 1.0}, {"id": "b", "start": 1.0, "end": 5.0}]}
        pts = qa.sheet_times({"duration": 5.0}, tl)
        self.assertEqual([lbl for _, lbl in pts], ["a mid", "b mid", "b end"])
        pts = qa.sheet_times({"duration": 10.0}, None, every=2.0)
        self.assertEqual(len(pts), 5)

    def test_filter_quote_escapes_colon(self):
        self.assertEqual(qa.filter_quote("C:\\Windows\\Fonts\\a.ttf"), "'C\\:/Windows/Fonts/a.ttf'")

    def test_mix_graph_ducks_music_under_voice(self):
        args = types.SimpleNamespace(no_duck=False, music_fade_in=1.0, music_fade_out=2.0)
        sources = [
            {"kind": "vo", "path": Path("a.wav"), "start": 0.2, "gain_db": 1.5, "label": "a"},
            {"kind": "vo", "path": Path("b.wav"), "start": 4.0, "gain_db": -0.5, "label": "b"},
            {"kind": "music", "path": Path("m.mp3"), "start": 0.0, "gain_db": -12.0, "label": "m"},
            {"kind": "sfx", "path": Path("w.wav"), "start": 3.9, "gain_db": -20.0, "label": "w"},
        ]
        inputs, lines, final = mix.build_graph(sources, 10.0, args, True)
        graph = ";".join(lines)
        self.assertEqual(inputs.count("-stream_loop"), 1)
        self.assertIn("adelay=200|200", graph)
        self.assertIn("adelay=4000|4000", graph)
        self.assertIn("sidechaincompress", graph)
        self.assertIn("[musicbus][vosc]", graph)
        self.assertIn("normalize=0", graph)
        self.assertIn("atrim=0:10.000", graph)
        self.assertEqual(final, "mix")

    def test_mix_graph_without_normalize_option_compensates(self):
        args = types.SimpleNamespace(no_duck=True, music_fade_in=1.0, music_fade_out=2.0)
        sources = [{"kind": "vo", "path": Path("a.wav"), "start": 0, "gain_db": 0, "label": "a"},
                   {"kind": "vo", "path": Path("b.wav"), "start": 3, "gain_db": 0, "label": "b"}]
        _, lines, _ = mix.build_graph(sources, 6.0, args, False)
        self.assertIn("amix=inputs=2:duration=longest,volume=2", ";".join(lines))


def ff(*args, cwd=None):
    subprocess.run([FFMPEG, "-hide_banner", "-v", "error", "-y"] + list(args), check=True, cwd=cwd)


@unittest.skipUnless(HAVE_FF, "ffmpeg/ffprobe not available")
class EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        cls.dir = d
        # 0–2 s moving pattern | 2–4.5 s frozen solid colour | 4.5–7 s moving pattern with a 1-frame white flash
        ff("-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=2", "-f", "lavfi", "-i", "color=c=0x2050a0:s=640x360:r=30:d=2.5",
           "-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=2.5",
           "-f", "lavfi", "-i", "aevalsrc='0.2*sin(2*PI*440*t)*(lt(t,2)+gt(t,4.5))':s=48000:d=7",
           "-filter_complex",
           "[2:v]drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='between(t,1.0,1.02)'[c];"
           "[0:v][1:v][c]concat=n=3:v=1:a=0,format=yuv420p[v]",
           "-map", "[v]", "-map", "3:a", "-c:v", "libx264", "-crf", "20", "-c:a", "aac", str(d / "test.mp4"))
        tl = {"fps": 30, "width": 640, "height": 360, "duration": 7.0,
              "shots": [{"id": "a", "start": 0.0, "end": 2.0, "from": 0, "durationInFrames": 60},
                        {"id": "b", "start": 2.0, "end": 4.5, "from": 60, "durationInFrames": 75},
                        {"id": "c", "start": 4.5, "end": 7.0, "from": 135, "durationInFrames": 75}]}
        (d / "timeline.json").write_text(json.dumps(tl))
        out = subprocess.run([sys.executable, "-B", str(SKILL / "scripts/video_qa.py"), "all", str(d / "test.mp4"),
                              "--timeline", str(d / "timeline.json"), "--out", str(d / "qa")],
                             capture_output=True, text=True)
        cls.stdout, cls.stderr, cls.code = out.stdout, out.stderr, out.returncode
        cls.report = json.loads((d / "qa/report.json").read_text(encoding="utf-8")) if cls.code == 0 else None

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_runs(self):
        self.assertEqual(self.code, 0, self.stderr)

    def test_probe(self):
        p = self.report["probe"]
        self.assertEqual(p["video"]["width"], 640)
        self.assertAlmostEqual(p["video"]["fps"], 30.0)
        self.assertAlmostEqual(p["duration"], 7.0, delta=0.1)

    def test_flash_freeze_and_cuts(self):
        det = self.report["detect"]
        self.assertTrue(any(abs(f["time"] - 5.5) < 0.1 for f in det["flashes"]), det["flashes"])
        self.assertTrue(any(f["start"] < 2.2 and f["duration"] >= 2.0 for f in det["freeze"]), det["freeze"])
        matched = [m for m in det["cut_match"] if m["detected"] is not None]
        self.assertEqual(len(matched), 2, det["cut_match"])
        codes = [c["code"] for c in self.report["checks"]]
        self.assertIn("flash", codes)
        self.assertIn("freeze", codes)

    def test_audio_measured(self):
        det = self.report["detect"]
        self.assertIsNotNone(det["loudness"])
        self.assertTrue(any(1.8 < s["start"] < 2.3 and s["duration"] > 2.0 for s in det["silence"]), det["silence"])

    def test_images_written(self):
        qa_dir = self.dir / "qa"
        self.assertTrue(list(qa_dir.glob("sheet-*.jpg")))
        self.assertEqual(len(list((qa_dir / "cuts").glob("cut-*.jpg"))), 2)
        self.assertEqual(len(list((qa_dir / "entries").glob("entry-*.jpg"))), 3)
        self.assertFalse(list(qa_dir.glob(".*")), "temporary folders should be removed")
        index = json.loads(next(qa_dir.glob("sheet-index.json")).read_text(encoding="utf-8"))
        self.assertEqual(len(index["cells"]), 6)  # mid + end for each 2–2.5 s shot

    def test_mix_audio_end_to_end(self):
        d = self.dir
        (d / "vo").mkdir(exist_ok=True)
        ff("-f", "lavfi", "-i", "sine=f=300:d=1.5", "-af", "volume=-12dB", str(d / "vo/a.wav"))
        ff("-f", "lavfi", "-i", "sine=f=500:d=1.0", "-af", "volume=-26dB", str(d / "vo/b.wav"))
        ff("-f", "lavfi", "-i", "sine=f=200:d=3", "-af", "volume=-6dB", str(d / "music.wav"))
        ff("-f", "lavfi", "-i", "anoisesrc=d=0.3:a=0.5", str(d / "whoosh.wav"))
        tl = {"fps": 30, "duration": 7.0, "shots": [
            {"id": "a", "start": 0, "end": 2, "vo": {"file": "vo/a.wav", "start": 0.2, "duration": 1.5}},
            {"id": "b", "start": 2, "end": 7, "vo": {"file": "vo/b.wav", "start": 4.6, "duration": 1.0},
             "sfx": [{"at": 4.5, "name": "whoosh", "gain": -14}]}]}
        (d / "mix-timeline.json").write_text(json.dumps(tl))
        out = subprocess.run([sys.executable, "-B", str(SKILL / "scripts/mix_audio.py"), "--video", str(d / "test.mp4"),
                              "--timeline", str(d / "mix-timeline.json"), "--music", str(d / "music.wav"),
                              "--sfx-dir", str(d), "--out", str(d / "final.mp4")], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        qa.FFMPEG, qa.FFPROBE = FFMPEG, FFPROBE
        mix.FFMPEG, mix.FFPROBE = FFMPEG, FFPROBE
        info = qa.probe(d / "final.mp4")
        self.assertEqual(info["audio"]["sample_rate"], 48000)
        self.assertAlmostEqual(info["duration"], 7.0, delta=0.1)
        self.assertEqual(info["video"]["codec"], "h264")
        self.assertNotIn("faststart", [c["code"] for c in info["checks"]])
        i, tp = mix.loudness(d / "final.mp4")
        self.assertAlmostEqual(i, -14.0, delta=1.0)
        self.assertLessEqual(tp, -0.5)


if __name__ == "__main__":
    unittest.main()
