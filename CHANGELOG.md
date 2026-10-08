# Changelog

## 0.2.1

- **Fix: correct results when installed with pipx or `uv tool`.** These tools put pyfirstaid in
  its own private environment, so it used to diagnose *that* environment and report false
  problems (e.g. "pip installs into a DIFFERENT Python"). It now checks the Python you get
  when you type `python3`, and says so in a short note.
- **New `--python PATH` option** to check any interpreter, e.g. `--python python3.12` or
  `--python .venv/bin/python`. The target doesn't need pyfirstaid installed.
- Files in the current folder (e.g. `random.py`) can no longer break pyfirstaid itself.
- Clearer message when no compiled packages are installed.

## 0.2.0

Nine new checks, bringing the total to 12:

- **python-version**: Python past (or close to) end of life, pre-release Pythons, and Apple's
  built-in Command Line Tools Python on macOS.
- **path**: typing `python` / `python3` runs a *different* Python, or opens the Windows
  Microsoft Store shortcut.
- **leaks**: `PYTHONPATH` / `PYTHONHOME` set, and venvs that can see system packages.
- **shadowing**: files like `random.py` or `requests.py` in the current folder that hide real
  modules.
- **compiled**: packages with compiled files built for a different Python version.
- **broken-installs**: packages installed twice, `~` leftovers from interrupted installs,
  and corrupted metadata.
- **dependencies**: dependency conflicts from `pip check`, each with a suggested fix.
- **permissions**: venvs that are not writable (e.g. created with sudo).
- **encoding**: default text encoding that is not UTF-8.

## 0.1.0

First release, with 3 checks:

- **venv**: is a virtual environment active, is an unused `.venv` sitting in the folder,
  is a *different* venv activated in your shell, and does the system Python block pip (PEP 668)?
- **pip-mismatch**: does the `pip` command install into a different Python than the one you run?
- **ssl**: can Python reach pypi.org over HTTPS, and are certificate settings
  (`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `PIP_CERT`, macOS certificates) valid?

Options: `--json`, `--share`, `--offline`, `--strict`, `--only`, `--skip`, `--list`.
