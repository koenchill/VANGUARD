"""Minimal FastAPI entrypoint for gateway/inference image smoke tests."""

from __future__ import annotations

import os

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

app = FastAPI(title="VANGUARD API", version="0.1.0")


@app.middleware("http")
async def security_headers(request: Request, call_next) -> Response:
    """Baseline headers required by disposable DAST (ZAP) against the gateway."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    return response


@app.get("/readyz")
def readyz() -> dict[str, str]:
    return {"status": "ok", "workload": os.getenv("VANGUARD_WORKLOAD", "api")}


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    main()
