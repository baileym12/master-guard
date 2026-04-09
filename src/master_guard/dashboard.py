from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def run_dashboard_server(host: str, port: int, root: str) -> int:
    root_dir = Path(root).expanduser().resolve()
    if not root_dir.exists() or not root_dir.is_dir():
        raise ValueError(f"dashboard root is not a directory: {root_dir}")

    handler = partial(SimpleHTTPRequestHandler, directory=str(root_dir))
    server = ThreadingHTTPServer((host, port), handler)

    print(f"dashboard server started at http://{host}:{port}/index.html")
    print(f"serving files from {root_dir}")
    print("press Ctrl+C to stop")

    try:
        server.serve_forever()
    finally:
        server.server_close()

    return 0
