"""Gateway responses must carry baseline security headers (DAST / ZAP)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_readyz_security_headers() -> None:
    resp = client.get("/readyz")
    assert resp.status_code == 200
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["cross-origin-resource-policy"] == "same-origin"


def test_healthz_and_openapi_security_headers() -> None:
    for path in ("/healthz", "/openapi.json"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert resp.headers["cross-origin-resource-policy"] == "same-origin"
