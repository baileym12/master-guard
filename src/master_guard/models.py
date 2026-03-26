from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChangeReport:
    modified: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.modified or self.added or self.deleted)
