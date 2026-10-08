"""Check: does the `pip` command install into the Python you are running?"""

from __future__ import annotations

import re
import shutil
import site
import sys
from typing import List, Optional, Tuple

from pyfirstaid.model import Finding, Options, Status
from pyfirstaid.util import is_within, run

CHECK_ID = "pip-mismatch"

_PIP_RE = re.compile(r"^pip (?P<ver>\S+) from (?P<loc>.+?) \(python (?P<py>\d+\.\d+)\)\s*$")


def parse_pip_version(output: str) -> Optional[Tuple[str, str, str]]:
    """Parse `pip --version` output into (pip_version, location, python_version)."""
    for line in output.splitlines():
        m = _PIP_RE.match(line.strip())
        if m:
            return m.group("ver"), m.group("loc"), m.group("py")
    return None


def pip_belongs_here(location: str, pip_python: str, running_python: str,
                     prefixes: List[str]) -> bool:
    """True if a pip install at `location` serves the running interpreter."""
    if pip_python != running_python:
        return False
    return any(is_within(location, p) for p in prefixes if p)


def _allowed_prefixes() -> List[str]:
    prefixes = [sys.prefix]
    if site.ENABLE_USER_SITE:
        user_site = site.getusersitepackages()
        if isinstance(user_site, str):
            prefixes.append(user_site)
    return prefixes


def run_check(opts: Options) -> List[Finding]:
    running = "%d.%d" % sys.version_info[:2]

    code, out, err = run([sys.executable, "-m", "pip", "--version"], opts.timeout)
    if code != 0:
        return [Finding(
            CHECK_ID, Status.ERROR,
            "pip is not installed for this Python",
            detail=(err or out)[-300:],
            fix="python -m ensurepip --upgrade",
        )]

    pip_cmd = shutil.which("pip") or shutil.which("pip3")
    if not pip_cmd:
        return [Finding(
            CHECK_ID, Status.INFO,
            "No `pip` command on PATH (python -m pip works)",
            fix="Use `python -m pip install <package>`. It always targets the right Python.",
        )]

    code, out, err = run([pip_cmd, "--version"], opts.timeout)
    parsed = parse_pip_version(out) if code == 0 else None
    if not parsed:
        return [Finding(
            CHECK_ID, Status.WARN,
            "The `pip` command on PATH is broken",
            detail="%s\n%s" % (pip_cmd, (err or out)[-300:]),
            fix="python -m pip install --force-reinstall pip",
        )]

    _, location, pip_python = parsed
    if pip_belongs_here(location, pip_python, running, _allowed_prefixes()):
        return [Finding(CHECK_ID, Status.OK, "`pip` installs into this Python")]

    return [Finding(
        CHECK_ID, Status.ERROR,
        "`pip` installs into a DIFFERENT Python",
        detail="pip    -> %s (python %s)\npython -> %s (python %s)" % (
            location, pip_python, sys.executable, running),
        fix="Use `python -m pip install <package>` instead of `pip install`. "
            "If a virtual environment should be active, activate it first.",
    )]
