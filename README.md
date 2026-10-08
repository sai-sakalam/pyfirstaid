# pyfirstaid 🩹

**First aid for broken Python environments.** One command tells you *what's broken* and *exactly how to fix it*.

> ⚠️ **Status: design stage.** Nothing to install yet. This README describes the planned v0.1.
> Feedback is welcome in [Issues](../../issues), especially: *which problems do you hit most?*

---

## Why

"It works on my machine" usually comes down to a broken environment: `pip` installing into a different Python than you run, SSL errors behind a corporate proxy, a compiled package built for the wrong Python version, or a venv that isn't active.

The errors are cryptic, the fixes are scattered across Stack Overflow, and there's no single command that checks it all.

This was discussed on the Python forum: [Standard Library Health Check Module](https://discuss.python.org/t/standard-library-health-check-module/105153). The advice there was to start it as a package on PyPI.

## What it will look like

```console
$ python pyfirstaid.pyz

pyfirstaid: checking your Python environment

✔ Python 3.13.1 (/home/me/proj/.venv/bin/python)
✔ Virtual environment active (.venv)
✘ pip belongs to a DIFFERENT Python
    pip → /usr/bin/python3.11   python → .venv/bin/python3.13
    fix: python -m pip install <package>   (always use "python -m pip")
✘ numpy failed to load (built for Python 3.12, running 3.13)
    fix: python -m pip install --force-reinstall numpy
✔ SSL: pypi.org reachable, certificates OK
⚠ PYTHONPATH is set; packages may leak in from outside this venv
    fix: unset PYTHONPATH

2 problems, 1 warning. Run with --share to copy a privacy-safe report.
```

## Planned v0.1 checks

1. `python` and `pip` point to different installations
2. Virtual environment missing, or the wrong one is active
3. SSL certificate problems reaching PyPI (including proxy settings)
4. Compiled packages that fail to load (wrong Python version)
5. Broken or duplicate package installs
6. Dependency conflicts (`pip check`)
7. Multiple Pythons on PATH shadowing each other
8. `PYTHONPATH` or user-site packages leaking in
9. No write permission on site-packages
10. Locale and encoding problems

## Design principles

- **Works when pip is broken.** It ships as a single file you can run directly (`python pyfirstaid.pyz`), and it's also on PyPI.
- **Zero dependencies.** Standard library only.
- **Every problem comes with a fix command,** not just a description.
- **Conservative.** It's better to miss an edge case than to raise a false alarm.
- **Privacy-safe sharing.** `--share` strips usernames and paths, and `--json` is for CI and bug reports.
- **Diagnose only.** It never changes your environment.

## Scope

**In:** pip, venv and uv on Windows, macOS and Linux.
**Out (for now):** conda (use `conda doctor`), Poetry and pyenv specifics, automatic repair.

## Contributing

Comment on the [Issues](../../issues) with an environment error you've hit, the cause and the fix. Real cases decide which checks come first.

## License

MIT
