"""Check: Jupyter kernels that point at the wrong (or a missing) Python.

The classic notebook problem is "I installed the package, but the notebook can't import
it": the notebook runs a *kernel*, and each kernel is tied to one Python. This check
reads the kernel files (kernel.json) on disk. It runs no Jupyter commands.

- kernels whose Python no longer exists (deleted or moved venv, upgraded Python),
- this environment has ipykernel but is not registered as a kernel,
- several kernels with the same name in the kernel picker.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

from pyfirstaid.model import Finding, Options, Status
from pyfirstaid.util import in_virtualenv, is_within, norm

CHECK_ID = "jupyter"

Kernel = Tuple[str, str, List[str], str]  # (name, folder, argv, display name)


def jupyter_dirs(prefix: Optional[str] = None) -> List[str]:
    """Folders Jupyter searches for kernels, in Jupyter's own order (user, env, system)."""
    prefix = prefix or sys.prefix
    home = os.path.expanduser("~")
    dirs: List[str] = []

    data_dir = os.environ.get("JUPYTER_DATA_DIR")
    if data_dir:
        dirs.append(data_dir)
    elif sys.platform == "darwin":
        dirs.append(os.path.join(home, "Library", "Jupyter"))
    elif os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            dirs.append(os.path.join(appdata, "jupyter"))
    else:
        xdg = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
        dirs.append(os.path.join(xdg, "jupyter"))

    for extra in (os.environ.get("JUPYTER_PATH") or "").split(os.pathsep):
        if extra:
            dirs.append(extra)

    dirs.append(os.path.join(prefix, "share", "jupyter"))
    if os.name == "nt":
        programdata = os.environ.get("PROGRAMDATA")
        if programdata:
            dirs.append(os.path.join(programdata, "jupyter"))
    else:
        dirs.extend(["/usr/local/share/jupyter", "/usr/share/jupyter"])
    return [os.path.join(d, "kernels") for d in dirs]


def find_kernels(kernel_dirs: List[str]) -> List[Kernel]:
    """All kernels, first one wins when the same name is in several folders (like Jupyter)."""
    seen: Dict[str, Kernel] = {}
    for base in kernel_dirs:
        try:
            names = sorted(os.listdir(base))
        except OSError:
            continue
        for name in names:
            folder = os.path.join(base, name)
            spec_file = os.path.join(folder, "kernel.json")
            if name.lower() in seen or not os.path.isfile(spec_file):
                continue
            try:
                with open(spec_file, encoding="utf-8") as fh:
                    spec = json.load(fh)
            except (OSError, ValueError):
                continue
            argv = spec.get("argv") if isinstance(spec, dict) else None
            if not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
                continue
            display = spec.get("display_name")
            if not isinstance(display, str):
                display = name
            seen[name.lower()] = (name, folder, argv, display)
    return list(seen.values())


def missing_python(kernel: Kernel) -> bool:
    """True when the kernel starts a Python by full path and that file is gone.

    Kernels that use a bare `python` are fine: Jupyter runs them with its own Python.
    """
    exe = kernel[2][0]
    return os.path.isabs(exe) and not os.path.exists(exe)


def env_name(prefix: str) -> str:
    """A readable kernel name for an environment: `.venv` folders are named after the project."""
    base = os.path.basename(os.path.normpath(prefix))
    if base.lower() in (".venv", "venv", "env", ".env"):
        base = os.path.basename(os.path.dirname(os.path.normpath(prefix))) or base
    return "".join(c if c.isalnum() or c in "-_." else "-" for c in base).strip("-") or "myenv"


def is_registered(kernels: List[Kernel], prefix: str, executable: str) -> bool:
    for _, _, argv, _ in kernels:
        exe = argv[0]
        if os.path.isabs(exe) and (norm(exe) == norm(executable) or is_within(exe, prefix)):
            return True
    return False


def run_check(opts: Options, kernel_dirs: Optional[List[str]] = None,
              prefix: Optional[str] = None, executable: Optional[str] = None,
              has_ipykernel: Optional[bool] = None, is_env: Optional[bool] = None,
              has_jupyter: Optional[bool] = None) -> List[Finding]:
    prefix = prefix or sys.prefix
    executable = executable or sys.executable
    if has_ipykernel is None:
        has_ipykernel = importlib.util.find_spec("ipykernel") is not None
    if has_jupyter is None:
        has_jupyter = any(importlib.util.find_spec(m) is not None
                          for m in ("jupyter_server", "notebook", "jupyterlab"))
    if is_env is None:
        is_env = in_virtualenv() or os.path.isdir(os.path.join(prefix, "conda-meta"))
    kernels = find_kernels(kernel_dirs if kernel_dirs is not None else jupyter_dirs(prefix))

    if not kernels and not has_ipykernel:
        return [Finding(CHECK_ID, Status.SKIP, "Jupyter not found")]

    findings: List[Finding] = []

    broken = [k for k in kernels if missing_python(k)]
    if broken:
        findings.append(Finding(
            CHECK_ID, Status.WARN,
            "%d Jupyter kernel(s) point to a Python that no longer exists" % len(broken),
            detail="These kernels fail to start (often after deleting a venv or upgrading "
                   "Python):\n" + "\n".join(
                       "%s -> %s" % (k[0], k[2][0]) for k in broken[:8]),
            fix="Remove each one: jupyter kernelspec remove %s\n"
                "Then register the environment again from inside it: "
                "python -m ipykernel install --user --name <name>" % broken[0][0],
        ))

    # Jupyter installed in this same environment already uses this Python.
    if has_ipykernel and is_env and not has_jupyter and not is_registered(
            kernels, prefix, executable):
        name = env_name(prefix)
        findings.append(Finding(
            CHECK_ID, Status.INFO,
            "This environment has ipykernel, but no Jupyter kernel uses it",
            detail="Notebooks can only use this Python (and its packages) through a kernel. "
                   "Otherwise `import` in a notebook won't see what you installed here.",
            fix='python -m ipykernel install --user --name %s --display-name "Python (%s)"'
                % (name, name),
        ))

    by_display: Dict[str, List[str]] = {}
    shown: Dict[str, str] = {}
    for name, _, _, display in kernels:
        key = display.strip().lower()
        by_display.setdefault(key, []).append(name)
        shown.setdefault(key, display.strip())
    dupes = {shown[d]: n for d, n in by_display.items() if len(n) > 1}
    if dupes:
        findings.append(Finding(
            CHECK_ID, Status.INFO,
            "Several Jupyter kernels have the same name in the kernel picker",
            detail="\n".join("%s: %s" % (d, ", ".join(n)) for d, n in sorted(dupes.items())),
            fix="List them with `jupyter kernelspec list`, then remove old ones "
                "(`jupyter kernelspec remove <name>`) or re-install with a clear "
                '--display-name "Python (project)".',
        ))

    if not findings:
        findings.append(Finding(
            CHECK_ID, Status.OK,
            "%d Jupyter kernel(s) found, all point to a working Python" % len(kernels)
            if kernels else "ipykernel installed, no kernel problems",
        ))
    return findings
