from __future__ import annotations

import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class DashboardHTTPRequestHandler(SimpleHTTPRequestHandler):
    events_file: str = "live-events.jsonl"

    def translate_path(self, path: str) -> str:
        # Strip query parameters and fragments before checking
        clean_path = path.split('?', 1)[0].split('#', 1)[0]
        if clean_path == "/live-events.jsonl":
            return str(Path(self.events_file).expanduser().resolve())
        return super().translate_path(path)


def run_dashboard_server(host: str, port: int, root: str, events_file: str = "live-events.jsonl") -> int:
    root_dir = Path(root).expanduser().resolve()
    if not root_dir.exists() or not root_dir.is_dir():
        raise ValueError(f"dashboard root is not a directory: {root_dir}")

    class Handler(DashboardHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            self.events_file = events_file
            super().__init__(*args, directory=str(root_dir), **kwargs)

    server = ThreadingHTTPServer((host, port), Handler)

    print(f"dashboard server started at http://{host}:{port}/index.html")
    print(f"serving files from {root_dir} and events from {events_file}")
    print("press Ctrl+C to stop")

    try:
        server.serve_forever()
    finally:
        server.server_close()

    return 0
