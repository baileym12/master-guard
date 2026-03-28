from __future__ import annotations

from pathlib import Path

from .hashing import sha256_file
from .models import ChangeReport


def normalize_paths(paths: list[str]) -> list[Path]:
    normalized = [Path(p).expanduser().resolve() for p in paths]
    return sorted(dict.fromkeys(normalized))


def build_snapshot(paths: list[str]) -> tuple[dict[str, str], list[str]]:
    files: dict[str, str] = {}
    errors: list[str] = []

    for root in normalize_paths(paths):
        if not root.exists():
            errors.append(f"missing path: {root}")
            continue

        if root.is_file():
            try:
                files[str(root)] = sha256_file(root)
            except (OSError, PermissionError) as exc:
                errors.append(f"{root}: {exc}")
            continue

        for file_path in sorted(p for p in root.rglob("*") if p.is_file()):
            try:
                files[str(file_path.resolve())] = sha256_file(file_path)
            except (OSError, PermissionError) as exc:
                errors.append(f"{file_path}: {exc}")

    return files, sorted(errors)


def compare_snapshots(baseline: dict[str, str], current: dict[str, str]) -> ChangeReport:
    baseline_keys = set(baseline)
    current_keys = set(current)

    deleted = sorted(baseline_keys - current_keys)
    added = sorted(current_keys - baseline_keys)

    modified = sorted(
        path for path in (baseline_keys & current_keys) if baseline[path] != current[path]
    )

    return ChangeReport(modified=modified, added=added, deleted=deleted)
