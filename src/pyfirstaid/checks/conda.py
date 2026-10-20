"""Check: problems from mixing conda and pip in a conda environment.

`conda doctor` checks conda's own files but not what pip did to the environment.
This check looks only at files on disk (no conda or pip commands are run):

- a package that conda installed and pip later replaced (two tools fighting over it),
- packages pip-installed into the conda *base* environment,
- a conda environment that is activated but is not the Python actually running.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
from typing import Dict, List, Optional, Set

from pyfirstaid.model import Finding, Options, Status
from pyfirstaid.util import norm, site_package_dirs

CHECK_ID = "conda"

_META_RE = re.compile(r"^(?P<name>.+?)-(?P<ver>[^-]+)\.(?:dist-info|egg-info)$")


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def is_conda_env(prefix: str) -> bool:
    """Every conda environment (base included) has a conda-meta folder."""
    return os.path.isdir(os.path.join(prefix, "conda-meta"))


def is_base_env(prefix: str) -> bool:
    """The base environment holds conda itself: it has condabin/ or an envs/ folder."""
    return (os.path.isdir(os.path.join(prefix, "condabin"))
            or os.path.isdir(os.path.join(prefix, "envs")))


def conda_records(prefix: str) -> Dict[str, Set[str]]:
    """Map normalized conda package name -> metadata folder names conda installed for it.

    Reads conda-meta/*.json. The set is empty for packages that ship no Python metadata.
    """
    records: Dict[str, Set[str]] = {}
    for path in glob.glob(os.path.join(prefix, "conda-meta", "*.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        name = data.get("name")
        if not isinstance(name, str):
            continue
        metas: Set[str] = set()
        for f in data.get("files") or []:
            if not isinstance(f, str):
                continue
            for part in f.replace("\\", "/").split("/"):
                if part.endswith((".dist-info", ".egg-info")):
                    metas.add(part)
                    break
        records.setdefault(normalize(name), set()).update(metas)
    return records


def installer_of(meta_dir: str) -> str:
    try:
        with open(os.path.join(meta_dir, "INSTALLER"), encoding="utf-8") as fh:
            return fh.read().strip().lower()
    except OSError:
        return ""


def find_problems(site_dirs: List[str], records: Dict[str, Set[str]]):
    """Return (replaced, pip_only): package names pip replaced over conda, and pip-only ones."""
    owned_by_conda: Set[str] = set()
    for metas in records.values():
        owned_by_conda.update(metas)

    replaced: List[str] = []
    pip_only: List[str] = []
    for d in site_dirs:
        try:
            entries = os.listdir(d)
        except OSError:
            continue
        for entry in entries:
            m = _META_RE.match(entry)
            if not m or entry in owned_by_conda:
                continue
            if installer_of(os.path.join(d, entry)) != "pip":
                continue  # conservative: only packages pip clearly says it installed
            name = normalize(m.group("name"))
            if name in records:
                replaced.append("%s %s" % (name, m.group("ver")))
            else:
                pip_only.append(name)
    return sorted(set(replaced)), sorted(set(pip_only))


def run_check(opts: Options, prefix: Optional[str] = None,
              site_dirs: Optional[List[str]] = None) -> List[Finding]:
    prefix = prefix or sys.prefix
    findings: List[Finding] = []
    active = os.environ.get("CONDA_PREFIX")

    if not is_conda_env(prefix):
        if active and is_conda_env(active):
            findings.append(Finding(
                CHECK_ID, Status.WARN,
                "A conda environment is activated, but this Python is not from it",
                detail="activated: %s\nrunning:   %s" % (active, sys.executable),
                fix="Use the environment's own Python: python -m pyfirstaid after "
                    "`conda activate <env>`, or check which python with `which python` "
                    "(Windows: `where python`).",
            ))
            return findings
        return [Finding(CHECK_ID, Status.SKIP, "Not a conda environment")]

    records = conda_records(prefix)
    replaced, pip_only = find_problems(
        site_dirs if site_dirs is not None else site_package_dirs(), records)
    base = is_base_env(prefix)
    env_hint = "the base environment" if base else "this conda environment"

    if replaced:
        findings.append(Finding(
            CHECK_ID, Status.WARN,
            "%d package(s) installed by conda were later replaced by pip" % len(replaced),
            detail="conda and pip now both think they own these, which can cause "
                   "import errors and broken updates:\n" + "\n".join(replaced[:8])
                   + ("\n...and %d more" % (len(replaced) - 8) if len(replaced) > 8 else ""),
            fix="Pick one tool per package. Usually: conda install --force-reinstall <name>. "
                "Rule of thumb: install with conda first, and use pip only for packages "
                "conda doesn't have.",
        ))

    if base and pip_only:
        findings.append(Finding(
            CHECK_ID, Status.WARN,
            "%d package(s) pip-installed into the conda base environment" % len(pip_only),
            detail="The base environment runs conda itself; extra pip packages there can "
                   "break conda updates:\n" + ", ".join(pip_only[:10])
                   + (" ..." if len(pip_only) > 10 else ""),
            fix="Create a separate environment for your work: conda create -n myenv python, "
                "then conda activate myenv",
        ))

    if active and norm(active) != norm(prefix):
        findings.append(Finding(
            CHECK_ID, Status.WARN,
            "Your shell activated a DIFFERENT conda environment",
            detail="activated: %s\nrunning:   %s" % (active, prefix),
            fix="Run `conda activate <the env you meant>`, then run pyfirstaid again.",
        ))

    if not findings:
        findings.append(Finding(
            CHECK_ID, Status.OK,
            "No conda / pip conflicts in %s" % env_hint,
        ))
    return findings
