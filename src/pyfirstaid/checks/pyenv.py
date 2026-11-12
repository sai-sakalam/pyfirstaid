"""Check: pyenv and `.python-version` files that ask for a different Python.

pyenv (and uv) read a `.python-version` file to pick the Python for a folder. When the
Python running is not the one that file asks for, packages "disappear" and versions look
wrong. This check reads files and PATH only: it runs no pyenv commands.
"""

from __future__ import annotations

import os
import re
import sys
from typing import List, Optional, Tuple

from pyfirstaid.model import Finding, Options, Status
from pyfirstaid.util import find_upwards, norm

CHECK_ID = "pyenv"

_VERSION_RE = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?$")


def pyenv_root() -> Optional[str]:
    """pyenv's folder (PYENV_ROOT or ~/.pyenv), if pyenv is installed."""
    root = os.environ.get("PYENV_ROOT") or os.path.join(os.path.expanduser("~"), ".pyenv")
    if os.name == "nt" and os.path.isdir(os.path.join(root, "pyenv-win")):
        root = os.path.join(root, "pyenv-win")  # pyenv-win keeps everything one level down
    return root if os.path.isdir(os.path.join(root, "versions")) else None


def requested_version(cwd: str) -> Tuple[Optional[str], str]:
    """(version asked for, where it came from): PYENV_VERSION, else the nearest .python-version."""
    env = os.environ.get("PYENV_VERSION")
    if env:
        return env.split(":")[0].strip(), "PYENV_VERSION"
    path = find_upwards(cwd, ".python-version")
    if not path or not os.path.isfile(path):
        return None, ""
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                word = line.split("#", 1)[0].strip()
                if word:
                    return word.split()[0], path
    except OSError:
        pass
    return None, path


def matches(wanted: str, running: Tuple[int, ...]) -> Optional[bool]:
    """Does Python `running` satisfy `wanted` ("3", "3.12" or "3.12.4")?

    None when `wanted` is not a plain version (e.g. "system", "pypy3.10", a virtualenv name).
    """
    m = _VERSION_RE.match(wanted)
    if not m:
        return None
    parts = tuple(int(p) for p in m.groups() if p is not None)
    return tuple(running[:len(parts)]) == parts


def installed(root: str, wanted: str) -> bool:
    """pyenv has `wanted` installed (exact folder, or a newer patch of "3.12")."""
    try:
        names = os.listdir(os.path.join(root, "versions"))
    except OSError:
        return False
    return any(n == wanted or n.startswith(wanted + ".") for n in names)


def shims_on_path(root: str) -> bool:
    shims = norm(os.path.join(root, "shims"))
    return any(norm(p) == shims for p in os.environ.get("PATH", "").split(os.pathsep) if p)


def run_check(opts: Options, root: Optional[str] = None,
              running: Optional[Tuple[int, ...]] = None) -> List[Finding]:
    cwd = opts.cwd or os.getcwd()
    root = root if root is not None else pyenv_root()
    running = running or tuple(sys.version_info[:3])
    running_str = ".".join(str(p) for p in running)
    wanted, source = requested_version(cwd)

    if not root and not wanted:
        return [Finding(CHECK_ID, Status.SKIP, "No pyenv and no .python-version file")]
    if not wanted:
        return [Finding(CHECK_ID, Status.OK, "pyenv found; no .python-version file here")]

    where = "PYENV_VERSION" if source == "PYENV_VERSION" else "`.python-version`"
    ok = matches(wanted, running)
    if ok is None:
        return [Finding(CHECK_ID, Status.INFO,
                        "%s asks for %r (not a plain version, so not compared)" % (where, wanted),
                        detail=source)]
    if ok:
        return [Finding(CHECK_ID, Status.OK,
                        "Python %s matches %s (%s)" % (running_str, where, wanted))]

    if root and not installed(root, wanted):
        return [Finding(
            CHECK_ID, Status.WARN,
            "%s asks for Python %s, but pyenv doesn't have it installed" % (where, wanted),
            detail="%s\nrunning: Python %s" % (source, running_str),
            fix="pyenv install %s   (or change the version: pyenv local <version>)" % wanted,
        )]

    if root and os.name != "nt" and not shims_on_path(root):
        fix = ('pyenv is installed but not set up in your shell. Add to your shell profile '
               '(e.g. ~/.zshrc), then open a new terminal:\n'
               'export PYENV_ROOT="$HOME/.pyenv"\n'
               '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"\n'
               'eval "$(pyenv init -)"')
    elif root:
        fix = ("Something earlier on PATH wins over pyenv (an activated venv, or an alias). "
               "Check with `pyenv which python` and `which python`. Or change the version: "
               "pyenv local %s.%s" % running[:2])
    else:
        fix = ("Use a Python %s (uv reads this file too: `uv run python ...`), "
               "or update the file to the version you use." % wanted)
    return [Finding(
        CHECK_ID, Status.WARN,
        "%s asks for Python %s, but this is Python %s" % (where, wanted, running_str),
        detail=source,
        fix=fix,
    )]
