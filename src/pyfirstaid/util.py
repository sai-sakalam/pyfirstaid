"""Small helpers used by checks. Standard library only."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import List, Optional, Tuple


def run(cmd: List[str], timeout: float = 15.0) -> Tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr).

    Never raises: a missing executable or a timeout returns code 127 / 124.
    """
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1"},
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", "executable not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timed out after %ss" % timeout
    except OSError as exc:
        return 126, "", str(exc)


def norm(path: Optional[str]) -> str:
    """Normalise a path for comparison (absolute, resolved case on Windows)."""
    if not path:
        return ""
    return os.path.normcase(os.path.abspath(path))


def is_within(path: str, parent: str) -> bool:
    path, parent = norm(path), norm(parent)
    if not path or not parent:
        return False
    try:
        return os.path.commonpath([path, parent]) == parent
    except ValueError:  # different drives on Windows
        return False


def in_virtualenv() -> bool:
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)
