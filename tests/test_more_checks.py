import datetime as dt
import os

from pyfirstaid.checks import (
    broken_installs,
    compiled,
    dependencies,
    encoding,
    leaks,
    path_check,
    python_version,
    shadowing,
)
from pyfirstaid.model import Options, Status

# --- python-version ---------------------------------------------------------

def test_eol_status():
    today = dt.date(2026, 10, 8)
    assert python_version.eol_status((3, 9), today)[0] == "eol"
    assert python_version.eol_status((3, 10), today)[0] == "soon"
    assert python_version.eol_status((3, 13), today)[0] == "ok"
    assert python_version.eol_status((3, 99), today)[0] == "unknown"
    assert python_version.eol_status((3, 5), today)[0] == "eol"


def test_is_apple_python():
    assert python_version.is_apple_python(
        "/Library/Developer/CommandLineTools/usr/bin/python3", "")
    assert not python_version.is_apple_python("/opt/homebrew/bin/python3", "/opt/homebrew")


def test_python_version_check_runs():
    findings = python_version.run_check(Options(), today=dt.date(2026, 1, 1))
    assert findings and findings[0].check == "python-version"


# --- compiled ---------------------------------------------------------------

LINUX_313 = [".cpython-313-x86_64-linux-gnu.so", ".abi3.so", ".so"]
WIN_313 = [".cp313-win_amd64.pyd", ".pyd"]


def test_mismatched_tag_linux():
    ok = "numpy/_core/_multiarray.cpython-313-x86_64-linux-gnu.so"
    bad = "numpy/_core/_multiarray.cpython-312-x86_64-linux-gnu.so"
    assert compiled.mismatched_tag(ok, LINUX_313) is None
    assert compiled.mismatched_tag(bad, LINUX_313) == "cpython-312-x86_64-linux-gnu"
    assert compiled.mismatched_tag("pkg/_speedups.abi3.so", LINUX_313) is None
    assert compiled.mismatched_tag("pkg/_plain.so", LINUX_313) is None


def test_mismatched_tag_windows():
    assert compiled.mismatched_tag(r"pkg\_x.cp313-win_amd64.pyd", WIN_313) is None
    assert compiled.mismatched_tag(r"pkg\_x.cp311-win_amd64.pyd", WIN_313) == "cp311-win_amd64"


def test_shared_libraries_are_not_extensions():
    # vendored C libraries such as libopenblas64_p-r0-0cf96a72.3.23.dev.so must be ignored
    assert compiled.mismatched_tag("numpy.libs/libopenblas64_p-r0.3.23.dev.so", LINUX_313) is None


# --- broken-installs --------------------------------------------------------

def test_scan_dir_finds_duplicates_leftovers_and_corruption(tmp_path):
    for d in ("requests-2.31.0.dist-info", "requests-2.32.3.dist-info", "~umpy",
              "six-1.16.0.dist-info", "idna-3.7.dist-info"):
        (tmp_path / d).mkdir()
    for d in ("requests-2.31.0.dist-info", "requests-2.32.3.dist-info", "six-1.16.0.dist-info"):
        (tmp_path / d / "METADATA").write_text("Name: x\n")
    titles = [f.title for f in broken_installs.scan_dir(str(tmp_path))]
    assert any("requests is installed more than once" in t for t in titles)
    assert any("~umpy" in t for t in titles)
    assert any("idna-3.7.dist-info has no METADATA" in t for t in titles)
    assert not any("six" in t for t in titles)


def test_normalize():
    assert broken_installs.normalize("Typing_Extensions") == "typing-extensions"


# --- dependencies -----------------------------------------------------------

def test_fix_for_missing_and_wrong_version():
    assert dependencies.fix_for("foo 1.0 requires bar, which is not installed.") == \
        'python -m pip install "bar"'
    assert dependencies.fix_for(
        "foo 1.0 has requirement bar>=2.0, but you have bar 1.5.") == \
        'python -m pip install "bar>=2.0"'


# --- path -------------------------------------------------------------------

def test_store_stub_detection():
    assert path_check.is_store_stub(
        r"C:\Users\me\AppData\Local\Microsoft\WindowsApps\python.exe")
    assert not path_check.is_store_stub("/usr/bin/python3")


# --- leaks ------------------------------------------------------------------

def test_pythonpath_and_pythonhome(monkeypatch):
    monkeypatch.setenv("PYTHONPATH", "/somewhere/else")
    monkeypatch.setenv("PYTHONHOME", "/bad/home")
    titles = [f.title for f in leaks.run_check(Options())]
    assert any("PYTHONPATH" in t for t in titles)
    assert any("PYTHONHOME" in t for t in titles)


def test_system_site_enabled(tmp_path):
    (tmp_path / "pyvenv.cfg").write_text("home = /usr/bin\ninclude-system-site-packages = true\n")
    assert leaks.system_site_enabled(str(tmp_path))


# --- shadowing --------------------------------------------------------------

def test_shadowing(tmp_path):
    (tmp_path / "random.py").write_text("")
    (tmp_path / "requests.py").write_text("")
    (tmp_path / "test.py").write_text("")          # ignored on purpose
    (tmp_path / "my_tool.py").write_text("")
    stdlib, installed = {"random", "test"}, {"requests"}
    folder = str(tmp_path)
    assert shadowing.shadowed_by("random.py", folder, stdlib, installed) == "stdlib"
    assert shadowing.shadowed_by("requests.py", folder, stdlib, installed) == "installed"
    assert shadowing.shadowed_by("test.py", folder, stdlib, installed) is None
    assert shadowing.shadowed_by("my_tool.py", folder, stdlib, installed) is None


def test_shadowing_check_reports(tmp_path):
    (tmp_path / "json.py").write_text("")
    findings = shadowing.run_check(Options(cwd=str(tmp_path)))
    assert findings[0].status == Status.WARN and "json" in findings[0].title


# --- encoding ---------------------------------------------------------------

def test_is_utf8():
    assert encoding.is_utf8("UTF-8") and encoding.is_utf8("utf8")
    assert not encoding.is_utf8("cp1252")


def test_all_checks_registered():
    from pyfirstaid.checks import ALL_CHECKS

    ids = [c.id for c in ALL_CHECKS]
    assert len(ids) == len(set(ids)) == 12
    assert os.path.basename(__file__)  # keeps `os` used


# --- v0.2.2 regressions found on a real Mac (Homebrew) ------------------------

def test_pip_in_homebrew_site_packages_outside_prefix(tmp_path):
    # Homebrew: sys.prefix is .../Frameworks/Python.framework/Versions/3.14, but
    # site-packages lives in /opt/homebrew/lib/python3.14/site-packages
    from pyfirstaid.checks import pip_mismatch

    prefix = str(tmp_path / "Frameworks" / "Versions" / "3.14")
    site_dir = str(tmp_path / "lib" / "python3.14" / "site-packages")
    loc = os.path.join(site_dir, "pip")
    assert not pip_mismatch.pip_belongs_here(loc, "3.14", "3.14", [prefix])
    assert pip_mismatch.pip_belongs_here(loc, "3.14", "3.14", [prefix, site_dir])


def test_norm_resolves_symlinks(tmp_path):
    from pyfirstaid.util import norm

    real = tmp_path / "Cellar" / "python"
    real.mkdir(parents=True)
    link = tmp_path / "opt-python"
    link.symlink_to(real)
    assert norm(str(link)) == norm(str(real))


def test_dependency_conflicts_in_system_python_are_info(monkeypatch):
    monkeypatch.setattr(dependencies, "system_managed", lambda: True)
    monkeypatch.setattr(dependencies, "run", lambda cmd, timeout=0: (
        1, "wheel 0.48.0 requires packaging, which is not installed.", ""))
    findings = dependencies.run_check(Options())
    assert len(findings) == 1 and findings[0].status == Status.INFO
    assert "pip install" not in findings[0].fix.split("Don't pip install")[-1].split(".")[0]


def test_dependency_conflicts_in_venv_are_warnings(monkeypatch):
    monkeypatch.setattr(dependencies, "system_managed", lambda: False)
    monkeypatch.setattr(dependencies, "run", lambda cmd, timeout=0: (
        1, "wheel 0.48.0 requires packaging, which is not installed.", ""))
    findings = dependencies.run_check(Options())
    assert findings[0].status == Status.WARN and 'install "packaging"' in findings[0].fix
