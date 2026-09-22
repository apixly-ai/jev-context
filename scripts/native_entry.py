"""Entrypoint for self-contained CLI distributions."""

import os
import sys
from pathlib import Path

from jev_context.cli import entrypoint

if getattr(sys, "frozen", False):
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")
raise SystemExit(entrypoint())
