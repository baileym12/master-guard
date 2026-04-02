from __future__ import annotations

import argparse
import sys


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


def main() -> int:
    parser = build_parser()
    _ = parser.parse_args()
    print("cli parser ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
