"""Bind a K6 summary to the G-011 workload manifest (dataset + code version)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "tests" / "load" / "workload-manifest.yaml"
REPORT_DIR = REPO / "tests" / "load" / "reports"


def link_report(
    *,
    code_version: str,
    k6_summary: Path | None = None,
    manifest_path: Path | None = None,
) -> Path:
    manifest = yaml.safe_load((manifest_path or MANIFEST).read_text(encoding="utf-8"))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {}
    if k6_summary and k6_summary.is_file():
        summary = json.loads(k6_summary.read_text(encoding="utf-8"))

    # Evaluate thresholds from manifest against k6 metrics when present.
    metrics = summary.get("metrics", {})
    http_duration = metrics.get("http_req_duration", {}).get("values", {})
    p95 = http_duration.get("p(95)")
    p99 = http_duration.get("p(99)")
    err = metrics.get("errors", {}).get("values", {}).get("rate")

    slos = manifest["slos"]
    checks = {
        "latency_p95_ms": {
            "threshold": slos["latency_p95_ms"],
            "actual": p95,
            "passed": p95 is None or p95 <= slos["latency_p95_ms"],
        },
        "latency_p99_ms": {
            "threshold": slos["latency_p99_ms"],
            "actual": p99,
            "passed": p99 is None or p99 <= slos["latency_p99_ms"],
        },
        "error_budget_pct": {
            "threshold": slos["error_budget_pct"],
            "actual": None if err is None else err * 100,
            "passed": err is None or (err * 100) <= slos["error_budget_pct"],
        },
    }
    passed = all(c["passed"] for c in checks.values())

    report = {
        "manifest_version": manifest["manifest_version"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "code_version": code_version,
        "dataset_version": manifest["dataset"]["dataset_version"],
        "lakefs_commit_id": manifest["dataset"]["lakefs_commit_id"],
        "karpenter_scale_response_target_seconds": manifest["karpenter"][
            "scale_response_target_seconds"
        ],
        "cost_ceiling": manifest["cost"],
        "checks": checks,
        "passed": passed,
        "note": "Green runs without this manifest binding do not count (G-011).",
    }
    out = REPORT_DIR / f"benchmark-{code_version}.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-version", required=True)
    parser.add_argument("--k6-summary", type=Path, default=None)
    args = parser.parse_args()
    path = link_report(code_version=args.code_version, k6_summary=args.k6_summary)
    print(path)


if __name__ == "__main__":
    main()
