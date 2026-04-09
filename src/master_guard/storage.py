from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASELINE_VERSION = 2
REPORTS_DIRNAME = "master-guard-reports"


def reports_root_for_baseline(baseline_path: str) -> Path:
    return Path(baseline_path).expanduser().resolve().parent / REPORTS_DIRNAME


def save_baseline(path: str, scanned_paths: list[str], files: dict[str, dict[str, Any]]) -> None:
    baseline = {
        "version": BASELINE_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "paths": scanned_paths,
        "files": files,
    }
    baseline_path = Path(path)
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n")


def load_baseline(path: str) -> dict:
    baseline_path = Path(path)
    data = json.loads(baseline_path.read_text())

    version = data.get("version")
    if version == 1:
        files = data.get("files")
        paths = data.get("paths")
        if not isinstance(files, dict) or not isinstance(paths, list):
            raise ValueError("baseline is malformed")

        # v1 stored path -> hash. We up-convert at runtime for compatibility.
        upgraded_files = {
            file_path: {"sha256": digest, "text": None}
            for file_path, digest in files.items()
            if isinstance(digest, str)
        }
        if len(upgraded_files) != len(files):
            raise ValueError("baseline is malformed")

        data["version"] = BASELINE_VERSION
        data["files"] = upgraded_files
        return data

    if version != BASELINE_VERSION:
        raise ValueError(
            f"unsupported baseline version: {version} (expected {BASELINE_VERSION})"
        )

    files = data.get("files")
    paths = data.get("paths")
    if not isinstance(files, dict) or not isinstance(paths, list):
        raise ValueError("baseline is malformed")

    for file_path, entry in files.items():
        if not isinstance(file_path, str):
            raise ValueError("baseline is malformed")
        if not isinstance(entry, dict):
            raise ValueError("baseline is malformed")
        digest = entry.get("sha256")
        text = entry.get("text")
        if not isinstance(digest, str):
            raise ValueError("baseline is malformed")
        if text is not None and not isinstance(text, str):
            raise ValueError("baseline is malformed")

    return data


def write_scan_report(
    baseline_path: str,
    modified: list[str],
    added: list[str],
    deleted: list[str],
    errors: list[str],
    diffs: dict[str, str],
) -> str:
    now = datetime.now(timezone.utc)
    base_report_dir = reports_root_for_baseline(baseline_path)
    timestamp = now.strftime("%Y%m%dT%H%M%SZ")
    report_dir = base_report_dir / timestamp
    suffix = 1
    while report_dir.exists():
        report_dir = base_report_dir / f"{timestamp}-{suffix}"
        suffix += 1

    diff_dir = report_dir / "diffs"
    diff_dir.mkdir(parents=True, exist_ok=False)

    written_diffs: dict[str, str] = {}
    combined_chunks: list[str] = []

    for path, diff_text in sorted(diffs.items()):
        slug = hashlib.sha1(path.encode("utf-8")).hexdigest()[:12]
        filename = f"{Path(path).name or 'file'}-{slug}.diff"
        target = diff_dir / filename
        target.write_text(diff_text)
        written_diffs[path] = str(target)

        if diff_text:
            combined_chunks.append(diff_text)
            if not diff_text.endswith("\n"):
                combined_chunks.append("\n")

    if combined_chunks:
        (report_dir / "combined.patch").write_text("".join(combined_chunks))

    summary = {
        "created_at": now.isoformat(),
        "modified": modified,
        "added": added,
        "deleted": deleted,
        "errors": errors,
        "diff_files": written_diffs,
    }
    (report_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )

    return str(report_dir)


def append_live_event(path: str, event: dict[str, Any]) -> None:
    event_path = Path(path).expanduser().resolve()
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
