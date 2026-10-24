"""Offline local HTTP contract check; no Kubernetes behavior asserted."""

import tempfile
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import urlopen

import importlib.util

source = Path(__file__).resolve().with_name("probe_app.py")
spec = importlib.util.spec_from_file_location("probe_app", source)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)
make_handler = app.make_handler
from http.server import ThreadingHTTPServer


def status(port: int, path: str) -> int:
    try:
        with urlopen(f"http://127.0.0.1:{port}{path}", timeout=2) as response:
            return response.status
    except HTTPError as exc:
        return exc.code


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        flag = Path(tmp) / "unready"
        live_fail = Path(tmp) / "unlive"
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(flag, live_fail))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_port
            initial = (status(port, "/live"), status(port, "/ready"))
            flag.touch()
            during = (status(port, "/live"), status(port, "/ready"))
            flag.unlink()
            restored = (status(port, "/live"), status(port, "/ready"))
            live_fail.touch()
            liveness_failure = (status(port, "/live"), status(port, "/ready"))
            live_fail.unlink()
            live_restored = (status(port, "/live"), status(port, "/ready"))
            missing = status(port, "/missing")
            assert initial == (200, 200), initial
            assert during == (200, 503), during
            assert restored == (200, 200), restored
            assert liveness_failure == (503, 200), liveness_failure
            assert live_restored == (200, 200), live_restored
            assert missing == 404, missing
            print("initial: live=200 ready=200")
            print("unready: live=200 ready=503")
            print("restored: live=200 ready=200")
            print("liveness failure: live=503 ready=200")
            print("liveness restored: live=200 ready=200")
            print("unknown: status=404")
        finally:
            server.shutdown()
            thread.join(timeout=3)
            server.server_close()


if __name__ == "__main__":
    main()
