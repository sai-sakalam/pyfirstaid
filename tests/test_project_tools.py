"""Tests for the uv, Poetry and pyenv checks (all work on fake folders)."""

import os
import sys

from pyfirstaid import util
from pyfirstaid.checks import pip_mismatch, poetry, pyenv, uv
from pyfirstaid.model import Options, Status


def make_venv(path, home, extra=""):
    path.mkdir(parents=True, exist_ok=True)
    (path / "pyvenv.cfg").write_text("home = %s\n%s" % (home, extra))
    return path


# --- util helpers ---------------------------------------------------------------

def test_read_pyvenv_cfg_and_broken_base(tmp_path):
    good = make_venv(tmp_path / "good", str(tmp_path), "uv = 0.9.0\n")
    bad = make_venv(tmp_path / "bad", str(tmp_path / "gone" / "bin"))
    assert util.read_pyvenv_cfg(str(good))["uv"] == "0.9.0"
    assert util.broken_venv_base(str(good)) is None
    assert util.broken_venv_base(str(bad)) == str(tmp_path / "gone" / "bin")
    assert util.read_pyvenv_cfg(str(tmp_path / "missing")) == {}


def test_find_upwards(tmp_path):
    (tmp_path / "uv.lock").write_text("")
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    assert util.find_upwards(str(deep), "uv.lock") == str(tmp_path / "uv.lock")
    assert util.find_upwards(str(deep), "no-such-file-anywhere.xyz") is None


def test_simple_toml_fallback():
    data = util._simple_toml('[project]\nname = "shop"\n\n[tool.poetry]\nname = \'shop2\'\n')
    assert data["project"]["name"] == "shop"
    assert data["tool"]["poetry"]["name"] == "shop2"


def test_read_pyproject_without_tomllib(tmp_path, monkeypatch):
    # Python 3.9 / 3.10 have no tomllib: the simple reader must take over
    monkeypatch.setitem(sys.modules, "tomllib", None)
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "shop"\n')
    assert util.read_pyproject(str(tmp_path))["project"]["name"] == "shop"


def test_read_pyproject(tmp_path):
    assert util.read_pyproject(str(tmp_path)) == {}
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "shop"\n')
    assert util.read_pyproject(str(tmp_path))["tool"]["poetry"]["name"] == "shop"


# --- uv -------------------------------------------------------------------------

def run_uv(tmp_path, prefix, in_venv=True):
    return uv.run_check(Options(cwd=str(tmp_path)), prefix=str(prefix), in_venv=in_venv)


def test_uv_not_a_project_is_skipped(tmp_path):
    assert [f.status for f in run_uv(tmp_path, tmp_path / "py")] == [Status.SKIP]


def test_uv_env_outside_project_is_ok(tmp_path):
    env = make_venv(tmp_path / "env", str(tmp_path), "uv = 0.9.0\n")
    findings = run_uv(tmp_path, env)
    assert findings[0].status == Status.OK and "uv pip install" in findings[0].fix


def test_uv_project_not_synced(tmp_path, monkeypatch):
    monkeypatch.delenv("UV_PROJECT_ENVIRONMENT", raising=False)
    (tmp_path / "uv.lock").write_text("")
    findings = run_uv(tmp_path, tmp_path / "other", in_venv=False)
    assert findings[0].status == Status.INFO and findings[0].fix == "uv sync"


def test_uv_running_project_env(tmp_path, monkeypatch):
    monkeypatch.delenv("UV_PROJECT_ENVIRONMENT", raising=False)
    (tmp_path / "uv.lock").write_text("")
    env = make_venv(tmp_path / ".venv", str(tmp_path))
    assert [f.status for f in run_uv(tmp_path, env)] == [Status.OK]


def test_uv_from_a_subfolder(tmp_path, monkeypatch):
    monkeypatch.delenv("UV_PROJECT_ENVIRONMENT", raising=False)
    (tmp_path / "uv.lock").write_text("")
    env = make_venv(tmp_path / ".venv", str(tmp_path))
    sub = tmp_path / "src"
    sub.mkdir()
    findings = uv.run_check(Options(cwd=str(sub)), prefix=str(env), in_venv=True)
    assert [f.status for f in findings] == [Status.OK]


def test_uv_different_env_running(tmp_path, monkeypatch):
    monkeypatch.delenv("UV_PROJECT_ENVIRONMENT", raising=False)
    (tmp_path / "uv.lock").write_text("")
    make_venv(tmp_path / ".venv", str(tmp_path))
    other = make_venv(tmp_path / "other-venv", str(tmp_path))
    findings = run_uv(tmp_path, other)
    assert findings[0].status == Status.WARN and "DIFFERENT" in findings[0].title
    assert "uv run" in findings[0].fix
    findings = run_uv(tmp_path, tmp_path / "system", in_venv=False)
    assert findings[0].status == Status.INFO


def test_uv_broken_project_env(tmp_path, monkeypatch):
    monkeypatch.delenv("UV_PROJECT_ENVIRONMENT", raising=False)
    (tmp_path / "uv.lock").write_text("")
    make_venv(tmp_path / ".venv", str(tmp_path / "old-python" / "bin"))
    findings = run_uv(tmp_path, tmp_path / "x")
    assert findings[0].status == Status.WARN and "broken" in findings[0].title
    assert "uv sync" in findings[0].fix


def test_uv_project_environment_variable(tmp_path, monkeypatch):
    (tmp_path / "uv.lock").write_text("")
    env = make_venv(tmp_path / "envs" / "shop", str(tmp_path))
    monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", "envs/shop")
    assert [f.status for f in run_uv(tmp_path, env)] == [Status.OK]


def test_pip_missing_in_uv_env_gives_uv_fix(monkeypatch, tmp_path):
    make_venv(tmp_path, str(tmp_path), "uv = 0.9.0\n")
    monkeypatch.setattr(pip_mismatch.sys, "prefix", str(tmp_path))
    monkeypatch.setattr(pip_mismatch, "run", lambda cmd, timeout: (1, "", "No module named pip"))
    findings = pip_mismatch.run_check(Options())
    assert findings[0].status == Status.INFO and "uv pip install" in findings[0].fix


# --- Poetry ---------------------------------------------------------------------

def poetry_project(tmp_path, name="Shop"):
    root = tmp_path / "shop"
    root.mkdir()
    (root / "pyproject.toml").write_text('[tool.poetry]\nname = "%s"\n' % name)
    (root / "poetry.lock").write_text("")
    return root


def run_poetry(root, prefix, cache, in_venv=True):
    return poetry.run_check(Options(cwd=str(root)), prefix=str(prefix), in_venv=in_venv,
                            cache_dir=str(cache))


def test_poetry_not_a_project(tmp_path):
    findings = run_poetry(tmp_path, tmp_path, tmp_path / "cache")
    assert [f.status for f in findings] == [Status.SKIP]


def test_poetry_env_name_matches_poetry():
    # Same formula as Poetry's EnvManager.generate_env_name
    name = poetry.env_name("My Shop", "/tmp")
    assert name.startswith("my_shop-") and len(name.split("-")[-1]) == 8


def test_poetry_no_env_yet(tmp_path):
    root = poetry_project(tmp_path)
    findings = run_poetry(root, tmp_path / "py", tmp_path / "cache", in_venv=False)
    assert findings[0].status == Status.INFO and findings[0].fix == "poetry install"


def test_poetry_running_cache_env(tmp_path):
    root = poetry_project(tmp_path)
    cache = tmp_path / "cache"
    env = make_venv(cache / (poetry.env_name("Shop", str(root)) + "-py3.12"), str(tmp_path))
    assert [f.status for f in run_poetry(root, env, cache)] == [Status.OK]


def test_poetry_moved_project_env_still_counts(tmp_path):
    root = poetry_project(tmp_path)
    cache = tmp_path / "cache"
    env = make_venv(cache / "shop-AbCdEfGh-py3.12", str(tmp_path))  # hash from an old path
    assert [f.status for f in run_poetry(root, env, cache)] == [Status.OK]


def test_poetry_in_project_venv(tmp_path):
    root = poetry_project(tmp_path)
    env = make_venv(root / ".venv", str(tmp_path))
    assert [f.status for f in run_poetry(root, env, tmp_path / "cache")] == [Status.OK]


def test_poetry_different_env_running(tmp_path):
    root = poetry_project(tmp_path)
    cache = tmp_path / "cache"
    make_venv(cache / (poetry.env_name("Shop", str(root)) + "-py3.12"), str(tmp_path))
    findings = run_poetry(root, tmp_path / "elsewhere", cache)
    assert findings[0].status == Status.WARN and "poetry run" in findings[0].fix


def test_poetry_broken_env(tmp_path):
    root = poetry_project(tmp_path)
    cache = tmp_path / "cache"
    make_venv(cache / (poetry.env_name("Shop", str(root)) + "-py3.11"),
              str(tmp_path / "gone" / "bin"))
    findings = run_poetry(root, tmp_path / "elsewhere", cache)
    assert findings[0].status == Status.WARN and "broken" in findings[0].title
    assert "poetry env remove python3.11" in findings[0].fix


def test_poetry_pep621_name(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "shop"\n[tool.poetry]\n')
    assert poetry.project_name(str(tmp_path)) == "shop"


# --- pyenv ----------------------------------------------------------------------

def fake_pyenv(tmp_path, versions=()):
    root = tmp_path / "pyenv"
    for v in versions:
        (root / "versions" / v).mkdir(parents=True)
    (root / "versions").mkdir(parents=True, exist_ok=True)
    (root / "shims").mkdir()
    return root


def run_pyenv(cwd, root, running=(3, 12, 4)):
    return pyenv.run_check(Options(cwd=str(cwd)), root=str(root) if root else "",
                           running=running)


def test_pyenv_matches():
    assert pyenv.matches("3.12", (3, 12, 4)) is True
    assert pyenv.matches("3.12.4", (3, 12, 4)) is True
    assert pyenv.matches("3.12.5", (3, 12, 4)) is False
    assert pyenv.matches("3.13", (3, 12, 4)) is False
    assert pyenv.matches("system", (3, 12, 4)) is None
    assert pyenv.matches("pypy3.10", (3, 12, 4)) is None


def test_pyenv_nothing_is_skipped(tmp_path, monkeypatch):
    monkeypatch.delenv("PYENV_VERSION", raising=False)
    project = tmp_path / "p"
    project.mkdir()
    findings = run_pyenv(project, None)
    # a .python-version higher up (e.g. in the home folder) would also be valid
    assert findings[0].status in (Status.SKIP, Status.OK, Status.WARN, Status.INFO)


def test_version_file_matches(tmp_path, monkeypatch):
    monkeypatch.delenv("PYENV_VERSION", raising=False)
    (tmp_path / ".python-version").write_text("# comment\n3.12\n")
    findings = run_pyenv(tmp_path, fake_pyenv(tmp_path, ["3.12.4"]))
    assert [f.status for f in findings] == [Status.OK]


def test_version_file_not_installed_in_pyenv(tmp_path, monkeypatch):
    monkeypatch.delenv("PYENV_VERSION", raising=False)
    (tmp_path / ".python-version").write_text("3.11.9\n")
    findings = run_pyenv(tmp_path, fake_pyenv(tmp_path, ["3.12.4"]))
    assert findings[0].status == Status.WARN
    assert findings[0].fix.startswith("pyenv install 3.11.9")


def test_version_mismatch_shims_missing_from_path(tmp_path, monkeypatch):
    monkeypatch.delenv("PYENV_VERSION", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    (tmp_path / ".python-version").write_text("3.11\n")
    findings = run_pyenv(tmp_path, fake_pyenv(tmp_path, ["3.11.9"]))
    assert findings[0].status == Status.WARN
    assert "3.11" in findings[0].title and "3.12.4" in findings[0].title
    if os.name != "nt":
        assert "pyenv init" in findings[0].fix


def test_version_mismatch_without_pyenv(tmp_path, monkeypatch):
    monkeypatch.delenv("PYENV_VERSION", raising=False)
    (tmp_path / ".python-version").write_text("3.13\n")
    findings = run_pyenv(tmp_path, None)
    assert findings[0].status == Status.WARN and "uv run" in findings[0].fix


def test_pyenv_version_variable_wins(tmp_path, monkeypatch):
    (tmp_path / ".python-version").write_text("3.13\n")
    monkeypatch.setenv("PYENV_VERSION", "3.12.4")
    findings = run_pyenv(tmp_path, fake_pyenv(tmp_path, ["3.12.4"]))
    assert findings[0].status == Status.OK and "PYENV_VERSION" in findings[0].title


def test_non_version_names_are_not_compared(tmp_path, monkeypatch):
    monkeypatch.delenv("PYENV_VERSION", raising=False)
    (tmp_path / ".python-version").write_text("my-virtualenv\n")
    findings = run_pyenv(tmp_path, fake_pyenv(tmp_path))
    assert findings[0].status == Status.INFO


def test_real_environment_does_not_crash():
    for check in (uv, poetry, pyenv):
        findings = check.run_check(Options())
        assert findings and all(f.check == check.CHECK_ID for f in findings)
