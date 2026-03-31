from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASELINE_VERSION = 1


def save_baseline(path: str, scanned_paths: list[str], files: dict[str, str]) -> None:
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

    if data.get("version") != BASELINE_VERSION:
        raise ValueError(
            f"unsupported baseline version: {data.get('version')} (expected {BASELINE_VERSION})"
        )

    files = data.get("files")
    paths = data.get("paths")
    if not isinstance(files, dict) or not isinstance(paths, list):
        raise ValueError("baseline is malformed")

    return data
