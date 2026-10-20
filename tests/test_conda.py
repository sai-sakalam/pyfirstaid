import json

from pyfirstaid.checks import conda
from pyfirstaid.model import Options, Status


def make_env(tmp_path, base=False, conda_pkgs=(), dists=()):
    """Build a fake conda environment.

    conda_pkgs: (name, version) pairs that conda installed, with their dist-info.
    dists: (dist-info folder name, INSTALLER contents) actually present in site-packages.
    """
    prefix = tmp_path / "env"
    meta = prefix / "conda-meta"
    meta.mkdir(parents=True)
    if base:
        (prefix / "condabin").mkdir()
    site = prefix / "lib" / "site-packages"
    site.mkdir(parents=True)
    for name, ver in conda_pkgs:
        record = {
            "name": name,
            "version": ver,
            "files": ["lib/site-packages/%s/__init__.py" % name,
                      "lib/site-packages/%s-%s.dist-info/METADATA" % (name, ver)],
        }
        (meta / ("%s-%s-0.json" % (name, ver))).write_text(json.dumps(record))
    for folder, installer in dists:
        d = site / folder
        d.mkdir()
        (d / "METADATA").write_text("Name: x\n")
        if installer is not None:
            (d / "INSTALLER").write_text(installer + "\n")
    return str(prefix), [str(site)]


def run(prefix, site_dirs, monkeypatch, active=None):
    if active is None:
        monkeypatch.setenv("CONDA_PREFIX", prefix)
    else:
        monkeypatch.setenv("CONDA_PREFIX", active)
    return conda.run_check(Options(), prefix=prefix, site_dirs=site_dirs)


def test_not_conda_is_skipped(tmp_path, monkeypatch):
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    findings = conda.run_check(Options(), prefix=str(tmp_path), site_dirs=[])
    assert [f.status for f in findings] == [Status.SKIP]


def test_clean_env_is_ok(tmp_path, monkeypatch):
    prefix, sites = make_env(
        tmp_path,
        conda_pkgs=[("numpy", "2.1.0")],
        dists=[("numpy-2.1.0.dist-info", "conda"), ("requests-2.32.0.dist-info", "pip")],
    )
    findings = run(prefix, sites, monkeypatch)
    assert [f.status for f in findings] == [Status.OK]


def test_pip_replaced_conda_package(tmp_path, monkeypatch):
    prefix, sites = make_env(
        tmp_path,
        conda_pkgs=[("numpy", "2.1.0")],
        dists=[("numpy-2.2.0.dist-info", "pip")],  # pip upgraded over conda's numpy
    )
    findings = run(prefix, sites, monkeypatch)
    assert findings[0].status == Status.WARN
    assert "replaced by pip" in findings[0].title
    assert "numpy 2.2.0" in findings[0].detail


def test_conda_owned_dist_is_not_flagged_even_if_installer_says_pip(tmp_path, monkeypatch):
    # some conda packages are built with pip; conda-meta lists the dist-info, so it's conda's
    prefix, sites = make_env(
        tmp_path,
        conda_pkgs=[("numpy", "2.1.0")],
        dists=[("numpy-2.1.0.dist-info", "pip")],
    )
    findings = run(prefix, sites, monkeypatch)
    assert [f.status for f in findings] == [Status.OK]


def test_unknown_installer_is_not_flagged(tmp_path, monkeypatch):
    prefix, sites = make_env(
        tmp_path,
        conda_pkgs=[("numpy", "2.1.0")],
        dists=[("numpy-2.2.0.dist-info", None)],  # no INSTALLER file: stay conservative
    )
    findings = run(prefix, sites, monkeypatch)
    assert [f.status for f in findings] == [Status.OK]


def test_pip_packages_in_base_env(tmp_path, monkeypatch):
    prefix, sites = make_env(
        tmp_path, base=True,
        dists=[("requests-2.32.0.dist-info", "pip")],
    )
    findings = run(prefix, sites, monkeypatch)
    assert findings[0].status == Status.WARN
    assert "base environment" in findings[0].title
    assert "requests" in findings[0].detail


def test_pip_packages_in_normal_env_are_fine(tmp_path, monkeypatch):
    prefix, sites = make_env(tmp_path, dists=[("requests-2.32.0.dist-info", "pip")])
    findings = run(prefix, sites, monkeypatch)
    assert [f.status for f in findings] == [Status.OK]


def test_different_conda_env_activated(tmp_path, monkeypatch):
    prefix, sites = make_env(tmp_path)
    other = tmp_path / "other"
    (other / "conda-meta").mkdir(parents=True)
    findings = run(prefix, sites, monkeypatch, active=str(other))
    assert findings[0].status == Status.WARN
    assert "DIFFERENT conda environment" in findings[0].title


def test_conda_activated_but_python_is_elsewhere(tmp_path, monkeypatch):
    active = tmp_path / "myenv"
    (active / "conda-meta").mkdir(parents=True)
    monkeypatch.setenv("CONDA_PREFIX", str(active))
    findings = conda.run_check(Options(), prefix=str(tmp_path / "not-conda"), site_dirs=[])
    assert findings[0].status == Status.WARN
    assert "not from it" in findings[0].title


def test_conda_records_ignores_bad_json(tmp_path):
    meta = tmp_path / "conda-meta"
    meta.mkdir()
    (meta / "broken.json").write_text("{not json")
    (meta / "ok-1.0-0.json").write_text(json.dumps({"name": "Some_Pkg", "files": []}))
    assert conda.conda_records(str(tmp_path)) == {"some-pkg": set()}


def test_real_environment_does_not_crash():
    findings = conda.run_check(Options())
    assert findings and all(f.check == "conda" for f in findings)
