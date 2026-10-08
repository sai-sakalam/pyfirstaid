import os
import subprocess
import sys

from pyfirstaid import cli, delegate


def test_in_tool_venv():
    assert delegate.in_tool_venv(
        "/Users/me/Library/Application Support/pipx/venvs/pyfirstaid")
    assert delegate.in_tool_venv("/home/me/.local/share/pipx/venvs/pyfirstaid")
    assert delegate.in_tool_venv("/home/me/.local/share/uv/tools/pyfirstaid")
    assert delegate.in_tool_venv(r"C:\Users\me\pipx\venvs\pyfirstaid")
    assert not delegate.in_tool_venv("/home/me/project/.venv")
    assert not delegate.in_tool_venv("/opt/homebrew/opt/python@3.14")


def test_forwarded_drops_python_option():
    assert cli.forwarded(["--share", "--python", "/x/python", "--only", "venv"]) == \
        ["--share", "--only", "venv"]
    assert cli.forwarded(["--python=/x/python", "--json"]) == ["--json"]


def test_resolve_command_name_and_path():
    assert delegate.resolve(sys.executable) == sys.executable
    assert delegate.resolve(os.path.join("no", "such", "python")) is None


def test_probe_and_same_environment():
    ok, prefix = delegate.probe(sys.executable)
    assert ok and delegate.same_environment(prefix)
    assert not delegate.same_environment("/somewhere/else")


def test_unknown_python_is_an_error(capsys):
    assert cli.main(["--python", "/definitely/not/a/python"]) == cli.EXIT_INTERNAL


def test_delegated_run_produces_report():
    # Run pyfirstaid "inside" this same interpreter through the bootstrap command,
    # exactly as --python would for another interpreter.
    cmd = delegate.build_command(sys.executable, ["--only", "encoding", "--json"])
    env = dict(os.environ, **{delegate.DELEGATED_ENV: "1"})
    out = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
    assert out.returncode == 0, out.stderr
    assert '"check": "encoding"' in out.stdout


def test_probe_missing_python():
    assert delegate.probe("/definitely/not/a/python") is None
