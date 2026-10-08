"""Check: compiled extension files built for a different Python version."""

from __future__ import annotations

import importlib.machinery
import os
import re
from typing import Dict, List, Optional, Sequence, Set

from pyfirstaid.model import Finding, Options, Status

CHECK_ID = "compiled"

# Matches version-tagged extension files, e.g. _core.cpython-312-x86_64-linux-gnu.so,
# _core.cp312-win_amd64.pyd, _core.abi3.so. Untagged "_core.so" is always accepted.
_TAG_RE = re.compile(r"\.((?:cpython-|cp|pypy|graalpy)[0-9][^.]*|abi3)\.(so|pyd)$")


def mismatched_tag(filename: str, valid_suffixes: Sequence[str]) -> Optional[str]:
    """Return the ABI tag if `filename` is tagged for a different interpreter, else None."""
    base = os.path.basename(filename.replace("\\", "/"))
    m = _TAG_RE.search(base)
    if not m:
        return None
    suffix = ".%s.%s" % (m.group(1), m.group(2))
    return None if suffix in valid_suffixes else m.group(1)


def running_tag() -> str:
    for s in importlib.machinery.EXTENSION_SUFFIXES:
        m = _TAG_RE.search("x" + s)
        if m and m.group(1) != "abi3":
            return m.group(1)
    return "this Python"


def run_check(opts: Options) -> List[Finding]:
    import importlib.metadata as md

    valid = importlib.machinery.EXTENSION_SUFFIXES
    bad: Dict[str, Set[str]] = {}
    compiled_count = 0
    seen: Set[str] = set()

    for dist in md.distributions():
        name = (dist.metadata["Name"] or "").strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        has_ext = False
        for f in dist.files or []:
            s = str(f)
            if not s.endswith((".so", ".pyd")) or ".libs/" in s.replace("\\", "/"):
                continue
            has_ext = True
            tag = mismatched_tag(s, valid)
            if tag:
                bad.setdefault(name, set()).add(tag)
        compiled_count += has_ext

    if not bad:
        return [Finding(CHECK_ID, Status.OK,
                        "%d compiled package(s) match this Python" % compiled_count)]

    findings = []
    for name, tags in sorted(bad.items())[:10]:
        findings.append(Finding(
            CHECK_ID, Status.ERROR,
            "%s was built for a different Python" % name,
            detail="files are tagged %s, but this is %s" % (", ".join(sorted(tags)), running_tag()),
            fix="python -m pip install --force-reinstall --no-cache-dir %s" % name,
        ))
    if len(bad) > 10:
        findings.append(Finding(CHECK_ID, Status.INFO,
                                "...and %d more packages with the same problem" % (len(bad) - 10)))
    return findings
