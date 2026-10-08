"""Check: files in the current folder that hide real modules (e.g. random.py)."""

from __future__ import annotations

import os
import sys
from typing import List, Optional, Set

from pyfirstaid.model import Finding, Options, Status

CHECK_ID = "shadowing"

# Fallback for Python 3.9, which lacks sys.stdlib_module_names.
_COMMON_STDLIB = {
    "abc", "array", "ast", "asyncio", "base64", "bisect", "calendar", "cmd", "code", "collections",
    "copy", "csv", "datetime", "decimal", "dis", "email", "enum", "fractions", "functools", "glob",
    "hashlib", "heapq", "html", "http", "inspect", "io", "itertools", "json", "logging", "math",
    "numbers", "operator", "os", "pathlib", "pdb", "platform", "profile", "queue", "random", "re",
    "secrets", "select", "selectors", "shutil", "signal", "site", "socket", "sqlite3", "ssl",
    "statistics", "string", "struct", "subprocess", "sys", "tempfile", "threading", "time", "token",
    "tokenize", "trace", "turtle", "types", "typing", "unittest", "urllib", "uuid", "xml",
    "zipfile",
}
# Names that are normal in projects even though they match a module.
_IGNORE = {"test", "tests", "conftest", "setup", "__main__", "__init__", "main", "app", "docs"}


def stdlib_names() -> Set[str]:
    names = getattr(sys, "stdlib_module_names", None)
    return set(names) if names else set(_COMMON_STDLIB)


def installed_top_level() -> Set[str]:
    try:
        import importlib.metadata as md

        return set(md.packages_distributions())  # Python 3.10+
    except Exception:  # noqa: BLE001 - optional on 3.9
        return set()


def shadowed_by(entry: str, folder: str, stdlib: Set[str], installed: Set[str]) -> Optional[str]:
    """Return 'stdlib' / 'installed' if `entry` in `folder` hides a module, else None."""
    path = os.path.join(folder, entry)
    if entry.endswith(".py") and os.path.isfile(path):
        name, is_file = entry[:-3], True
    elif os.path.isfile(os.path.join(path, "__init__.py")):
        name, is_file = entry, False
    else:
        return None
    if name in _IGNORE or name.startswith("_"):
        return None
    if name in stdlib:
        return "stdlib"
    if is_file and name in installed:  # a package folder may be the project itself
        return "installed"
    return None


def run_check(opts: Options) -> List[Finding]:
    folder = opts.cwd or os.getcwd()
    try:
        entries = sorted(os.listdir(folder))
    except OSError:
        return [Finding(CHECK_ID, Status.SKIP, "Could not read the current folder")]

    stdlib, installed = stdlib_names(), installed_top_level()
    findings: List[Finding] = []
    for entry in entries:
        kind = shadowed_by(entry, folder, stdlib, installed)
        if not kind:
            continue
        module = entry[:-3] if entry.endswith(".py") else entry
        what = "the standard library module" if kind == "stdlib" else "the installed package"
        findings.append(Finding(
            CHECK_ID, Status.WARN,
            "`%s` in this folder hides %s `%s`" % (entry, what, module),
            detail="`import %s` will load your file instead, which causes confusing errors like "
                   "\"module '%s' has no attribute ...\"." % (module, module),
            fix="Rename it (e.g. my_%s.py) and delete any __pycache__ folder next to it."
                % module,
        ))
    if not findings:
        findings.append(Finding(CHECK_ID, Status.OK,
                                "No files in this folder hide real modules"))
    return findings
