import json
import os

from pyfirstaid import cli, report
from pyfirstaid.model import Check, Finding, Options, Status


def test_list(capsys):
    assert cli.main(["--list"]) == 0
    out = capsys.readouterr().out
    assert "pip-mismatch" in out and "venv" in out and "ssl" in out


def test_json_output_is_valid(capsys):
    code = cli.main(["--offline", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code in (0, 1)
    assert data["tool"] == "pyfirstaid"
    assert {"ok", "info", "warn", "error", "skip"} <= set(data["summary"])
    assert all({"check", "status", "title", "detail", "fix"} <= set(f) for f in data["findings"])


def test_only_and_skip():
    assert [c.id for c in cli.select_checks("venv", None)] == ["venv"]
    assert "ssl" not in [c.id for c in cli.select_checks(None, "ssl")]


def test_crashing_check_is_reported_not_raised():
    def boom(opts):
        raise RuntimeError("kaboom")

    findings = cli.run_checks([Check("boom", "Boom", boom)], Options())
    assert findings[0].status == Status.SKIP and "kaboom" in findings[0].detail


def test_exit_codes(monkeypatch):
    def fake(statuses):
        return lambda checks, opts: [Finding("x", s, "t") for s in statuses]

    monkeypatch.setattr(cli, "run_checks", fake([Status.OK]))
    assert cli.main(["--json"]) == 0
    monkeypatch.setattr(cli, "run_checks", fake([Status.WARN]))
    assert cli.main(["--json"]) == 0
    assert cli.main(["--json", "--strict"]) == 1
    monkeypatch.setattr(cli, "run_checks", fake([Status.ERROR]))
    assert cli.main(["--json"]) == 1


def test_redact_hides_home():
    home = os.path.expanduser("~")
    assert home not in report.redact("path is %s/project" % home)


def test_text_report_shows_fix():
    text = report.render_text([Finding("x", Status.ERROR, "Broken", "why", "do this")])
    assert "Broken" in text and "fix: do this" in text and "1 problem(s)" in text
