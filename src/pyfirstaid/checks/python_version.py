"""Check: is this Python still supported, and is it Apple's built-in one?"""

from __future__ import annotations

import datetime as dt
import sys
from typing import List, Optional, Tuple

from pyfirstaid.model import Finding, Options, Status

CHECK_ID = "python-version"

# End-of-life dates (approximate month), from https://devguide.python.org/versions/
EOL = {
    (3, 6): dt.date(2021, 12, 23),
    (3, 7): dt.date(2023, 6, 27),
    (3, 8): dt.date(2024, 10, 7),
    (3, 9): dt.date(2025, 10, 31),
    (3, 10): dt.date(2026, 10, 31),
    (3, 11): dt.date(2027, 10, 31),
    (3, 12): dt.date(2028, 10, 31),
    (3, 13): dt.date(2029, 10, 31),
    (3, 14): dt.date(2030, 10, 31),
}
APPLE_MARKERS = ("/Library/Developer/CommandLineTools/", "/Applications/Xcode")


def eol_status(version: Tuple[int, int], today: dt.date) -> Tuple[str, Optional[dt.date]]:
    """Return ('eol' | 'soon' | 'ok' | 'unknown', eol_date)."""
    eol = EOL.get(version)
    if eol is None:
        return ("unknown" if version > max(EOL) else "eol"), None
    if today > eol:
        return "eol", eol
    if (eol - today).days <= 183:
        return "soon", eol
    return "ok", eol


def is_apple_python(executable: str, prefix: str) -> bool:
    return any(m in executable or m in prefix for m in APPLE_MARKERS)


def upgrade_fix() -> str:
    if sys.platform == "darwin":
        return "Install a current Python: `brew install python` or download it from python.org."
    if sys.platform == "win32":
        return "Install a current Python from python.org (or: winget install Python.Python.3.13)."
    return "Install a newer Python with your package manager, pyenv, or `uv python install`."


def run_check(opts: Options, today: Optional[dt.date] = None) -> List[Finding]:
    today = today or dt.date.today()
    ver = sys.version_info[:2]
    label = "Python %d.%d.%d" % sys.version_info[:3]
    findings: List[Finding] = []

    status, eol = eol_status(ver, today)
    if status == "eol":
        findings.append(Finding(
            CHECK_ID, Status.WARN, "%s no longer gets security updates" % label,
            detail="End of life: %s" % eol.strftime("%B %Y") if eol else "",
            fix=upgrade_fix(),
        ))
    elif status == "soon":
        findings.append(Finding(
            CHECK_ID, Status.INFO,
            "%s reaches end of life in %s" % (label, eol.strftime("%B %Y")),
            fix="Plan an upgrade. " + upgrade_fix(),
        ))
    elif status == "ok":
        findings.append(Finding(
            CHECK_ID, Status.OK, "%s (supported until %s)" % (label, eol.strftime("%B %Y"))))
    else:
        findings.append(Finding(CHECK_ID, Status.OK, label))

    if sys.version_info.releaselevel != "final":
        findings.append(Finding(
            CHECK_ID, Status.INFO, "This is a pre-release Python (%s)"
            % sys.version_info.releaselevel,
            detail="Some packages may not have wheels for it yet.",
        ))

    if sys.platform == "darwin" and is_apple_python(sys.executable, sys.prefix):
        findings.append(Finding(
            CHECK_ID, Status.WARN, "You are using Apple's built-in Python (Command Line Tools)",
            detail="It is meant for Apple's own tools: it is old and updated only with Xcode.",
            fix="`brew install python` (or python.org), then make sure `which python3` "
                "shows the new one first.",
        ))
    return findings
