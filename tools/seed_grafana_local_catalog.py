#!/usr/bin/env python3
"""Seed Local Grafana catalog pages with real Mission BI content.

Populates Playlists, Library panels, Snapshots, and Public dashboards so the
Grafana empty-state pages show portfolio (G-001 Local) evidence instead of
placeholder illustrations.

Requires: scripts/run-grafana-local.ps1 already up.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

DEFAULT_BASE = "http://127.0.0.1:33000"
DEFAULT_USER = "admin"
DEFAULT_PASS = "vanguard"

DASHBOARDS = [
    ("curation_health", "Curation Pipeline Health (Local)"),
    ("data_quality_drift", "Data Quality & Drift (Local)"),
    ("live_enterprise_stream", "Live Enterprise Stream (Local)"),
    ("mission_agent_evaluation", "Mission Agent Evaluation (Local)"),
    ("security_compliance", "Security & Compliance (Local)"),
]


class GrafanaClient:
    def __init__(self, base: str, user: str, password: str) -> None:
        self.base = base.rstrip("/")
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        ok: tuple[int, ...] = (200, 201),
    ) -> Any:
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base}{path}",
            data=data,
            headers=self._headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code in ok:
                return json.loads(detail) if detail else None
            raise RuntimeError(f"{method} {path} -> {exc.code}: {detail}") from exc

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def post(self, path: str, body: dict[str, Any], ok: tuple[int, ...] = (200, 201)) -> Any:
        return self.request("POST", path, body, ok=ok)

    def put(self, path: str, body: dict[str, Any], ok: tuple[int, ...] = (200, 201)) -> Any:
        return self.request("PUT", path, body, ok=ok)

    def delete(self, path: str, ok: tuple[int, ...] = (200, 204)) -> Any:
        return self.request("DELETE", path, ok=ok)


def _wait_ready(client: GrafanaClient) -> None:
    client.get("/api/health")


def seed_playlist(client: GrafanaClient) -> dict[str, Any]:
    name = "Mission BI — Local Freeze Rotation"
    existing = client.get("/api/playlists") or []
    for item in existing:
        if item.get("name") == name:
            client.delete(f"/api/playlists/{item['uid']}", ok=(200, 204, 404))

    items = []
    for i, (uid, title) in enumerate(DASHBOARDS):
        items.append(
            {
                "type": "dashboard_by_uid",
                "value": uid,
                "order": i + 1,
                "title": title,
            }
        )

    payload = {
        "name": name,
        "interval": "1m",
        "items": items,
    }
    created = client.post("/api/playlists", payload)
    return {
        "name": name,
        "uid": created.get("uid") if isinstance(created, dict) else None,
        "dashboards": len(items),
        "interval": "1m",
    }


def _stat_panel(title: str, sql: str, panel_id: int = 1) -> dict[str, Any]:
    return {
        "id": panel_id,
        "type": "stat",
        "title": title,
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "datasource": {"type": "postgres", "uid": "MissionBI-Local"},
        "targets": [
            {
                "refId": "A",
                "datasource": {"type": "postgres", "uid": "MissionBI-Local"},
                "format": "table",
                "rawQuery": True,
                "rawSql": sql,
            }
        ],
        "options": {
            "reduceOptions": {"values": False, "calcs": ["lastNotNull"], "fields": ""},
            "orientation": "auto",
            "textMode": "value_and_name",
            "colorMode": "value",
            "graphMode": "area",
            "justifyMode": "auto",
        },
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "red", "value": None},
                        {"color": "green", "value": 0},
                    ],
                },
            }
        },
    }


LIBRARY_SPECS = [
    {
        "uid": "lib-mart-curation-throughput",
        "name": "Mart: curation throughput",
        "description": "Latest records_processed_per_day from reporting.fct_curation_health",
        "folder_uid": "mission-bi",
        "model": _stat_panel(
            "Mart: curation throughput",
            "SELECT value FROM reporting.fct_curation_health "
            "WHERE metric_id = 'records_processed_per_day' ORDER BY time DESC LIMIT 1",
        ),
    },
    {
        "uid": "lib-mart-quality-score",
        "name": "Mart: latest quality score",
        "description": "Latest quality_score_trend from reporting.fct_data_quality",
        "folder_uid": "mission-bi",
        "model": _stat_panel(
            "Mart: latest quality score",
            "SELECT value FROM reporting.fct_data_quality "
            "WHERE metric_id = 'quality_score_trend' ORDER BY time DESC LIMIT 1",
        ),
    },
    {
        "uid": "lib-mart-stream-landed",
        "name": "Mart: stream events landed (15m)",
        "description": "Count of Local CDC landing events in the last 15 minutes",
        "folder_uid": "mission-bi",
        "model": _stat_panel(
            "Mart: stream events landed (15m)",
            "SELECT COUNT(*)::double precision AS value FROM reporting.stream_events "
            "WHERE event_time > NOW() - INTERVAL '15 minutes'",
        ),
    },
]


def seed_library_panels(client: GrafanaClient) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    search = client.get("/api/library-elements?perPage=100") or {}
    elements = search.get("elements") or search.get("result") or []
    if isinstance(search, list):
        elements = search

    by_uid = {e.get("uid"): e for e in elements if isinstance(e, dict)}

    for spec in LIBRARY_SPECS:
        uid = spec["uid"]
        body = {
            "uid": uid,
            "kind": 1,
            "name": spec["name"],
            "model": spec["model"],
            "folderUid": spec["folder_uid"],
            "description": spec["description"],
            "type": "stat",
        }
        existing = by_uid.get(uid)
        if existing:
            version = existing.get("version", 1)
            client.request(
                "PATCH",
                f"/api/library-elements/{uid}",
                {**body, "version": version},
                ok=(200, 201),
            )
            out.append({"uid": uid, "name": spec["name"], "action": "updated"})
        else:
            # Prefer create; if conflict, patch.
            try:
                client.post("/api/library-elements", body)
                out.append({"uid": uid, "name": spec["name"], "action": "created"})
            except RuntimeError as exc:
                if "409" in str(exc) or "already exists" in str(exc).lower():
                    detail = client.get(f"/api/library-elements/{uid}")
                    version = (detail or {}).get("version", 1)
                    if isinstance(detail, dict) and "result" in detail:
                        version = detail["result"].get("version", 1)
                    client.request(
                        "PATCH",
                        f"/api/library-elements/{uid}",
                        {**body, "version": version},
                        ok=(200, 201),
                    )
                    out.append({"uid": uid, "name": spec["name"], "action": "updated"})
                else:
                    raise
    return out


def seed_snapshots(client: GrafanaClient) -> list[dict[str, Any]]:
    """Create external snapshots for key Local dashboards (shareable Local URLs)."""
    # Delete prior VANGUARD-named snapshots to keep the list clean.
    existing = client.get("/api/dashboard/snapshots") or []
    for snap in existing:
        name = snap.get("name") or ""
        if name.startswith("VANGUARD Local —"):
            key = snap.get("key")
            if key:
                client.delete(f"/api/snapshots/{key}", ok=(200, 204, 404))

    created: list[dict[str, Any]] = []
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    for uid, title in DASHBOARDS[:3]:
        dash = client.get(f"/api/dashboards/uid/{uid}")
        dashboard = dash["dashboard"]
        snapshot_name = f"VANGUARD Local — {title}"
        payload = {
            "dashboard": dashboard,
            "name": snapshot_name,
            "expires": 0,
            "external": False,
            "key": f"vanguard-local-{uid}",
        }
        # key may conflict; delete first
        client.delete(f"/api/snapshots/vanguard-local-{uid}", ok=(200, 204, 404))
        result = client.post("/api/snapshots", payload)
        created.append(
            {
                "name": snapshot_name,
                "key": result.get("key"),
                "url": result.get("url"),
                "dashboard_uid": uid,
                "captured_at": stamp,
            }
        )
    return created


def seed_public_dashboards(client: GrafanaClient) -> list[dict[str, Any]]:
    """Enable public dashboard shares for selected Local Mission BI boards."""
    targets = [
        ("curation_health", "Mission BI — Curation Health (public Local)"),
        ("data_quality_drift", "Mission BI — Data Quality (public Local)"),
        ("live_enterprise_stream", "Mission BI — Live Stream (public Local)"),
    ]
    out: list[dict[str, Any]] = []
    for uid, _label in targets:
        # Remove existing public config if present
        try:
            existing = client.get(f"/api/dashboards/uid/{uid}/public-dashboards")
            pub_uid = None
            if isinstance(existing, dict):
                pub_uid = existing.get("uid") or (existing.get("publicDashboard") or {}).get("uid")
            if pub_uid:
                client.delete(
                    f"/api/dashboards/uid/{uid}/public-dashboards/{pub_uid}",
                    ok=(200, 204, 404),
                )
        except RuntimeError as exc:
            if "404" not in str(exc):
                raise

        body = {
            "isEnabled": True,
            "annotationsEnabled": False,
            "timeSelectionEnabled": True,
            "share": "public",
        }
        try:
            result = client.post(f"/api/dashboards/uid/{uid}/public-dashboards", body)
        except RuntimeError as exc:
            # Older/newer API shape variants
            if "404" in str(exc):
                out.append({"dashboard_uid": uid, "status": "unsupported", "detail": str(exc)})
                continue
            raise
        access = result.get("accessToken") or result.get("uid")
        out.append(
            {
                "dashboard_uid": uid,
                "title": next(t for u, t in DASHBOARDS if u == uid),
                "public_uid": result.get("uid"),
                "access_token": access,
                "is_enabled": True,
                "url": f"{client.base}/public-dashboards/{access}" if access else None,
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--user", default=DEFAULT_USER)
    parser.add_argument("--password", default=DEFAULT_PASS)
    args = parser.parse_args(argv)

    client = GrafanaClient(args.base_url, args.user, args.password)
    try:
        _wait_ready(client)
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                    "hint": "Start Local Grafana first: .\\scripts\\run-grafana-local.ps1",
                }
            ),
            flush=True,
        )
        return 1

    report: dict[str, Any] = {
        "ok": True,
        "assurance": "G-001 Local Grafana catalog seed — not Cloud-Integration / not ATO",
        "base_url": args.base_url,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "playlist": None,
        "library_panels": [],
        "snapshots": [],
        "public_dashboards": [],
        "pages": {
            "playlists": f"{args.base_url}/playlists",
            "library_panels": f"{args.base_url}/library-panels",
            "snapshots": f"{args.base_url}/dashboard/snapshots",
            "public_dashboards": f"{args.base_url}/dashboard/public-dashboards",
        },
    }

    errors: list[str] = []
    try:
        report["playlist"] = seed_playlist(client)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"playlist: {exc}")

    try:
        report["library_panels"] = seed_library_panels(client)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"library_panels: {exc}")

    try:
        report["snapshots"] = seed_snapshots(client)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"snapshots: {exc}")

    try:
        report["public_dashboards"] = seed_public_dashboards(client)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"public_dashboards: {exc}")

    if errors:
        report["ok"] = False
        report["errors"] = errors

    print(json.dumps(report, indent=2), flush=True)
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
