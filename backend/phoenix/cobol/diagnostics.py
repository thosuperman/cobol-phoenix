from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(slots=True)
class Diagnostic:
    severity: Severity
    code: str
    message: str
    file: str
    line: int

    def to_dict(self) -> dict:
        return {
            "severity": str(self.severity),
            "code": self.code,
            "message": self.message,
            "file": self.file,
            "line": self.line,
        }
