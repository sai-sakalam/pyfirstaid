import os
import ssl
import sys
import urllib.error

from pyfirstaid.checks import pip_mismatch, ssl_check, venv
from pyfirstaid.model import Options, Status

# --- pip-mismatch -----------------------------------------------------------

def test_parse_pip_version_posix():
    out = "pip 24.0 from /usr/lib/python3/dist-packages/pip (python 3.13)"
    assert pip_mismatch.parse_pip_version(out) == (
        "24.0", "/usr/lib/python3/dist-packages/pip", "3.13")


def test_parse_pip_version_windows_path_with_spaces():
    out = r"pip 25.1 from C:\Program Files\Python313\Lib\site-packages\pip (python 3.13)"
    assert pip_mismatch.parse_pip_version(out)[1].endswith(r"site-packages\pip")


def test_parse_pip_version_garbage():
    assert pip_mismatch.parse_pip_version("Traceback (most recent call last):") is None


def test_pip_belongs_here(tmp_path):
    prefix = str(tmp_path / "venv")
    loc = os.path.join(prefix, "lib", "site-packages", "pip")
    assert pip_mismatch.pip_belongs_here(loc, "3.13", "3.13", [prefix])
    assert not pip_mismatch.pip_belongs_here(loc, "3.12", "3.13", [prefix])
    assert not pip_mismatch.pip_belongs_here("/usr/lib/pip", "3.13", "3.13", [prefix])


def test_pip_check_runs_without_crashing():
    findings = pip_mismatch.run_check(Options(offline=True))
    assert findings and all(f.check == "pip-mismatch" for f in findings)


# --- venv -------------------------------------------------------------------

def test_find_unused_venv(tmp_path):
    assert venv.find_unused_venv(str(tmp_path)) is None
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "pyvenv.cfg").write_text("home = /usr/bin\n")
    assert venv.find_unused_venv(str(tmp_path)).endswith(".venv")


def test_activate_command_mentions_path():
    assert ".venv" in venv.activate_command(".venv")


def test_wrong_venv_activated(monkeypatch, tmp_path):
    monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path / "some-other-venv"))
    findings = venv.run_check(Options(cwd=str(tmp_path)))
    assert any("DIFFERENT virtual environment" in f.title for f in findings)


# --- ssl --------------------------------------------------------------------

def test_bad_cert_env_vars(tmp_path):
    good = tmp_path / "ca.pem"
    good.write_text("x")
    env = {"SSL_CERT_FILE": str(tmp_path / "missing.pem"), "REQUESTS_CA_BUNDLE": str(good)}
    assert ssl_check.bad_cert_env_vars(env) == ["SSL_CERT_FILE"]


def test_classify_error():
    cert = urllib.error.URLError(ssl.SSLCertVerificationError("CERTIFICATE_VERIFY_FAILED"))
    assert ssl_check.classify_error(cert) == "cert"
    assert ssl_check.classify_error(urllib.error.URLError(ssl.SSLError("bad"))) == "ssl"
    assert ssl_check.classify_error(urllib.error.URLError(OSError("no route"))) == "network"


def test_ssl_offline_skips_network(monkeypatch):
    for name in ssl_check.CERT_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    findings = ssl_check.run_check(Options(offline=True))
    assert any(f.status == Status.SKIP for f in findings)
    if sys.platform != "darwin":
        assert all(f.status != Status.ERROR for f in findings)
