"""Data model shared by all checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Callable, List, Optional


class Status(str, Enum):
    OK = "ok"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    SKIP = "skip"


@dataclass
class Finding:
    check: str
    status: Status
    title: str
    detail: str = ""
    fix: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class Check:
    id: str
    title: str
    run: Callable[["Options"], List[Finding]]


@dataclass
class Options:
    offline: bool = False
    timeout: float = 8.0
    cwd: Optional[str] = None
