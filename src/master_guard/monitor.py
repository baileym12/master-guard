from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from .models import ChangeReport
from .scanner import build_diffs, build_snapshot
from .storage import append_live_event


def _print_live_notification(report: ChangeReport) -> None:
    total = len(report.modified) + len(report.added) + len(report.deleted)
    print(f"\033[1;36mchange detected\033[0m ({total} file(s))")

    for path in report.modified:
        print(f"  \033[33mM\033[0m {path}")
    for path in report.added:
        print(f"  \033[32mA\033[0m {path}")
    for path in report.deleted:
        print(f"  \033[31mD\033[0m {path}")

    for path, diff in sorted(report.diffs.items()):
        print(f"\033[1;35mdiff -- master-guard {path}\033[0m")
        if not diff:
            print("(no diff generated)")
            continue
        for line in diff.splitlines(keepends=False):
            if line.startswith('+'):
                print(f"\033[32m{line}\033[0m")
            elif line.startswith('-'):
                print(f"\033[31m{line}\033[0m")
            elif line.startswith('@'):
                print(f"\033[36m{line}\033[0m")
            else:
                print(line)


def run_monitor_loop(
    paths: list[str],
    interval_seconds: float,
    ignored_paths: list[str],
    events_file: str,
    report_writer,
) -> int:
    current_files, startup_errors = build_snapshot(paths, ignored_paths=ignored_paths)
    if startup_errors:
        for error in startup_errors:
            print(f"scan error: {error}")

    print(
        f"live monitoring started (interval: {interval_seconds:.2f}s, events: {events_file})"
    )

    while True:
        time.sleep(interval_seconds)
        next_files, errors = build_snapshot(paths, ignored_paths=ignored_paths)

        report = ChangeReport(
            modified=[],
            added=[],
            deleted=[],
            errors=errors,
        )

        previous_keys = set(current_files)
        current_keys = set(next_files)
        report.deleted = sorted(previous_keys - current_keys)
        report.added = sorted(current_keys - previous_keys)
        report.modified = sorted(
            path
            for path in (previous_keys & current_keys)
            if current_files[path]["sha256"] != next_files[path]["sha256"]
        )

        if report.has_changes:
            report.diffs = build_diffs(current_files, next_files, report)
            report.report_dir = report_writer(
                report.modified,
                report.added,
                report.deleted,
                report.errors,
                report.diffs,
            )

            _print_live_notification(report)
            print(f"live report saved to {report.report_dir}")

            append_live_event(
                events_file,
                {
                    "added": report.added,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "deleted": report.deleted,
                    "errors": report.errors,
                    "modified": report.modified,
                    "report_dir": report.report_dir,
                },
            )

        current_files = next_files


def normalize_events_file_path(events_file: str) -> str:
    return str(Path(events_file).expanduser().resolve())
