#!/usr/bin/env python3
"""Local raw-ingest demo (G-001 portfolio) — bulk + ongoing + quarantine.

Uses in-memory object store + SQLite (no S3/DataSync). Prints a JSON summary.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from app.data_pipelines.db.models import CurationStage  # noqa: E402
from app.data_pipelines.db.session import create_db_engine, init_schema, session_factory  # noqa: E402
from app.data_pipelines.ingestion.bulk import run_bulk_onboarding  # noqa: E402
from app.data_pipelines.ingestion.ongoing import run_ongoing_sync  # noqa: E402
from app.data_pipelines.ingestion.types import (  # noqa: E402
    LANDING_PREFIX,
    QUARANTINE_PREFIX,
    ObjectManifestEntry,
    TransferBatch,
    TransferPath,
)
from app.data_pipelines.ingestion.validation import (  # noqa: E402
    InMemoryObjectStore,
    validate_landing_batch,
)


def main() -> int:
    engine = create_db_engine("sqlite+pysqlite:///:memory:")
    init_schema(engine)
    Session = session_factory(engine)
    store = InMemoryObjectStore()
    report: dict = {
        "assurance": "G-001 Local raw-ingest demo — not Cloud-Integration",
        "steps": [],
    }

    with Session() as session:
        # 1) Bulk onboarding — lands under landing/raw/
        files = {
            "a.parquet": b"raw-bulk-aaaa",
            "b.parquet": b"raw-bulk-bbbb",
        }
        batch, records = run_bulk_onboarding(
            session,
            store,
            batch_id="raw-demo-bulk-001",
            source_uri="file://demo/enterprise-source",
            source_files=files,
        )
        landing_bulk = [o.key for o in store.list_prefix(f"{LANDING_PREFIX}raw-demo-bulk-001/")]
        report["steps"].append(
            {
                "id": "bulk_onboarding",
                "ok": batch.path == TransferPath.BULK and len(records) == 2,
                "path": batch.path.value,
                "batch_id": batch.batch_id,
                "dataset_versions": [r.dataset_version for r in records],
                "stages": [r.curation_stage.value for r in records],
                "landing_keys": landing_bulk,
            }
        )

        # 2) Ongoing CDC-style sync — separate module/path
        delta = {"delta-001.json": b'{"event":"upsert","id":1}'}
        batch2, records2 = run_ongoing_sync(
            session,
            store,
            batch_id="raw-demo-cdc-001",
            source_uri="file://demo/enterprise-source",
            delta_files=delta,
            mechanism="cdc",
        )
        report["steps"].append(
            {
                "id": "ongoing_sync",
                "ok": batch2.path == TransferPath.ONGOING and len(records2) == 1,
                "path": batch2.path.value,
                "batch_id": batch2.batch_id,
                "mechanism": "cdc",
                "dataset_versions": [r.dataset_version for r in records2],
                "stages": [r.curation_stage.value for r in records2],
            }
        )

        # 3) Quarantine gate — corrupt checksum must not promote
        good = b"good-payload"
        bad = b"truncated"
        store.put_bytes(
            f"{LANDING_PREFIX}raw-demo-bad/good.parquet",
            good,
            hashlib.sha256(good).hexdigest(),
        )
        store.put_bytes(
            f"{LANDING_PREFIX}raw-demo-bad/corrupt.parquet",
            bad,
            hashlib.sha256(bad).hexdigest(),
        )
        bad_batch = TransferBatch(
            batch_id="raw-demo-bad",
            path=TransferPath.BULK,
            source_uri="file://demo/enterprise-source",
            metadata={"store": store},
        )
        source_manifest = [
            ObjectManifestEntry(
                key="good.parquet",
                size_bytes=len(good),
                checksum_sha256=hashlib.sha256(good).hexdigest(),
            ),
            ObjectManifestEntry(
                key="corrupt.parquet",
                size_bytes=len(bad) + 100,
                checksum_sha256=hashlib.sha256(b"full-original-bytes").hexdigest(),
            ),
        ]
        result = validate_landing_batch(store, bad_batch, source_manifest=source_manifest)
        report["steps"].append(
            {
                "id": "quarantine_gate",
                "ok": result.should_promote is False and bool(result.quarantined_keys),
                "should_promote": result.should_promote,
                "quarantined_keys": list(result.quarantined_keys),
                "errors": list(result.errors),
            }
        )

        report["summary"] = {
            "all_ok": all(s["ok"] for s in report["steps"]),
            "landed_stage": CurationStage.landed.value,
            "landing_prefix": LANDING_PREFIX,
            "quarantine_prefix": QUARANTINE_PREFIX,
        }

    print(json.dumps(report, indent=2))
    return 0 if report["summary"]["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
