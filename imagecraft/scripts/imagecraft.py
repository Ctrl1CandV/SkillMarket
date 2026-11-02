#!/usr/bin/env python3
"""Run with Python 3.10+, preferably the selected existing ComfyUI interpreter."""
import sys

if sys.version_info < (3, 10):
    raise SystemExit("imagecraft requires Python 3.10+; no environment changes were made")

sys.dont_write_bytecode = True
for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure:
        reconfigure(encoding="utf-8")

from ic.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
