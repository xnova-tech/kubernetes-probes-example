"""Two independent HTTP probes for the Kubernetes example."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse


def create_app(unready_file: Path | None = None, unlive_file: Path | None = None) -> FastAPI:
    """Build an app whose probe state is controlled by two separate files."""
    unready_file = unready_file or Path(os.getenv("UNREADY_FILE", "/state/unready"))
    unlive_file = unlive_file or Path(os.getenv("LIVE_FAIL_FILE", "/state/unlive"))
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/ready", response_class=PlainTextResponse)
    def ready() -> PlainTextResponse:
        if unready_file.exists():
            return PlainTextResponse("not ready\n", status_code=503)
        return PlainTextResponse("ready\n")

    @app.get("/live", response_class=PlainTextResponse)
    def live() -> PlainTextResponse:
        if unlive_file.exists():
            return PlainTextResponse("not alive\n", status_code=503)
        return PlainTextResponse("alive\n")

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")), access_log=False)


if __name__ == "__main__":
    main()
