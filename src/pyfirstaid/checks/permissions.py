"""Check: can packages be installed into this environment?"""

from __future__ import annotations

import os
import sys
import sysconfig
from typing import List

from pyfirstaid.model import Finding, Options, Status
from pyfirstaid.util import in_virtualenv

CHECK_ID = "permissions"


def run_check(opts: Options) -> List[Finding]:
    target = sysconfig.get_paths().get("purelib", "")
    if not target or not os.path.isdir(target):
        return [Finding(CHECK_ID, Status.SKIP, "Could not find site-packages")]

    if os.access(target, os.W_OK):
        return [Finding(CHECK_ID, Status.OK, "site-packages is writable")]

    if in_virtualenv():
        owner_fix = ("sudo chown -R $(whoami) %s" % sys.prefix if os.name != "nt"
                     else "Recreate it: python -m venv --clear %s" % sys.prefix)
        return [Finding(
            CHECK_ID, Status.ERROR, "This virtual environment is not writable",
            detail="%s\nIt was probably created with sudo or by another user." % target,
            fix=owner_fix,
        )]
    return [Finding(
        CHECK_ID, Status.INFO, "System site-packages is read-only (this is normal)",
        detail=target,
        fix="Don't use sudo pip. Create a venv: python -m venv .venv, "
            "or install command-line tools with pipx.",
    )]
