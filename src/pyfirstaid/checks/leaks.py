"""Check: environment variables and settings that leak outside packages in."""

from __future__ import annotations

import os
import sys
from typing import List

from pyfirstaid.model import Finding, Options, Status
from pyfirstaid.util import in_virtualenv

CHECK_ID = "leaks"


def unset_hint(var: str) -> str:
    if os.name == "nt":
        return "set %s=   (or remove it in System Properties → Environment Variables)" % var
    return "unset %s   (and remove it from ~/.zshrc / ~/.bashrc if it is set there)" % var


def system_site_enabled(prefix: str) -> bool:
    cfg = os.path.join(prefix, "pyvenv.cfg")
    try:
        with open(cfg, encoding="utf-8") as fh:
            for line in fh:
                key, _, value = line.partition("=")
                if key.strip() == "include-system-site-packages":
                    return value.strip().lower() == "true"
    except OSError:
        pass
    return False


def run_check(opts: Options) -> List[Finding]:
    findings: List[Finding] = []

    if os.environ.get("PYTHONHOME"):
        findings.append(Finding(
            CHECK_ID, Status.WARN, "PYTHONHOME is set",
            detail="PYTHONHOME=%s\nThis overrides where Python finds its standard library and "
                   "commonly breaks virtual environments." % os.environ["PYTHONHOME"],
            fix=unset_hint("PYTHONHOME"),
        ))

    if os.environ.get("PYTHONPATH"):
        entries = [e for e in os.environ["PYTHONPATH"].split(os.pathsep) if e]
        findings.append(Finding(
            CHECK_ID, Status.WARN, "PYTHONPATH is set: packages may leak in from outside",
            detail="\n".join(entries[:6]),
            fix=unset_hint("PYTHONPATH") + ". Install packages into a venv instead.",
        ))

    if in_virtualenv() and system_site_enabled(sys.prefix):
        findings.append(Finding(
            CHECK_ID, Status.INFO,
            "This venv can also see the system's packages (include-system-site-packages)",
            fix="Fine if intended. Otherwise recreate it: python -m venv --clear <venv-folder>",
        ))

    if not findings:
        findings.append(Finding(CHECK_ID, Status.OK, "No PYTHONPATH / PYTHONHOME leaks"))
    return findings
