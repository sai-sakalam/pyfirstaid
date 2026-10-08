"""Check: is the default text encoding UTF-8?"""

from __future__ import annotations

import locale
import os
import sys
from typing import List

from pyfirstaid.model import Finding, Options, Status

CHECK_ID = "encoding"


def is_utf8(name: str) -> bool:
    return (name or "").lower().replace("-", "").replace("_", "") == "utf8"


def run_check(opts: Options) -> List[Finding]:
    preferred = locale.getpreferredencoding(False)
    if sys.flags.utf8_mode or is_utf8(preferred):
        return [Finding(CHECK_ID, Status.OK, "Default text encoding is UTF-8")]

    if os.name == "nt":
        fix = "setx PYTHONUTF8 1   (then open a new terminal)"
    else:
        fix = "export LANG=en_US.UTF-8   (add it to ~/.zshrc or ~/.bashrc), or export PYTHONUTF8=1"
    return [Finding(
        CHECK_ID, Status.WARN, "Default text encoding is %s, not UTF-8" % preferred,
        detail="open() without encoding= uses %s, so files with accents, emoji or non-English "
               "text can fail with UnicodeDecodeError." % preferred,
        fix=fix,
    )]
