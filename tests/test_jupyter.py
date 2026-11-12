import json

from pyfirstaid.checks import jupyter
from pyfirstaid.model import Options, Status


def add_kernel(base, name, python, display=None):
    folder = base / name
    folder.mkdir(parents=True)
    spec = {"argv": [python, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": display or name, "language": "python"}
    (folder / "kernel.json").write_text(json.dumps(spec))


def check(kernels_dir, **kw):
    kw.setdefault("has_ipykernel", False)
    kw.setdefault("is_env", False)
    kw.setdefault("has_jupyter", False)
    return jupyter.run_check(Options(), kernel_dirs=[str(kernels_dir)], **kw)


def test_no_jupyter_is_skipped(tmp_path):
    assert [f.status for f in check(tmp_path / "none")] == [Status.SKIP]


def test_working_kernels_are_ok(tmp_path):
    kernels = tmp_path / "kernels"
    python = tmp_path / "bin" / "python"
    python.parent.mkdir()
    python.write_text("")
    add_kernel(kernels, "project", str(python))
    add_kernel(kernels, "python3", "python", "Python 3 (ipykernel)")  # bare name is fine
    findings = check(kernels)
    assert [f.status for f in findings] == [Status.OK]
    assert "2 Jupyter kernel(s)" in findings[0].title


def test_kernel_with_missing_python(tmp_path):
    kernels = tmp_path / "kernels"
    add_kernel(kernels, "old-project", str(tmp_path / "deleted" / ".venv" / "bin" / "python"))
    findings = check(kernels)
    assert findings[0].status == Status.WARN
    assert "no longer exists" in findings[0].title
    assert "old-project" in findings[0].detail
    assert "jupyter kernelspec remove old-project" in findings[0].fix


def test_env_with_ipykernel_not_registered(tmp_path):
    prefix = tmp_path / "myproject" / ".venv"
    prefix.mkdir(parents=True)
    findings = check(tmp_path / "kernels", has_ipykernel=True, is_env=True,
                     prefix=str(prefix), executable=str(prefix / "bin" / "python"))
    assert findings[0].status == Status.INFO
    assert "--name myproject" in findings[0].fix


def test_env_registered_is_ok(tmp_path):
    prefix = tmp_path / "proj" / ".venv"
    python = prefix / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("")
    kernels = tmp_path / "kernels"
    add_kernel(kernels, "proj", str(python))
    findings = check(kernels, has_ipykernel=True, is_env=True,
                     prefix=str(prefix), executable=str(python))
    assert [f.status for f in findings] == [Status.OK]


def test_jupyter_in_same_env_needs_no_kernel(tmp_path):
    prefix = tmp_path / "env"
    prefix.mkdir()
    findings = check(tmp_path / "kernels", has_ipykernel=True, is_env=True, has_jupyter=True,
                     prefix=str(prefix), executable=str(prefix / "bin" / "python"))
    assert [f.status for f in findings] == [Status.OK]


def test_duplicate_display_names(tmp_path):
    kernels = tmp_path / "kernels"
    add_kernel(kernels, "a", "python", "Python 3")
    add_kernel(kernels, "b", "python3", "Python 3")
    findings = check(kernels)
    assert findings[0].status == Status.INFO
    assert "same name" in findings[0].title


def test_first_kernel_folder_wins_and_bad_files_are_ignored(tmp_path):
    user, system = tmp_path / "user", tmp_path / "system"
    add_kernel(user, "py", "python")
    add_kernel(system, "py", str(tmp_path / "missing" / "python"))  # hidden by the user one
    (system / "broken").mkdir()
    (system / "broken" / "kernel.json").write_text("{not json")
    (system / "noargv").mkdir()
    (system / "noargv" / "kernel.json").write_text(json.dumps({"display_name": "x"}))
    kernels = jupyter.find_kernels([str(user), str(system)])
    assert [k[0] for k in kernels] == ["py"]
    assert kernels[0][2][0] == "python"


def test_env_name():
    assert jupyter.env_name("/home/me/shop/.venv") == "shop"
    assert jupyter.env_name("/opt/conda/envs/data science") == "data-science"


def test_jupyter_dirs_respect_env_vars(tmp_path, monkeypatch):
    monkeypatch.setenv("JUPYTER_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("JUPYTER_PATH", str(tmp_path / "extra"))
    dirs = jupyter.jupyter_dirs(str(tmp_path / "prefix"))
    assert dirs[0] == str(tmp_path / "data" / "kernels")
    assert dirs[1] == str(tmp_path / "extra" / "kernels")
    assert str(tmp_path / "prefix" / "share" / "jupyter" / "kernels") in dirs


def test_real_environment_does_not_crash():
    findings = jupyter.run_check(Options())
    assert findings and all(f.check == "jupyter" for f in findings)
