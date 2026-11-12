"""GPU probe: tell "no tool found" apart from "tool found but GPU unreachable" (WSL, sandboxes)."""
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'docvision' / 'scripts'))
from dv import doctor, util


def completed(code, out='', err=''):
    return subprocess.CompletedProcess(['nvidia-smi'], code, out, err)


class GpuProbe(unittest.TestCase):
    def test_missing_tool_is_not_detected(self):
        with patch.object(util, 'find_nvidia_smi', return_value=None):
            info = util.gpu_summary()
        self.assertEqual((info['available'], info['state']), (False, 'not_detected'))

    def test_wsl_driver_directory_is_used_when_path_has_no_tool(self):
        with patch.object(util.shutil, 'which', return_value=None), \
             patch.object(util.os.path, 'isfile', side_effect=lambda p: p == util.NVIDIA_SMI_FALLBACKS[0]), \
             patch.object(util.os, 'access', return_value=True):
            self.assertEqual(util.find_nvidia_smi(), util.NVIDIA_SMI_FALLBACKS[0])

    def test_blocked_gpu_is_present_but_inaccessible_and_plan_says_so(self):
        blocked = completed(255, '', 'Failed to initialize NVML: GPU access blocked by the operating system\n')
        with patch.object(util, 'find_nvidia_smi', return_value='/usr/lib/wsl/lib/nvidia-smi'), \
             patch.object(util, 'run', return_value=blocked):
            info = util.gpu_summary()
        self.assertEqual((info['available'], info['state']), (False, 'present_but_inaccessible'))
        self.assertIn('blocked', info['detail'])
        plan = doctor.hardware_plan({'os': 'Linux', 'machine': 'x86_64'}, 32.0, info, {})
        self.assertEqual(plan['paddle_device'], 'cpu')
        self.assertTrue(any('ordinary terminal' in note for note in plan['notes']))

    def test_not_detected_plan_has_no_sandbox_note(self):
        plan = doctor.hardware_plan({'os': 'Linux', 'machine': 'x86_64'}, 32.0,
                                    {'available': False, 'state': 'not_detected'}, {})
        self.assertFalse(any('ordinary terminal' in note for note in plan['notes']))

    def test_working_gpu_keeps_fields(self):
        ok = completed(0, 'NVIDIA GeForce RTX 4060 Laptop GPU, 8188 MiB, 610.57\n')
        with patch.object(util, 'find_nvidia_smi', return_value='nvidia-smi'), \
             patch.object(util, 'run', return_value=ok):
            info = util.gpu_summary()
        self.assertEqual((info['available'], info['state']), (True, 'ok'))
        self.assertEqual(info['gpus'][0]['vram'], '8188 MiB')


if __name__ == '__main__':
    unittest.main()
