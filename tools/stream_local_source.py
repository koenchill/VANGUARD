#!/usr/bin/env python3
"""Simulate an already-integrated enterprise CDC/data source streaming Locally.

Writes live rows into the Mission BI Postgres mart stand-in so Grafana graphs
move in real time, and prints a console event stream.

Assumes: scripts/run-grafana-local.ps1 has started vanguard-grafana-pg.
Assurance: G-001 Local streaming demo — not cloud DataSync/Debezium/Kafka.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

PG_USER = os.getenv("VANGUARD_PG_USER", "vanguard")
PG_DB = os.getenv("VANGUARD_PG_DB", "mission_marts")
PG_PASSWORD = os.getenv("VANGUARD_PG_PASSWORD", "vanguard")
CONTAINER = os.getenv("VANGUARD_PG_CONTAINER", "vanguard-grafana-pg")

METRICS = [
    ("curation_health", "records_processed_per_day", 110.0, 25.0),
    ("curation_health", "pii_scrub_rate", 0.9, 0.05),
    ("curation_health", "dedup_rate", 0.12, 0.04),
    ("curation_health", "hitl_approval_throughput", 16.0, 6.0),
    ("data_quality_drift", "quality_score_trend", 0.9, 0.04),
    ("data_quality_drift", "drift_flag_rate", 0.03, 0.02),
    ("mission_agent_evaluation", "task_completion_rate", 0.85, 0.05),
    ("mission_agent_evaluation", "cost_per_inference", 0.011, 0.003),
]

_STOP = False


def _handle_sig(_signum, _frame) -> None:
    global _STOP
    _STOP = True


def _psql(sql: str) -> str:
    proc = subprocess.run(
        [
            "docker",
            "exec",
            "-e",
            f"PGPASSWORD={PG_PASSWORD}",
            CONTAINER,
            "psql",
            "-U",
            PG_USER,
            "-d",
            PG_DB,
            "-v",
            "ON_ERROR_STOP=1",
            "-t",
            "-A",
            "-c",
            sql,
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or f"psql rc={proc.returncode}")
    return proc.stdout.strip()


def ensure_stream_schema() -> None:
    _psql(
        """
        CREATE TABLE IF NOT EXISTS reporting.stream_events (
          event_id text PRIMARY KEY,
          event_time timestamptz NOT NULL DEFAULT NOW(),
          source_system text NOT NULL,
          mechanism text NOT NULL,
          batch_id text NOT NULL,
          object_key text NOT NULL,
          payload_bytes int NOT NULL,
          checksum_sha256 text NOT NULL,
          landing_status text NOT NULL,
          mission_id text NOT NULL DEFAULT 'mission-alpha'
        );
        CREATE INDEX IF NOT EXISTS stream_events_time_idx
          ON reporting.stream_events (event_time DESC);
        """
    )


def _escape(value: str) -> str:
    return value.replace("'", "''")


def emit_event(rng: random.Random, seq: int) -> dict:
    now = datetime.now(timezone.utc)
    batch_id = f"cdc-{now.strftime('%Y%m%dT%H%M%S')}-{seq:04d}"
    object_key = f"landing/raw/{batch_id}/delta-{seq}.json"
    payload = {
        "seq": seq,
        "op": rng.choice(["insert", "update", "upsert"]),
        "entity": rng.choice(["asset", "event", "telemetry"]),
        "mission_id": rng.choice(["mission-alpha", "mission-bravo"]),
        "ts": now.isoformat(),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    import hashlib

    checksum = hashlib.sha256(raw).hexdigest()
    event_id = str(uuid.uuid4())
    mechanism = rng.choice(["cdc", "incremental_datasync", "event_driven_upload"])
    source = rng.choice(
        [
            "enterprise.erp.orders",
            "enterprise.sensor.bus",
            "enterprise.identity.changes",
        ]
    )
    status = "landed"

    dash_id, metric_id, base, noise = rng.choice(METRICS)
    value = max(0.0, base + rng.uniform(-noise, noise))
    if base <= 1.5:
        value = min(1.0, value)

    sql = f"""
    INSERT INTO reporting.stream_events
      (event_id, event_time, source_system, mechanism, batch_id, object_key,
       payload_bytes, checksum_sha256, landing_status, mission_id)
    VALUES (
      '{event_id}',
      NOW(),
      '{_escape(source)}',
      '{mechanism}',
      '{batch_id}',
      '{_escape(object_key)}',
      {len(raw)},
      '{checksum}',
      '{status}',
      '{payload["mission_id"]}'
    );
    INSERT INTO reporting.metric_series
      (time, dashboard_id, metric_id, value, mission_id)
    VALUES (
      NOW(),
      '{dash_id}',
      '{metric_id}',
      {round(value, 4)},
      '{payload["mission_id"]}'
    );
    """
    _psql(sql)

    event = {
        "t": now.isoformat(),
        "event_id": event_id,
        "source": source,
        "mechanism": mechanism,
        "batch_id": batch_id,
        "object_key": object_key,
        "bytes": len(raw),
        "status": status,
        "mission_id": payload["mission_id"],
        "mart_point": {
            "dashboard_id": dash_id,
            "metric_id": metric_id,
            "value": round(value, 4),
        },
    }
    return event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=1.5, help="Seconds between events")
    parser.add_argument("--count", type=int, default=0, help="Stop after N events (0=forever)")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)

    signal.signal(signal.SIGINT, _handle_sig)
    signal.signal(signal.SIGTERM, _handle_sig)

    try:
        _psql("SELECT 1;")
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                    "hint": "Start Local stack first: .\\scripts\\run-grafana-local.ps1",
                }
            ),
            flush=True,
        )
        return 1

    ensure_stream_schema()
    rng = random.Random(args.seed)
    print(
        json.dumps(
            {
                "stream": "started",
                "mode": "Local CDC simulator (integrated source assumption)",
                "grafana": "http://127.0.0.1:33000/d/live_enterprise_stream",
                "interval_sec": args.interval,
                "assurance": "G-001 Local — not cloud Kafka/Debezium",
            }
        ),
        flush=True,
    )

    seq = 0
    while not _STOP:
        seq += 1
        event = emit_event(rng, seq)
        print(json.dumps({"stream_event": event}), flush=True)
        if args.count and seq >= args.count:
            break
        time.sleep(args.interval)

    print(json.dumps({"stream": "stopped", "events": seq}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
