"""G-011 workload-manifest structure and report binding tests."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from tools.link_load_report import link_report

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "tests" / "load" / "workload-manifest.yaml"


def test_workload_manifest_has_required_g011_fields() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    assert data["dataset"]["representative_not_invented"] is True
    assert data["dataset"]["partition_cardinality"] > 0
    assert data["io_mix"]["read_write_ratio"]
    assert abs(sum(t["weight"] for t in data["io_mix"]["query_templates"]) - 1.0) < 1e-6
    assert data["concurrency"]["virtual_users"] >= 1
    assert data["cache"]["cold_run"] and data["cache"]["warm_run"]
    assert data["duration"]["soak_seconds"] > 0
    assert data["slos"]["latency_p95_ms"] < data["slos"]["latency_p99_ms"]
    assert data["karpenter"]["scale_response_target_seconds"] > 0
    assert data["cost"]["max_test_usd"] > 0
    assert (REPO / data["k6"]["script"]).is_file()


def test_benchmark_report_links_dataset_and_code(tmp_path: Path, monkeypatch) -> None:
    import tools.link_load_report as mod

    monkeypatch.setattr(mod, "REPORT_DIR", tmp_path)
    out = link_report(code_version="abc123", manifest_path=MANIFEST)
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["code_version"] == "abc123"
    assert report["dataset_version"] == "bulk-bulk-001"
    assert report["manifest_version"] == "1.0.0"
    assert "checks" in report
