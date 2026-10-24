"""Minimal probe demo: readiness changes independently from process liveness."""

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def make_handler(flag_file: Path, live_fail_file: Path | None = None):
    class ProbeHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/live":
                status, body = (
                    (503, b"not alive\n")
                    if live_fail_file is not None and live_fail_file.exists()
                    else (200, b"alive\n")
                )
            elif self.path == "/ready":
                status, body = (503, b"not ready\n") if flag_file.exists() else (200, b"ready\n")
            else:
                status, body = 404, b"not found\n"
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    return ProbeHandler


def main():
    flag = Path(os.environ.get("UNREADY_FILE", "/state/unready"))
    live_fail = Path(os.environ.get("LIVE_FAIL_FILE", "/state/unlive"))
    port = int(os.environ.get("PORT", "8080"))
    with ThreadingHTTPServer(("0.0.0.0", port), make_handler(flag, live_fail)) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
