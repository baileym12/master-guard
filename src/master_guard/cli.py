from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from .dashboard import run_dashboard_server
from .monitor import normalize_events_file_path, run_monitor_loop
from .scanner import build_diffs, build_snapshot, compare_snapshots, normalize_paths
from .storage import (
    append_live_event,
    load_baseline,
    reports_root_for_baseline,
    save_baseline,
    write_scan_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="master-guard",
        description="Simple file integrity monitoring tool",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create baseline")
    init_parser.add_argument("--paths", nargs="+", required=True)
    init_parser.add_argument("--baseline", default="baseline.json")

    scan_parser = subparsers.add_parser("scan", help="Scan against baseline")
    scan_parser.add_argument("--baseline", default="baseline.json")

    approve_parser = subparsers.add_parser("approve", help="Approve and refresh baseline")
    approve_parser.add_argument("--baseline", default="baseline.json")
    approve_parser.add_argument("--yes", action="store_true", help="Approve without prompt")

    monitor_parser = subparsers.add_parser("monitor", help="Live monitoring loop")
    monitor_parser.add_argument("--baseline", default="baseline.json")
    monitor_parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Polling interval in seconds (default: 2.0)",
    )
    monitor_parser.add_argument(
        "--events-file",
        default="live-events.jsonl",
        help="Path to live event log file (default: live-events.jsonl)",
    )

    dashboard_parser = subparsers.add_parser("dashboard", help="Launch web dashboard")
    dashboard_parser.add_argument("--host", default="127.0.0.1")
    dashboard_parser.add_argument("--port", type=int, default=8080)
    dashboard_parser.add_argument(
        "--root",
        default=".",
        help="Directory to serve (default: current directory)",
    )

    return parser


def _print_report(prefix: str, items: list[str]) -> None:
    if not items:
        return
    print(f"{prefix} ({len(items)}):")
    for item in items:
        print(f"  - {item}")


def _print_diffs(diffs: dict[str, str]) -> None:
    for path, diff in sorted(diffs.items()):
        print(f"diff -- master-guard {path}")
        print(diff if diff else "(no diff generated)")


def _ignored_paths_for_baseline(baseline_path: str) -> list[str]:
    baseline_abs = str(Path(baseline_path).expanduser().resolve())
    reports_root = str(reports_root_for_baseline(baseline_path))
    return [baseline_abs, reports_root]


def _run_init(paths: list[str], baseline_path: str) -> int:
    normalized_paths = [str(p) for p in normalize_paths(paths)]
    files, errors = build_snapshot(
        normalized_paths,
        ignored_paths=_ignored_paths_for_baseline(baseline_path),
    )
    save_baseline(baseline_path, normalized_paths, files)

    print(f"baseline saved to {baseline_path}")
    print(f"tracked files: {len(files)}")
    _print_report("scan errors", errors)
    return 0


def _run_scan(baseline_path: str) -> int:
    data = load_baseline(baseline_path)
    baseline_files = data["files"]
    paths = data["paths"]

    current_files, errors = build_snapshot(
        paths,
        ignored_paths=_ignored_paths_for_baseline(baseline_path),
    )
    report = compare_snapshots(baseline_files, current_files)
    report.errors.extend(errors)
    report.diffs = build_diffs(baseline_files, current_files, report)

    if report.has_changes or report.errors:
        report.report_dir = write_scan_report(
            baseline_path,
            report.modified,
            report.added,
            report.deleted,
            report.errors,
            report.diffs,
        )

    _print_report("modified files", report.modified)
    _print_report("added files", report.added)
    _print_report("deleted files", report.deleted)
    _print_report("scan errors", report.errors)
    if report.has_changes:
        _print_diffs(report.diffs)
    if report.report_dir:
        print(f"scan report saved to {report.report_dir}")

    if report.has_changes:
        print("integrity check failed: changes detected")
        return 1

    print("integrity check passed: no changes detected")
    return 0


def _run_approve(baseline_path: str, auto_yes: bool) -> int:
    data = load_baseline(baseline_path)
    paths = data["paths"]
    baseline_files = data["files"]
    current_files, errors = build_snapshot(
        paths,
        ignored_paths=_ignored_paths_for_baseline(baseline_path),
    )
    report = compare_snapshots(baseline_files, current_files)
    report.errors.extend(errors)
    report.diffs = build_diffs(baseline_files, current_files, report)

    _print_report("modified files", report.modified)
    _print_report("added files", report.added)
    _print_report("deleted files", report.deleted)
    _print_report("scan errors", report.errors)
    if report.has_changes:
        _print_diffs(report.diffs)

    if not report.has_changes and not report.errors:
        print("no changes to approve")
        return 0

    if not auto_yes:
        answer = input("approve these changes and update baseline? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            print("approval cancelled")
            return 1

    save_baseline(baseline_path, paths, current_files)
    print(f"baseline updated at {baseline_path}")
    return 0


def _run_monitor(baseline_path: str, interval_seconds: float, events_file: str) -> int:
    if interval_seconds <= 0:
        raise ValueError("interval must be greater than 0")

    data = load_baseline(baseline_path)
    paths = data["paths"]
    event_log_path = normalize_events_file_path(events_file)
    ignored_paths = _ignored_paths_for_baseline(baseline_path) + [event_log_path]

    append_live_event(
        event_log_path,
        {
            "event": "monitor_started",
            "baseline": Path(baseline_path).expanduser().resolve().as_posix(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "paths": paths,
        },
    )

    return run_monitor_loop(
        paths=paths,
        interval_seconds=interval_seconds,
        ignored_paths=ignored_paths,
        events_file=event_log_path,
        report_writer=lambda modified, added, deleted, errors, diffs: write_scan_report(
            baseline_path,
            modified,
            added,
            deleted,
            errors,
            diffs,
        ),
    )


def _run_dashboard(host: str, port: int, root: str) -> int:
    if port <= 0 or port > 65535:
        raise ValueError("port must be between 1 and 65535")
    return run_dashboard_server(host=host, port=port, root=root)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "init":
            return _run_init(args.paths, args.baseline)
        if args.command == "scan":
            return _run_scan(args.baseline)
        if args.command == "approve":
            return _run_approve(args.baseline, args.yes)
        if args.command == "monitor":
            return _run_monitor(args.baseline, args.interval, args.events_file)
        if args.command == "dashboard":
            return _run_dashboard(args.host, args.port, args.root)
        parser.error(f"unknown command: {args.command}")
    except FileNotFoundError:
        print(f"baseline not found: {args.baseline}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130

    return 2


if __name__ == "__main__":
    sys.exit(main())
