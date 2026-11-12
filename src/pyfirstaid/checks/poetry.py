"""Check: Poetry projects that run the wrong environment (or a broken one).

Poetry keeps each project's environment either in the project (`.venv`) or in its own
cache folder, named `<project>-<hash>-py3.X`. This check finds those folders on disk and
compares them with the Python that is running. It runs no Poetry commands.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
import sys
from typing import List, Optional

from pyfirstaid.checks.uv import display_path
from pyfirstaid.model import Finding, Options, Status
from pyfirstaid.util import (
    broken_venv_base,
    find_upwards,
    in_virtualenv,
    is_within,
    norm,
    read_pyproject,
)

CHECK_ID = "poetry"


def poetry_project(cwd: str) -> Optional[str]:
    """The Poetry project folder for `cwd` (has poetry.lock or [tool.poetry]), if any."""
    lock = find_upwards(cwd, "poetry.lock")
    if lock:
        return os.path.dirname(lock)
    if "poetry" in (read_pyproject(cwd).get("tool") or {}):
        return cwd
    return None


def project_name(root: str) -> Optional[str]:
    data = read_pyproject(root)
    for table in ((data.get("tool") or {}).get("poetry") or {}, data.get("project") or {}):
        name = table.get("name") if isinstance(table, dict) else None
        if isinstance(name, str) and name:
            return name
    return None


def venvs_dir() -> str:
    """Where Poetry keeps environments that are not inside the project."""
    custom = os.environ.get("POETRY_VIRTUALENVS_PATH")
    if custom:
        return custom
    cache = os.environ.get("POETRY_CACHE_DIR")
    if not cache:
        home = os.path.expanduser("~")
        if sys.platform == "darwin":
            cache = os.path.join(home, "Library", "Caches", "pypoetry")
        elif os.name == "nt":
            local = os.environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
            cache = os.path.join(local, "pypoetry", "Cache")
        else:
            xdg = os.environ.get("XDG_CACHE_HOME") or os.path.join(home, ".cache")
            cache = os.path.join(xdg, "pypoetry")
    return os.path.join(cache, "virtualenvs")


def sanitized(name: str) -> str:
    return re.sub(r'[ $`!*@"\\\r\n\t]', "_", name.lower())[:42]


def env_name(name: str, root: str) -> str:
    """Poetry's environment name: <name>-<first 8 chars of a hash of the project path>."""
    digest = hashlib.sha256(os.path.normcase(os.path.realpath(root)).encode()).digest()
    return "%s-%s" % (sanitized(name), base64.urlsafe_b64encode(digest).decode()[:8])


def project_envs(root: str, name: Optional[str], cache_dir: str) -> List[str]:
    """This project's environments: an in-project .venv, plus matching cache folders."""
    envs: List[str] = []
    local = os.path.join(root, ".venv")
    if os.path.isfile(os.path.join(local, "pyvenv.cfg")):
        envs.append(local)
    if name:
        start = env_name(name, root) + "-py"
        try:
            entries = sorted(os.listdir(cache_dir))
        except OSError:
            entries = []
        envs.extend(os.path.join(cache_dir, e) for e in entries if e.startswith(start))
    return envs


def run_check(opts: Options, prefix: Optional[str] = None, in_venv: Optional[bool] = None,
              cache_dir: Optional[str] = None) -> List[Finding]:
    prefix = prefix or sys.prefix
    in_venv = in_virtualenv() if in_venv is None else in_venv
    cache_dir = cache_dir or venvs_dir()
    cwd = opts.cwd or os.getcwd()

    root = poetry_project(cwd)
    if not root:
        return [Finding(CHECK_ID, Status.SKIP, "Not a Poetry project")]

    name = project_name(root)
    envs = project_envs(root, name, cache_dir)
    findings: List[Finding] = []

    working = []
    for env in envs:
        gone = broken_venv_base(env)
        if not gone:
            working.append(env)
            continue
        if norm(os.path.dirname(env)) == norm(root):
            fix = "Delete the .venv folder, then run `poetry install`."
        else:
            version = env.rsplit("-py", 1)[-1]
            fix = "poetry env remove python%s   then: poetry install" % version
        findings.append(Finding(
            CHECK_ID, Status.WARN,
            "A Poetry environment for this project is broken: its base Python is gone",
            detail="%s was built from %s, which no longer exists (often after upgrading "
                   "Python)." % (display_path(env, cwd), gone),
            fix=fix,
        ))

    # The running env counts as the project's even if the path hash changed (moved project).
    running_is_project = any(norm(prefix) == norm(e) for e in working) or (
        name is not None and is_within(prefix, cache_dir)
        and os.path.basename(os.path.normpath(prefix)).startswith(sanitized(name) + "-"))

    if running_is_project:
        findings.append(Finding(CHECK_ID, Status.OK, "Running the Poetry project's environment"))
    elif not envs:
        findings.append(Finding(
            CHECK_ID, Status.INFO,
            "Poetry project, but no environment for it was found",
            detail="project: %s" % root,
            fix="poetry install",
        ))
    elif working:
        findings.append(Finding(
            CHECK_ID, Status.WARN if in_venv else Status.INFO,
            "This is a Poetry project, but a DIFFERENT environment is running" if in_venv
            else "This is a Poetry project, but its environment is not the Python running",
            detail="project env: %s\nrunning:     %s" % (working[0], prefix),
            fix="Run commands through Poetry: `poetry run python ...`, "
                "or run `poetry env activate` and then the command it prints. "
                "To check it: poetry run python -m pyfirstaid",
        ))
    return findings
