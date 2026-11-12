from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "imagecraft/scripts"))
from ic import common


def completed(code, out="", err=""):
    return subprocess.CompletedProcess(["nvidia-smi"], code, out, err)


class GpuProbe(unittest.TestCase):
    def test_missing_tool_is_not_detected_rather_than_no_gpu(self):
        with patch.object(common, "find_nvidia_smi", return_value=None):
            info = common.gpu_info()
        self.assertEqual((info["available"], info["state"]), (False, "not_detected"))
        self.assertIn("does not prove", info["note"])

    def test_wsl_driver_directory_is_used_when_path_has_no_tool(self):
        with patch.object(common.shutil, "which", return_value=None), \
             patch.object(common.os.path, "isfile", side_effect=lambda p: p == common.NVIDIA_SMI_FALLBACKS[0]), \
             patch.object(common.os, "access", return_value=True):
            self.assertEqual(common.find_nvidia_smi(), common.NVIDIA_SMI_FALLBACKS[0])

    def test_blocked_gpu_is_reported_as_present_but_inaccessible(self):
        blocked = completed(255, "", "Failed to initialize NVML: GPU access blocked by the operating system\n")
        with patch.object(common, "find_nvidia_smi", return_value="/usr/lib/wsl/lib/nvidia-smi"), \
             patch.object(common.subprocess, "run", return_value=blocked):
            info = common.gpu_info()
        self.assertEqual((info["available"], info["state"]), (False, "present_but_inaccessible"))
        self.assertIn("blocked", info["detail"])
        self.assertIn("ordinary terminal", info["note"])

    def test_working_gpu_keeps_the_existing_fields(self):
        ok = completed(0, "NVIDIA GeForce RTX 4060 Laptop GPU, 8188, 512, 610.57\n")
        with patch.object(common, "find_nvidia_smi", return_value="nvidia-smi"), \
             patch.object(common.subprocess, "run", return_value=ok):
            info = common.gpu_info()
        self.assertEqual((info["available"], info["state"], info["memory_unit"]), (True, "ok", "MiB"))
        self.assertEqual(len(info["nvidia_smi"]), 1)

    def test_timeout_is_inaccessible_not_a_crash(self):
        with patch.object(common, "find_nvidia_smi", return_value="nvidia-smi"), \
             patch.object(common.subprocess, "run", side_effect=subprocess.TimeoutExpired("nvidia-smi", 10)):
            self.assertEqual(common.gpu_info()["state"], "present_but_inaccessible")



class GpuLoadGate(unittest.TestCase):
    """2026-11-12: a model generated while the user's Ollama held the GPU at 90%; generate now refuses first."""

    def load(self, line):
        with patch.object(common, "find_nvidia_smi", return_value="nvidia-smi"), \
             patch.object(common.subprocess, "run", return_value=completed(0, line + "\n")), \
             patch("time.sleep"):
            return common.gpu_load()

    def test_sustained_utilization_is_busy(self):
        load = self.load("92, 8823, 16376")
        self.assertTrue(load["busy"])
        self.assertEqual((load["utilization_percent"], load["memory_used_mib"]), (92, 8823))

    def test_idle_desktop_with_loaded_models_is_not_busy(self):
        self.assertFalse(self.load("4, 12000, 16376")["busy"])

    def test_unmeasurable_gpu_does_not_block(self):
        with patch.object(common, "find_nvidia_smi", return_value=None):
            self.assertIsNone(common.gpu_load())
        self.assertIsNone(self.load("[N/A], [N/A], 16376"))

    def test_generate_refuses_before_creating_the_job_unless_allowed(self):
        import io, json, tempfile
        from ic import cli
        busy = {"utilization_percent": 90, "memory_used_mib": 9000, "memory_total_mib": 16376, "busy": True}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "job"
            cfg = {"url": "http://127.0.0.1:8189"}
            with patch.object(cli, "config", return_value=cfg), patch.object(cli, "gpu_load", return_value=busy), \
                 patch.object(cli.jobs, "submit") as submit, patch("sys.stdout", new=io.StringIO()) as stdout:
                code = cli.main(["generate", "--prompt", "cup", "--output", str(out), "--wait", "1"])
            self.assertEqual(code, 2)
            self.assertIn("GPU is busy", json.loads(stdout.getvalue())["error"])
            submit.assert_not_called()
            self.assertFalse(out.exists())
            with patch.object(cli, "config", return_value=cfg), patch.object(cli, "gpu_load") as probe, \
                 patch.object(cli.jobs, "submit", side_effect=common.Error("stop after the gate")) as submit, \
                 patch("sys.stdout", new=io.StringIO()):
                cli.main(["generate", "--prompt", "cup", "--output", str(out), "--wait", "1", "--allow-busy-gpu"])
            probe.assert_not_called()
            submit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
