"""Run the checks inside *another* Python interpreter.

pyfirstaid must examine the Python the user actually works with. When it is
installed with pipx or `uv tool`, it runs from its own private virtual
environment, so it re-runs itself inside the target interpreter instead.
pyfirstaid has no dependencies, so the target does not need it installed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import List, Optional, Tuple

DELEGATED_ENV = "PYFIRSTAID_DELEGATED"

_TOOL_VENV_MARKERS = ("/pipx/venvs/", "/uv/tools/", "/pipx/.cache/")

# Runs inside the target interpreter. Drop the current folder from sys.path so a
# user's random.py or json.py can't break pyfirstaid, then import it from argv[1].
_BOOTSTRAP = (
    "import sys; sys.path[:] = [p for p in sys.path if p not in ('', '.')]; "
    "sys.path.insert(0, sys.argv.pop(1)); "
    "from pyfirstaid.cli import main; sys.exit(main(sys.argv[1:]))"
)


def in_tool_venv(prefix: str) -> bool:
    """True if `prefix` is a private tool environment made by pipx or `uv tool`."""
    p = prefix.replace("\\", "/").lower() + "/"
    return any(m in p for m in _TOOL_VENV_MARKERS)


def default_target() -> Optional[str]:
    """The interpreter the user gets when typing `python3` (or `python`)."""
    return shutil.which("python3") or shutil.which("python")


def resolve(python: str) -> Optional[str]:
    """Accept a path or a command name such as `python3.12`."""
    if os.path.sep in python or (os.altsep and os.altsep in python):
        return python if os.path.exists(python) else None
    return shutil.which(python)


def package_root() -> str:
    """Folder (or .pyz file) that contains the `pyfirstaid` package."""
    import pyfirstaid

    return os.path.dirname(os.path.dirname(os.path.abspath(pyfirstaid.__file__)))


def probe(target: str) -> Optional[Tuple[bool, str]]:
    """Ask `target` for (is Python 3.9+, sys.prefix). None if it does not start."""
    try:
        out = subprocess.run(
            [target, "-c", "import sys; print(sys.version_info >= (3, 9)); print(sys.prefix)"],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    lines = out.stdout.strip().splitlines()
    if out.returncode != 0 or len(lines) < 2:
        return None
    return lines[0] == "True", lines[1]


def same_environment(target_prefix: str) -> bool:
    """Venv interpreters are often links to the same binary, so compare sys.prefix."""
    def key(p: str) -> str:
        return os.path.normcase(os.path.realpath(p))

    return key(target_prefix) == key(sys.prefix)


def build_command(target: str, forwarded_args: List[str]) -> List[str]:
    return [target, "-c", _BOOTSTRAP, package_root()] + list(forwarded_args)


def run_in(target: str, forwarded_args: List[str]) -> int:
    env = dict(os.environ)
    env[DELEGATED_ENV] = "1"
    return subprocess.call(build_command(target, forwarded_args), env=env)
