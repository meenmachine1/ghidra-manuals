#!/usr/bin/env python3

"""Run ghidra-manuals from a checkout without installing it. See README.md."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ghidra_manuals.cli import main  # noqa: E402

main()
