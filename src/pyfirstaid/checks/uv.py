"""Check: uv projects that run the wrong environment (or a broken one).

uv keeps each project's packages in its own environment (usually `.venv`). Problems come
from running a different Python than that one, or from a `.venv` whose base Python was
removed. This check only reads files: it runs no uv commands.
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional

from pyfirstaid.model import Finding, Options, Status
from pyfirstaid.util import (
    broken_venv_base,
    find_upwards,
    in_virtualenv,
    norm,
    read_pyvenv_cfg,
)

CHECK_ID = "uv"


def made_by_uv(prefix: str) -> bool:
    """uv writes a `uv = <version>` line into pyvenv.cfg."""
    return "uv" in read_pyvenv_cfg(prefix)


def project_env(root: str) -> str:
    """The folder uv uses for a project's environment (UV_PROJECT_ENVIRONMENT or .venv)."""
    custom = os.environ.get("UV_PROJECT_ENVIRONMENT")
    if custom:
        return custom if os.path.isabs(custom) else os.path.join(root, custom)
    return os.path.join(root, ".venv")


def display_path(path: str, cwd: str) -> str:
    """Short path for messages: relative to the current folder when that is simpler."""
    try:
        rel = os.path.relpath(path, cwd)
    except ValueError:  # different drives on Windows
        return path
    return rel if not rel.startswith(os.pardir + os.sep + os.pardir) else path


def run_check(opts: Options, prefix: Optional[str] = None,
              in_venv: Optional[bool] = None) -> List[Finding]:
    prefix = prefix or sys.prefix
    in_venv = in_virtualenv() if in_venv is None else in_venv
    lock = find_upwards(opts.cwd or os.getcwd(), "uv.lock")

    if not lock:
        if made_by_uv(prefix):
            return [Finding(CHECK_ID, Status.OK, "Running an environment made by uv",
                            fix="This environment has no pip by design: install packages "
                                "with `uv pip install <package>`.")]
        return [Finding(CHECK_ID, Status.SKIP, "Not a uv project")]

    root = os.path.dirname(lock)
    env = project_env(root)
    shown = display_path(env, opts.cwd or os.getcwd())

    if not os.path.isfile(os.path.join(env, "pyvenv.cfg")):
        return [Finding(
            CHECK_ID, Status.INFO,
            "uv project, but its environment hasn't been created yet",
            detail="uv.lock: %s" % lock,
            fix="uv sync",
        )]

    gone = broken_venv_base(env)
    if gone:
        return [Finding(
            CHECK_ID, Status.WARN,
            "The uv project's environment is broken: the Python it was made from is gone",
            detail="%s was built from %s, which no longer exists (often after upgrading or "
                   "removing that Python)." % (shown, gone),
            fix="Rebuild it: delete the %s folder, then run `uv sync`." % shown,
        )]

    if norm(prefix) == norm(env):
        return [Finding(CHECK_ID, Status.OK, "Running the uv project's environment (%s)" % shown)]

    if in_venv:
        return [Finding(
            CHECK_ID, Status.WARN,
            "This is a uv project, but a DIFFERENT environment is running",
            detail="project: %s\nrunning: %s" % (env, prefix),
            fix="Run commands through uv so they use the project's environment: "
                "`uv run python ...`, `uv run pytest`. Or `deactivate` first.",
        )]
    return [Finding(
        CHECK_ID, Status.INFO,
        "This is a uv project, but its environment is not the Python running",
        detail="project: %s\nrunning: %s" % (env, prefix),
        fix="Run commands through uv: `uv run python ...`, `uv run pytest`. "
            "To check the project's Python: uv run python -m pyfirstaid",
    )]
