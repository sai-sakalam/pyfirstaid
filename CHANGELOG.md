# Changelog

## 0.1.0 (unreleased)

First version, with 3 checks:

- **venv**: is a virtual environment active, is an unused `.venv` sitting in the folder,
  is a *different* venv activated in your shell, and does the system Python block pip (PEP 668)?
- **pip-mismatch**: does the `pip` command install into a different Python than the one you run?
- **ssl**: can Python reach pypi.org over HTTPS, and are certificate settings
  (`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `PIP_CERT`, macOS certificates) valid?

Options: `--json`, `--share`, `--offline`, `--strict`, `--only`, `--skip`, `--list`.
Single-file build: `python scripts/build_pyz.py` creates `dist/pyfirstaid.pyz`.
