"""Build dist/pyfirstaid.pyz: a single file that runs with `python pyfirstaid.pyz`.

It needs no installation, so it works even when pip is broken.
Usage: python scripts/build_pyz.py
"""

import shutil
import tempfile
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    target = dist / "pyfirstaid.pyz"
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copytree(ROOT / "src" / "pyfirstaid", Path(tmp) / "pyfirstaid",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        zipapp.create_archive(tmp, target, interpreter="/usr/bin/env python3",
                              main="pyfirstaid.cli:_run")
    print("built", target)


if __name__ == "__main__":
    main()
