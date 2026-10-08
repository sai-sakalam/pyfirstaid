# pyfirstaid 🩹
[![CI](https://github.com/sai-sakalam/pyfirstaid/actions/workflows/ci.yml/badge.svg)](https://github.com/sai-sakalam/pyfirstaid/actions/workflows/ci.yml)

**First aid for broken Python environments.** One command tells you *what's broken* and *exactly how to fix it*.

> **Status: v0.2.** 12 checks, tested on Windows, macOS and Linux (Python 3.9–3.14).
> Feedback is very welcome in [Issues](https://github.com/sai-sakalam/pyfirstaid/issues). *Which problems do you hit most?*

---

## Why

"It works on my machine" usually comes down to a broken environment: `pip` installing into a different Python than you run, SSL errors behind a corporate proxy, or a virtual environment that isn't active.

The errors are cryptic, the fixes are scattered across Stack Overflow, and there's no single command that checks it all.

This was discussed on the Python forum: [Standard Library Health Check Module](https://discuss.python.org/t/standard-library-health-check-module/105153). The advice there was to start it as a package on PyPI.

## Example

A real run: the virtual environment's Python is running, but the `pip` command on PATH belongs to the system Python:

```console
$ python -m pyfirstaid

pyfirstaid 0.1.0: checking your Python environment
Python 3.13.1 (~/project/.venv/bin/python)

✔ Virtual environment active: ~/project/.venv
✘ `pip` installs into a DIFFERENT Python
    pip    -> /usr/lib/python3/dist-packages/pip (python 3.13)
    python -> ~/project/.venv/bin/python (python 3.13)
    fix: Use `python -m pip install <package>` instead of `pip install`. If a virtual environment should be active, activate it first.
✔ HTTPS to pypi.org works (OpenSSL 3.0.13 30 Jan 2024)

1 problem(s), 0 warning(s).
```

## Try it

```bash
pip install pyfirstaid          # or: pipx install pyfirstaid
python -m pyfirstaid
```

No install possible (for example, pip itself is broken)? Download `pyfirstaid.pyz` from the
[latest release](https://github.com/sai-sakalam/pyfirstaid/releases) and run:

```bash
python pyfirstaid.pyz
```

### Options

| Option | What it does |
|---|---|
| `--share` | Hides your username and home folder, so the report is safe to paste into a bug report |
| `--json` | Machine-readable output for CI and scripts |
| `--offline` | Skips checks that need the internet |
| `--strict` | Exits with code 1 on warnings too (useful in CI) |
| `--only venv,ssl` / `--skip ssl` | Runs only some checks, or skips some |
| `--list` | Lists all checks |

Exit codes: `0` means no problems, `1` means problems were found, `2` means pyfirstaid itself failed.

## Common situations

**"I installed a package, but `import` says it doesn't exist."**

    python -m pyfirstaid --only pip-mismatch,venv

Usually `pip` installed into a different Python, or your virtual environment isn't active. pyfirstaid tells you which, and how to fix it.

**"pip install fails with SSL: CERTIFICATE_VERIFY_FAILED at work."**

    python -m pyfirstaid --only ssl

This checks whether a company proxy is intercepting HTTPS and whether your certificate settings point at real files.

**"I'm reporting a bug and the maintainer asked for my environment details."**

    python -m pyfirstaid --share

Paste the output into the issue. Your username and home folder are hidden.

**"I want CI to fail if the environment is broken."**

    python -m pyfirstaid --offline --strict --json > env-report.json

The exit code is `1` if there are problems, and the JSON report can be saved as a build artifact.

**"pip itself is broken, so I can't install anything."**

Download `pyfirstaid.pyz` from the [latest release](https://github.com/sai-sakalam/pyfirstaid/releases) and run:

    python pyfirstaid.pyz

## Checks

| Check | What it catches |
|---|---|
| `python-version` | Python past (or close to) end of life, pre-release Pythons, Apple's built-in Command Line Tools Python |
| `venv` | No venv active, an unused `.venv` in the folder, a *different* venv activated in your shell, a system Python that blocks pip (PEP 668) |
| `pip-mismatch` | `pip` installs into a different Python than the one you run, pip missing, a broken `pip` command |
| `path` | Typing `python` / `python3` runs a *different* Python, or the Windows Microsoft Store shortcut |
| `leaks` | `PYTHONPATH` / `PYTHONHOME` set, venvs that can see system packages |
| `shadowing` | Files like `random.py` or `requests.py` in your folder that hide real modules |
| `ssl` | Certificate failures reaching PyPI (corporate proxies), certificate variables pointing at missing files, macOS certificates not installed, Python built without SSL |
| `compiled` | Packages with compiled files built for a different Python version |
| `broken-installs` | Packages installed twice, `~` leftovers from interrupted installs, corrupted metadata |
| `dependencies` | Dependency conflicts (`pip check`), each with a suggested fix |
| `permissions` | Virtual environments you can't install into (e.g. created with sudo) |
| `encoding` | Default text encoding that is not UTF-8 |

Run one or a few: `python -m pyfirstaid --only shadowing,path`. List them all: `python -m pyfirstaid --list`.

## How is this different?

| Tool | What it does | Gap pyfirstaid fills |
|---|---|---|
| `pip check` | Finds dependency conflicts | Only covers one kind of problem |
| `conda doctor` | Health checks for conda environments | Doesn't cover pip, venv or uv |
| pymedic | Lists environment info (versions, packages) | Reports, but doesn't diagnose or suggest fixes |
| pyenv-doctor | Early-stage environment checks | Single release so far |
| env-repair | Repairs conda and pip environments | Changes your environment; pyfirstaid only diagnoses, safely |

**pyfirstaid's focus:** diagnose the problem, explain it in plain English, and give a copy-paste fix.

## Design principles

- **Works when pip is broken.** Install with `pip install pyfirstaid`, or run the single file `python pyfirstaid.pyz` without installing.
- **Zero dependencies.** Standard library only, Python 3.9+.
- **Every problem comes with a fix command,** not just a description.
- **Conservative.** It's better to miss an edge case than to raise a false alarm.
- **Never crashes.** A check that fails internally is reported, and the rest still run.
- **Diagnose only.** It never changes your environment.

## Scope

**In:** pip, venv and uv on Windows, macOS and Linux.
**Out (for now):** conda (use `conda doctor`), Poetry and pyenv specifics, automatic repair.

## Contributing

- Hit an environment error? [Open an issue](https://github.com/sai-sakalam/pyfirstaid/issues) with the error message, the cause and the fix. Real cases decide which checks come next.
- Development: `python -m pip install -e ".[dev]"`, then `python -m pytest` and `ruff check src tests`.
- A new check is one file in `src/pyfirstaid/checks/` that returns a list of `Finding`s, registered in `checks/__init__.py`.

## License

MIT
