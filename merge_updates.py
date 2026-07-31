#!/usr/bin/env python3
"""Compatibility entry point for ``translation merge``.

Usage: python merge_updates.py <original_dir> <update_dir>

The original two-argument interface is retained. The merge is written back to
``original_dir``; new workflows should use ``souls-translation-tool translation
merge --original ... --update ... --output ...`` instead.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python merge_updates.py <original_dir> <update_dir>")
        return 1

    root = Path(__file__).resolve().parent
    command = [
        "uv",
        "run",
        "--project",
        str(root / "tools/souls-translation-tool"),
        "souls-translation-tool",
        "translation",
        "merge",
        "--original",
        str(Path(sys.argv[1]).resolve()),
        "--update",
        str(Path(sys.argv[2]).resolve()),
        "--output",
        str(Path(sys.argv[1]).resolve()),
    ]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
