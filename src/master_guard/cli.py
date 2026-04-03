from __future__ import annotations

import argparse
import sys

from .scanner import build_snapshot, compare_snapshots, normalize_paths
from .storage import load_baseline, save_baseline


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

    return parser


def _print_report(prefix: str, items: list[str]) -> None:
    if not items:
        return
    print(f"{prefix} ({len(items)}):")
    for item in items:
        print(f"  - {item}")


def _run_init(paths: list[str], baseline_path: str) -> int:
    normalized_paths = [str(p) for p in normalize_paths(paths)]
    files, errors = build_snapshot(normalized_paths)
    save_baseline(baseline_path, normalized_paths, files)

    print(f"baseline saved to {baseline_path}")
    print(f"tracked files: {len(files)}")
    _print_report("scan errors", errors)
    return 0


def _run_scan(baseline_path: str) -> int:
    data = load_baseline(baseline_path)
    baseline_files = data["files"]
    paths = data["paths"]

    current_files, errors = build_snapshot(paths)
    report = compare_snapshots(baseline_files, current_files)
    report.errors.extend(errors)

    _print_report("modified files", report.modified)
    _print_report("added files", report.added)
    _print_report("deleted files", report.deleted)
    _print_report("scan errors", report.errors)

    if report.has_changes:
        print("integrity check failed: changes detected")
        return 1

    print("integrity check passed: no changes detected")
    return 0


def _run_approve(baseline_path: str, auto_yes: bool) -> int:
    data = load_baseline(baseline_path)
    paths = data["paths"]
    baseline_files = data["files"]
    current_files, errors = build_snapshot(paths)
    report = compare_snapshots(baseline_files, current_files)
    report.errors.extend(errors)

    _print_report("modified files", report.modified)
    _print_report("added files", report.added)
    _print_report("deleted files", report.deleted)
    _print_report("scan errors", report.errors)

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
