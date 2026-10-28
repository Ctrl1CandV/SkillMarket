#!/usr/bin/env python3
"""Entry point for the docvision skill.

Run with any Python >= 3.10.  The core path uses only the standard library;
local OCR engines live in isolated environments.  If page rendering is
requested, install the small core extras with `docvision setup --profile core`.
"""

from __future__ import annotations

import sys
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

if __name__ == "__main__":
    from dv import util
    core_command = util.core_reexec_command(sys.argv[1:])
    if core_command:
        env = os.environ.copy()
        env["DOCVISION_CORE_ACTIVE"] = "1"
        # Preserve inherited engine settings; -s isolates this core Python only.
        sys.exit(subprocess.call(core_command, env=env))
    from dv.cli import main
    sys.exit(main())
