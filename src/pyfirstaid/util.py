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


def read_pyvenv_cfg(prefix: str) -> dict:
    """Key/value pairs from <prefix>/pyvenv.cfg (empty if there is none)."""
    values: dict = {}
    try:
        with open(os.path.join(prefix, "pyvenv.cfg"), encoding="utf-8") as fh:
            for line in fh:
                key, sep, value = line.partition("=")
                if sep:
                    values[key.strip().lower()] = value.strip()
    except OSError:
        pass
    return values


def broken_venv_base(prefix: str) -> Optional[str]:
    """The base Python folder a virtual environment was made from, if it no longer exists.

    A venv only links to its base Python. When that Python is upgraded or removed
    (e.g. `brew upgrade python`), the venv stops working.
    """
    home = read_pyvenv_cfg(prefix).get("home")
    if home and not os.path.isdir(home):
        return home
    return None


def find_upwards(start: str, name: str) -> Optional[str]:
    """Path of the first `name` in `start` or one of its parent folders."""
    current = os.path.abspath(start)
    while True:
        candidate = os.path.join(current, name)
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def read_pyproject(folder: str) -> dict:
    """Parsed pyproject.toml in `folder` ({} if missing or unreadable).

    Uses tomllib on Python 3.11+. On older Pythons a small fallback reads only
    table names and simple `key = "value"` lines, which is all the checks need.
    """
    path = os.path.join(folder, "pyproject.toml")
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return {}
    try:
        import tomllib  # type: ignore[import-not-found]

        return tomllib.loads(raw.decode("utf-8"))
    except ImportError:
        pass
    except Exception:  # noqa: BLE001 - invalid TOML: fall back to the simple reader
        pass
    return _simple_toml(raw.decode("utf-8", "replace"))


def _simple_toml(text: str) -> dict:
    import re

    data: dict = {}
    table = data
    for line in text.splitlines():
        line = line.strip()
        header = re.match(r"^\[([A-Za-z0-9_.\-]+)\]$", line)
        if header:
            table = data
            for part in header.group(1).split("."):
                table = table.setdefault(part, {})
            continue
        kv = re.match(r'^([A-Za-z0-9_\-]+)\s*=\s*["\']([^"\']*)["\']', line)
        if kv:
            table[kv.group(1)] = kv.group(2)
    return data
