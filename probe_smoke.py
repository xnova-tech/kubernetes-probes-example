"""Check the HTTP responses without starting a server or Kubernetes."""

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from probe_app import create_app


def check(client: TestClient, label: str, live: int, ready: int) -> None:
    actual = (client.get("/live").status_code, client.get("/ready").status_code)
    expected = (live, ready)
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected}, got {actual}")
    print(f"{label}: live={live} ready={ready}")


def main() -> None:
    with TemporaryDirectory() as directory:
        unready = Path(directory) / "unready"
        unlive = Path(directory) / "unlive"
        with TestClient(create_app(unready, unlive)) as client:
            check(client, "initial", 200, 200)
            unready.touch()
            check(client, "unready", 200, 503)
            unready.unlink()
            check(client, "restored", 200, 200)
            unlive.touch()
            check(client, "liveness failure", 503, 200)
            unlive.unlink()
            check(client, "liveness restored", 200, 200)
            missing = client.get("/missing")
            if missing.status_code != 404:
                raise AssertionError(f"unknown route: expected 404, got {missing.status_code}")
            print("unknown: status=404")


if __name__ == "__main__":
    main()
