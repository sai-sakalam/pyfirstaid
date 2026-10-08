"""Check: dependency conflicts reported by `pip check`."""

from __future__ import annotations

import re
import sys
from typing import List

from pyfirstaid.model import Finding, Options, Status
from pyfirstaid.util import in_virtualenv, run

CHECK_ID = "dependencies"

_MISSING_RE = re.compile(r"requires (?P<req>[^,]+), which is not installed")
_WRONG_RE = re.compile(r"has requirement (?P<spec>.+?), but you have ")


def fix_for(line: str) -> str:
    m = _MISSING_RE.search(line)
    if m:
        return 'python -m pip install "%s"' % m.group("req").strip()
    m = _WRONG_RE.search(line)
    if m:
        return 'python -m pip install "%s"' % m.group("spec").strip()
    return "python -m pip install --upgrade <the package named above>"


def system_managed() -> bool:
    """A Python that refuses pip installs (PEP 668) and is not a venv."""
    from pyfirstaid.checks.venv import is_externally_managed

    return is_externally_managed() and not in_virtualenv()


def run_check(opts: Options) -> List[Finding]:
    code, out, err = run([sys.executable, "-m", "pip", "check"], timeout=max(opts.timeout, 30))
    if code in (124, 126, 127) or "No module named pip" in err:
        return [Finding(CHECK_ID, Status.SKIP, "Skipped dependency check (pip not available)")]
    if code == 0:
        return [Finding(CHECK_ID, Status.OK, "No dependency conflicts (pip check)")]

    lines = [ln for ln in out.splitlines() if ln.strip()]
    if system_managed():
        # pip install would be refused here (PEP 668), and these packages belong to
        # Homebrew / the OS, so a conflict is informational, not something to fix with pip.
        return [Finding(
            CHECK_ID, Status.INFO,
            "%d dependency conflict(s) inside your system / Homebrew Python (usually harmless)"
            % len(lines),
            detail="\n".join(lines[:8]),
            fix="Don't pip install into this Python. Do your work in a venv "
                "(python -m venv .venv). If it causes real errors, reinstall Python with the "
                "tool that installed it (e.g. brew reinstall python).",
        )]
    findings = [Finding(CHECK_ID, Status.WARN, "Dependency conflict", detail=ln, fix=fix_for(ln))
                for ln in lines[:8]]
    if len(lines) > 8:
        findings.append(Finding(CHECK_ID, Status.INFO,
                                "...and %d more conflicts (run: python -m pip check)"
                                % (len(lines) - 8)))
    return findings or [Finding(CHECK_ID, Status.WARN, "pip check failed", detail=err[-300:])]
