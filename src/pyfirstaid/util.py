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
    """Normalise a path for comparison: symlinks resolved, case-folded on Windows.

    Resolving symlinks matters on macOS/Homebrew, where e.g.
    /opt/homebrew/opt/python@3.14 links into /opt/homebrew/Cellar/...
    """
    if not path:
        return ""
    return os.path.normcase(os.path.realpath(path))


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


def site_package_dirs() -> List[str]:
    """Existing site-packages directories used by this interpreter (deduplicated)."""
    import site
    import sysconfig

    candidates: List[str] = []
    try:
        candidates.extend(site.getsitepackages())
    except AttributeError:  # very old virtualenv
        pass
    paths = sysconfig.get_paths()
    candidates.extend([paths.get("purelib", ""), paths.get("platlib", "")])
    if site.ENABLE_USER_SITE:
        user_site = site.getusersitepackages()
        if isinstance(user_site, str):
            candidates.append(user_site)

    seen, result = set(), []
    for d in candidates:
        key = norm(d)
        if d and key not in seen and os.path.isdir(d):
            seen.add(key)
            result.append(d)
    return result
