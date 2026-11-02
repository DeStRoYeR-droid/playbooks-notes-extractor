"""Preview the site exactly as GitHub Pages will serve it.

    python3 scripts/serve.py [--port 8000]

Serves ./site under /playbooks-notes/ (the project-page path), redirects / there,
and answers missing paths with site/404.html and status 404, like GitHub Pages.
Standard library only.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import io
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
BASE = "/playbooks-notes"


class PagesHandler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".webmanifest": "application/manifest+json",
        ".woff2": "font/woff2",
        ".svg": "image/svg+xml",
        ".md": "text/markdown",
    }

    def send_head(self):  # noqa: D401 - stdlib hook
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        if path in ("", "/"):
            self.send_response(302)
            self.send_header("Location", f"{BASE}/")
            self.end_headers()
            return None
        if path == BASE:
            self.send_response(301)
            self.send_header("Location", f"{BASE}/")
            self.end_headers()
            return None
        if not path.startswith(f"{BASE}/"):
            return self._not_found()
        self.path = self.path[len(BASE):] or "/"
        target = Path(self.translate_path(self.path))
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            return self._not_found()
        return super().send_head()

    def _not_found(self):
        body = (SITE / "404.html").read_bytes()
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        return io.BytesIO(body)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")  # revalidate each time; keeps back/forward cache working
        super().end_headers()

    def log_message(self, fmt, *args):  # keep test output quiet
        pass


def make_server(port: int = 8000, host: str = "127.0.0.1") -> http.server.ThreadingHTTPServer:
    handler = functools.partial(PagesHandler, directory=str(SITE))
    return http.server.ThreadingHTTPServer((host, port), handler)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = make_server(args.port)
    print(f"Serving {SITE} at http://127.0.0.1:{args.port}{BASE}/  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
