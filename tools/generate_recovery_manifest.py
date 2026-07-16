"""CLI — generate a signed daily/weekly recovery-set manifest into backup-dr/manifests/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

from recovery_set import ManifestSigner, capture_checkpoint, write_manifest  # noqa: E402

MANIFEST_DIR = REPO / "backup-dr" / "manifests"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cadence", choices=["daily", "weekly"], required=True)
    parser.add_argument("--key-id", default="recovery-manifest-1")
    parser.add_argument("--delta", required=True)
    parser.add_argument("--rds", required=True)
    parser.add_argument("--velero", required=True)
    parser.add_argument("--milvus", required=True)
    parser.add_argument("--model-digest", required=True)
    parser.add_argument("--opa-digest", required=True)
    parser.add_argument("--schema", required=True)
    args = parser.parse_args()

    signer = ManifestSigner()
    signer.create_key(args.key_id)
    comps = capture_checkpoint(
        cadence=args.cadence,
        delta_table_version=args.delta,
        rds_recovery_point=args.rds,
        velero_backup_id=args.velero,
        milvus_vector_checkpoint=args.milvus,
        model_prompt_digest=args.model_digest,
        opa_policy_bundle_digest=args.opa_digest,
        schema_migration_version=args.schema,
    )
    manifest = signer.sign(args.key_id, comps)
    out = MANIFEST_DIR / f"{comps.checkpoint_id}.json"
    write_manifest(out, manifest)
    print(json.dumps({"wrote": str(out), "digest": manifest.content_digest()}))


if __name__ == "__main__":
    main()
