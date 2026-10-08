"""Check: do `python` / `python3` on PATH run the same Python as this one?"""

from __future__ import annotations

import shutil
import sys
from typing import List

from pyfirstaid.model import Finding, Options, Status
from pyfirstaid.util import norm, run

CHECK_ID = "path"


def is_store_stub(path: str) -> bool:
    """The Windows 'python' that only opens the Microsoft Store."""
    return "windowsapps" in path.replace("/", "\\").lower()


def run_check(opts: Options) -> List[Finding]:
    findings: List[Finding] = []
    checked = 0
    for cmd in ("python", "python3"):
        exe = shutil.which(cmd)
        if not exe:
            continue
        checked += 1
        if is_store_stub(exe):
            findings.append(Finding(
                CHECK_ID, Status.WARN,
                "`%s` on PATH is the Microsoft Store shortcut, not a real Python" % cmd,
                detail=exe,
                fix="Install Python from python.org, or turn off the shortcut: Settings → Apps → "
                    "Advanced app settings → App execution aliases → python.exe / python3.exe.",
            ))
            continue
        code, out, _ = run([exe, "-c", "import sys; print(sys.prefix)"], opts.timeout)
        if code != 0 or not out:
            findings.append(Finding(
                CHECK_ID, Status.WARN, "`%s` on PATH does not start" % cmd, detail=exe,
                fix="Reinstall Python, or remove the broken entry from PATH.",
            ))
        elif norm(out.splitlines()[-1]) != norm(sys.prefix):
            findings.append(Finding(
                CHECK_ID, Status.WARN,
                "Typing `%s` runs a DIFFERENT Python than this one" % cmd,
                detail="%s -> %s\nthis Python -> %s" % (cmd, out.splitlines()[-1], sys.prefix),
                fix="Activate the virtual environment you want, or call Python by its full path. "
                    "To change the default, put the right Python's folder first in PATH.",
            ))

    if not findings:
        if checked:
            findings.append(Finding(CHECK_ID, Status.OK,
                                    "`python`/`python3` on PATH run this Python"))
        else:
            findings.append(Finding(CHECK_ID, Status.INFO, "No `python` or `python3` on PATH",
                                    fix="Add Python's folder to PATH, or use the `py` launcher "
                                        "on Windows."))
    return findings
