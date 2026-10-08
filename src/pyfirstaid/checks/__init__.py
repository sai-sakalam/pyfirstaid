"""Registry of all checks. Add new checks to ALL_CHECKS."""

from __future__ import annotations

from typing import List

from pyfirstaid.checks import (
    broken_installs,
    compiled,
    dependencies,
    encoding,
    leaks,
    path_check,
    permissions,
    pip_mismatch,
    python_version,
    shadowing,
    ssl_check,
    venv,
)
from pyfirstaid.model import Check

ALL_CHECKS: List[Check] = [
    Check(python_version.CHECK_ID, "Python version", python_version.run_check),
    Check(venv.CHECK_ID, "Virtual environment", venv.run_check),
    Check(pip_mismatch.CHECK_ID, "pip / python match", pip_mismatch.run_check),
    Check(path_check.CHECK_ID, "python on PATH", path_check.run_check),
    Check(leaks.CHECK_ID, "PYTHONPATH / PYTHONHOME", leaks.run_check),
    Check(shadowing.CHECK_ID, "Files hiding real modules", shadowing.run_check),
    Check(ssl_check.CHECK_ID, "SSL / HTTPS to PyPI", ssl_check.run_check),
    Check(compiled.CHECK_ID, "Compiled packages", compiled.run_check),
    Check(broken_installs.CHECK_ID, "Broken installs", broken_installs.run_check),
    Check(dependencies.CHECK_ID, "Dependency conflicts", dependencies.run_check),
    Check(permissions.CHECK_ID, "Install permissions", permissions.run_check),
    Check(encoding.CHECK_ID, "Text encoding", encoding.run_check),
]
