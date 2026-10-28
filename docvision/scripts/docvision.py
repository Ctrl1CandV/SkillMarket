#!/usr/bin/env python3
"""Entry point for the docvision skill.

Run with any Python >= 3.10.  The core path uses only the standard library;
local OCR engines live in isolated environments.  If page rendering is
requested, install the small core extras with `docvision setup --profile core`.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from dv.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
