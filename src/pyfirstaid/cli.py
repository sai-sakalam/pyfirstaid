"""Command-line entry point: `python -m pyfirstaid` or `pyfirstaid`."""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from typing import List, Optional

from pyfirstaid import __version__
from pyfirstaid.checks import ALL_CHECKS
from pyfirstaid.model import Check, Finding, Options, Status
from pyfirstaid.report import render_json, render_text

EXIT_OK, EXIT_PROBLEMS, EXIT_INTERNAL = 0, 1, 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pyfirstaid",
        description="First aid for broken Python environments: "
                    "finds what's wrong and tells you how to fix it.",
    )
    p.add_argument("--json", action="store_true", help="output machine-readable JSON")
    p.add_argument("--share", action="store_true",
                   help="hide your username and home folder so the report is safe to share")
    p.add_argument("--offline", action="store_true", help="skip checks that need the internet")
    p.add_argument("--strict", action="store_true", help="exit with code 1 on warnings too")
    p.add_argument("--only", metavar="IDS", help="comma-separated check ids to run")
    p.add_argument("--skip", metavar="IDS", help="comma-separated check ids to skip")
    p.add_argument("--list", action="store_true", help="list available checks and exit")
    p.add_argument("--no-color", action="store_true", help="disable colored output")
    p.add_argument("--version", action="version", version="pyfirstaid " + __version__)
    return p


def select_checks(only: Optional[str], skip: Optional[str]) -> List[Check]:
    checks = list(ALL_CHECKS)
    if only:
        wanted = {s.strip() for s in only.split(",") if s.strip()}
        checks = [c for c in checks if c.id in wanted]
    if skip:
        unwanted = {s.strip() for s in skip.split(",") if s.strip()}
        checks = [c for c in checks if c.id not in unwanted]
    return checks


def run_checks(checks: List[Check], opts: Options) -> List[Finding]:
    findings: List[Finding] = []
    for check in checks:
        try:
            findings.extend(check.run(opts))
        except Exception as exc:  # noqa: BLE001 - a broken check must never crash the tool
            findings.append(Finding(
                check.id, Status.SKIP, "%s: check could not run" % check.title,
                detail="%s: %s" % (type(exc).__name__, exc),
                fix="Please report this at https://github.com/sai-sakalam/pyfirstaid/issues",
            ))
    return findings


def use_color(no_color: bool) -> bool:
    if no_color or os.environ.get("NO_COLOR"):
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty() and os.name != "nt" \
        or bool(os.environ.get("WT_SESSION"))  # Windows Terminal supports ANSI


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list:
        for c in ALL_CHECKS:
            print("%-16s %s" % (c.id, c.title))
        return EXIT_OK

    try:
        findings = run_checks(select_checks(args.only, args.skip), Options(offline=args.offline))
        if args.json:
            print(render_json(findings, share=args.share))
        else:
            print(render_text(findings, color=use_color(args.no_color), share=args.share))
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return EXIT_INTERNAL

    if any(f.status == Status.ERROR for f in findings):
        return EXIT_PROBLEMS
    if args.strict and any(f.status == Status.WARN for f in findings):
        return EXIT_PROBLEMS
    return EXIT_OK


def _run() -> None:
    """Entry point for the single-file pyfirstaid.pyz."""
    sys.exit(main())
