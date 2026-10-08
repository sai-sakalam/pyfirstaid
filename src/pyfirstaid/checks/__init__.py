"""Registry of all checks. Add new checks to ALL_CHECKS."""

from __future__ import annotations

from typing import List

from pyfirstaid.checks import pip_mismatch, ssl_check, venv
from pyfirstaid.model import Check

ALL_CHECKS: List[Check] = [
    Check(venv.CHECK_ID, "Virtual environment", venv.run_check),
    Check(pip_mismatch.CHECK_ID, "pip / python match", pip_mismatch.run_check),
    Check(ssl_check.CHECK_ID, "SSL / HTTPS to PyPI", ssl_check.run_check),
]
