from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from .hashing import sha256_file
from .models import ChangeReport

MAX_TEXT_SNAPSHOT_BYTES = 256 * 1024


def normalize_paths(paths: list[str]) -> list[Path]:
    normalized = [Path(p).expanduser().resolve() for p in paths]
    return sorted(dict.fromkeys(normalized))


def _build_file_state(path: Path) -> dict[str, Any]:
    state: dict[str, Any] = {"sha256": sha256_file(path), "text": None}

    try:
        if path.stat().st_size > MAX_TEXT_SNAPSHOT_BYTES:
            return state
    except (OSError, PermissionError):
        return state

    try:
        payload = path.read_bytes()
    except (OSError, PermissionError):
        return state

    if b"\x00" in payload:
        return state

    try:
        state["text"] = payload.decode("utf-8")
    except UnicodeDecodeError:
        return state

    return state


def _entry_sha256(entry: str | dict[str, Any]) -> str:
    if isinstance(entry, str):
        return entry
    digest = entry.get("sha256")
    if not isinstance(digest, str):
        raise ValueError("baseline file entry is malformed: missing sha256")
    return digest


def _entry_text(entry: str | dict[str, Any]) -> str | None:
    if isinstance(entry, str):
        return None
    text = entry.get("text")
    if text is None:
        return None
    if not isinstance(text, str):
        return None
    return text


def build_snapshot(
    paths: list[str],
    ignored_paths: list[str] | None = None,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    files: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    ignored = {
        str(Path(p).expanduser().resolve()) for p in (ignored_paths or [])
    }

    def is_ignored(candidate: str) -> bool:
        for ignored_path in ignored:
            if candidate == ignored_path or candidate.startswith(f"{ignored_path}/"):
                return True
        return False

    for root in normalize_paths(paths):
        if not root.exists():
            errors.append(f"missing path: {root}")
            continue

        if root.is_file():
            try:
                if is_ignored(str(root)):
                    continue
                files[str(root)] = _build_file_state(root)
            except (OSError, PermissionError) as exc:
                errors.append(f"{root}: {exc}")
            continue

        for file_path in sorted(p for p in root.rglob("*") if p.is_file()):
            try:
                resolved = str(file_path.resolve())
                if is_ignored(resolved):
                    continue
                files[resolved] = _build_file_state(file_path)
            except (OSError, PermissionError) as exc:
                errors.append(f"{file_path}: {exc}")

    return files, sorted(errors)


def compare_snapshots(
    baseline: dict[str, str | dict[str, Any]],
    current: dict[str, str | dict[str, Any]],
) -> ChangeReport:
    baseline_keys = set(baseline)
    current_keys = set(current)

    deleted = sorted(baseline_keys - current_keys)
    added = sorted(current_keys - baseline_keys)

    modified = sorted(
        path
        for path in (baseline_keys & current_keys)
        if _entry_sha256(baseline[path]) != _entry_sha256(current[path])
    )

    return ChangeReport(modified=modified, added=added, deleted=deleted)


def build_diffs(
    baseline: dict[str, str | dict[str, Any]],
    current: dict[str, str | dict[str, Any]],
    report: ChangeReport,
) -> dict[str, str]:
    diffs: dict[str, str] = {}

    for path in report.modified:
        before = _entry_text(baseline[path])
        after = _entry_text(current[path])
        if before is None or after is None:
            diffs[path] = "(no text diff available: file is binary, too large, or non-UTF-8)\n"
            continue

        lines = difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
        diffs[path] = "".join(lines)

    for path in report.added:
        after = _entry_text(current[path])
        if after is None:
            diffs[path] = "(no text diff available for added file: file is binary, too large, or non-UTF-8)\n"
            continue

        lines = difflib.unified_diff(
            [],
            after.splitlines(keepends=True),
            fromfile="/dev/null",
            tofile=f"b/{path}",
        )
        diffs[path] = "".join(lines)

    for path in report.deleted:
        before = _entry_text(baseline[path])
        if before is None:
            diffs[path] = "(no text diff available for deleted file: file is binary, too large, or non-UTF-8)\n"
            continue

        lines = difflib.unified_diff(
            before.splitlines(keepends=True),
            [],
            fromfile=f"a/{path}",
            tofile="/dev/null",
        )
        diffs[path] = "".join(lines)

    return diffs
