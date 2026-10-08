"""Check: duplicate, half-removed or corrupted package installs."""

from __future__ import annotations

import os
import re
from typing import Dict, List

from pyfirstaid.model import Finding, Options, Status
from pyfirstaid.util import site_package_dirs

CHECK_ID = "broken-installs"

_META_RE = re.compile(r"^(?P<name>.+?)-(?P<ver>[^-]+)\.(?:dist-info|egg-info)$")


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def scan_dir(directory: str) -> List[Finding]:
    findings: List[Finding] = []
    try:
        entries = os.listdir(directory)
    except OSError:
        return findings

    versions: Dict[str, List[str]] = {}
    for entry in entries:
        path = os.path.join(directory, entry)
        if entry.startswith("~"):
            findings.append(Finding(
                CHECK_ID, Status.WARN, "Leftover from an interrupted install: %s" % entry,
                detail="pip renames packages to '~...' while removing them; this one was "
                       "never cleaned up and can break imports.",
                fix="Delete the folder: %s" % path,
            ))
            continue
        m = _META_RE.match(entry)
        if not m:
            continue
        versions.setdefault(normalize(m.group("name")), []).append(entry)
        if entry.endswith(".dist-info") and not os.path.isfile(os.path.join(path, "METADATA")):
            findings.append(Finding(
                CHECK_ID, Status.ERROR, "Corrupted install: %s has no METADATA" % entry,
                fix="python -m pip install --force-reinstall %s" % m.group("name"),
            ))

    for name, metas in sorted(versions.items()):
        if len(metas) > 1:
            findings.append(Finding(
                CHECK_ID, Status.WARN, "%s is installed more than once" % name,
                detail="in %s:\n%s" % (directory, "\n".join(sorted(metas))),
                fix="python -m pip uninstall -y %s, repeat until it is gone, "
                    "then python -m pip install %s" % (name, name),
            ))
    return findings


def run_check(opts: Options) -> List[Finding]:
    findings: List[Finding] = []
    dirs = site_package_dirs()
    for d in dirs:
        findings.extend(scan_dir(d))
    if not findings:
        findings.append(Finding(
            CHECK_ID, Status.OK,
            "No broken or duplicate installs (%d folder(s) scanned)" % len(dirs)))
    return findings
