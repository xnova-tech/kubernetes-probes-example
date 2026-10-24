"""Regression checks for independent readiness and liveness signals."""

from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from probe_app import create_app


def test_probe_bodies_and_independent_failures(tmp_path: Path) -> None:
    unready = tmp_path / "unready"
    unlive = tmp_path / "unlive"
    with TestClient(create_app(unready, unlive)) as client:
        assert_probe(client, "/ready", 200, "ready\n")
        assert_probe(client, "/live", 200, "alive\n")

        unready.touch()
        assert_probe(client, "/ready", 503, "not ready\n")
        assert_probe(client, "/live", 200, "alive\n")

        unready.unlink()
        unlive.touch()
        assert_probe(client, "/ready", 200, "ready\n")
        assert_probe(client, "/live", 503, "not alive\n")

        unlive.unlink()
        assert_probe(client, "/live", 200, "alive\n")
        assert client.get("/missing").status_code == 404


def test_environment_configures_default_paths(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    unready = tmp_path / "unready"
    unlive = tmp_path / "unlive"
    monkeypatch.setenv("UNREADY_FILE", str(unready))
    monkeypatch.setenv("LIVE_FAIL_FILE", str(unlive))

    with TestClient(create_app()) as client:
        unready.touch()
        assert_probe(client, "/ready", 503, "not ready\n")
        assert_probe(client, "/live", 200, "alive\n")
        unlive.touch()
        assert_probe(client, "/live", 503, "not alive\n")


def assert_probe(client: TestClient, path: str, status: int, body: str) -> None:
    response = client.get(path)
    assert response.status_code == status
    assert response.text == body
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
