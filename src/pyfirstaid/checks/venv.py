"""Check: is a virtual environment active, and is it the right one?"""

from __future__ import annotations

import os
import sys
import sysconfig
from typing import List, Optional

from pyfirstaid.model import Finding, Options, Status
from pyfirstaid.util import in_virtualenv, norm

CHECK_ID = "venv"

CANDIDATE_DIRS = (".venv", "venv", "env", ".env")


def find_unused_venv(cwd: str) -> Optional[str]:
    """Return the path of a virtual environment folder in `cwd`, if any."""
    for name in CANDIDATE_DIRS:
        path = os.path.join(cwd, name)
        if os.path.isfile(os.path.join(path, "pyvenv.cfg")):
            return path
    return None


def activate_command(venv_path: str) -> str:
    if os.name == "nt":
        return r"%s\Scripts\activate" % venv_path
    return "source %s/bin/activate" % venv_path


def is_externally_managed() -> bool:
    stdlib = sysconfig.get_paths().get("stdlib", "")
    return bool(stdlib) and os.path.isfile(os.path.join(stdlib, "EXTERNALLY-MANAGED"))


def run_check(opts: Options) -> List[Finding]:
    findings: List[Finding] = []
    cwd = opts.cwd or os.getcwd()
    activated = os.environ.get("VIRTUAL_ENV")
    conda = os.environ.get("CONDA_PREFIX")

    if in_virtualenv():
        findings.append(Finding(CHECK_ID, Status.OK,
                                "Virtual environment active: %s" % sys.prefix))
    elif conda and norm(conda) == norm(sys.prefix):
        findings.append(Finding(
            CHECK_ID, Status.INFO, "Running in a conda environment: %s" % sys.prefix,
            fix="For conda-specific checks, also run `conda doctor`.",
        ))
    else:
        unused = find_unused_venv(cwd)
        if unused:
            findings.append(Finding(
                CHECK_ID, Status.WARN,
                "Found a virtual environment that is NOT being used",
                detail="%s exists, but this Python is %s" % (unused, sys.executable),
                fix=activate_command(os.path.relpath(unused, cwd)),
            ))
        elif is_externally_managed():
            findings.append(Finding(
                CHECK_ID, Status.WARN,
                "No virtual environment, and this system Python blocks pip installs",
                detail="Your OS marks this Python as externally managed (PEP 668), "
                       "so `pip install` will fail with 'externally-managed-environment'.",
                fix="python -m venv .venv  &&  " + activate_command(".venv"),
            ))
        else:
            findings.append(Finding(
                CHECK_ID, Status.INFO, "No virtual environment active",
                fix="Recommended: python -m venv .venv  &&  " + activate_command(".venv"),
            ))

    if activated and norm(activated) != norm(sys.prefix):
        findings.append(Finding(
            CHECK_ID, Status.WARN,
            "Your shell activated a DIFFERENT virtual environment",
            detail="activated: %s\nrunning:   %s" % (activated, sys.prefix),
            fix="Run `deactivate`, then activate the environment you meant to use.",
        ))
    return findings
