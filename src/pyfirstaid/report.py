"""Render findings as text or JSON, with optional privacy redaction."""

from __future__ import annotations

import getpass
import json
import os
import platform
import sys
from typing import Dict, List

from pyfirstaid import __version__
from pyfirstaid.model import Finding, Status

SYMBOLS = {
    Status.OK: ("✔", "[ok]"),
    Status.INFO: ("i", "[i]"),
    Status.WARN: ("!", "[!]"),
    Status.ERROR: ("✘", "[x]"),
    Status.SKIP: ("-", "[-]"),
}
COLORS = {Status.OK: "32", Status.INFO: "36", Status.WARN: "33",
          Status.ERROR: "31", Status.SKIP: "90"}


def redact(text: str) -> str:
    """Hide the home directory and username so reports are safe to share."""
    if not text:
        return text
    home = os.path.expanduser("~")
    if home and home not in ("~", "/"):
        text = text.replace(home, "~")
    try:
        user = getpass.getuser()
    except Exception:  # noqa: BLE001 - getuser can fail in odd environments
        user = ""
    if user and len(user) > 2:
        text = text.replace(user, "<user>")
    return text


def environment_summary() -> Dict[str, str]:
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "executable": sys.executable,
        "prefix": sys.prefix,
        "platform": platform.platform(),
    }


def _can_encode(s: str) -> bool:
    enc = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        s.encode(enc)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


def summarize(findings: List[Finding]) -> Dict[str, int]:
    return {s.value: sum(1 for f in findings if f.status == s) for s in Status}


def render_json(findings: List[Finding], share: bool = False) -> str:
    data = {
        "tool": "pyfirstaid",
        "version": __version__,
        "environment": environment_summary(),
        "summary": summarize(findings),
        "findings": [f.to_dict() for f in findings],
    }
    text = json.dumps(data, indent=2, ensure_ascii=False)
    return redact(text) if share else text


def render_text(findings: List[Finding], color: bool = False, share: bool = False) -> str:
    unicode_ok = _can_encode("✔✘")

    def paint(status: Status, s: str) -> str:
        return "\033[%sm%s\033[0m" % (COLORS[status], s) if color else s

    env = environment_summary()
    lines = [
        "pyfirstaid %s: checking your Python environment" % __version__,
        "Python %s (%s)" % (env["python"], env["executable"]),
        "",
    ]
    for f in findings:
        sym = SYMBOLS[f.status][0 if unicode_ok else 1]
        lines.append("%s %s" % (paint(f.status, sym), f.title))
        for d in filter(None, f.detail.splitlines()):
            lines.append("    " + d)
        if f.fix:
            lines.append("    fix: " + f.fix)

    counts = summarize(findings)
    lines.append("")
    if counts["error"] == 0 and counts["warn"] == 0:
        lines.append(paint(Status.OK, "No problems found."))
    else:
        lines.append("%d problem(s), %d warning(s)." % (counts["error"], counts["warn"]))
    if not share:
        lines.append("Tip: run with --share for a privacy-safe report "
                     "you can paste into a bug report.")
    text = "\n".join(lines)
    return redact(text) if share else text
