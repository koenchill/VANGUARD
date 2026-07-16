"""Unit tests for tools/render-resources.py (G-007)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RENDERER = REPO_ROOT / "tools" / "render_resources.py"
RESOURCES = REPO_ROOT / "infra" / "docker" / "resources"
SCHEMA = RESOURCES / "schema.json"

sys.path.insert(0, str(REPO_ROOT / "tools"))
import render_resources as rr  # noqa: E402


@pytest.fixture(scope="module")
def schema() -> dict:
    return rr.load_schema(SCHEMA)


@pytest.mark.parametrize(
    "name",
    ["inference.yaml", "pipeline.yaml", "gateway.yaml"],
)
def test_contracts_validate_against_schema(name: str, schema: dict) -> None:
    contract = rr.load_contract(RESOURCES / name)
    rr.validate_contract(contract, schema)


def test_inference_renders_gpu_limit(schema: dict) -> None:
    result = rr.render_pair(RESOURCES / "inference.yaml", schema)
    k8s = yaml.safe_load(result["k8s_resources_yaml"])
    assert k8s["resources"]["limits"]["nvidia.com/gpu"] == "1"
    assert "nvidia.com/gpu" in k8s["resources"]["requests"]
    karpenter = yaml.safe_load(result["karpenter_capacity_yaml"])
    assert (
        karpenter["karpenter_capacity_assumption"]["nodepool"]
        == "inference-gpu"
    )


def test_pipeline_and_gateway_have_no_gpu(schema: dict) -> None:
    for name in ("pipeline.yaml", "gateway.yaml"):
        result = rr.render_pair(RESOURCES / name, schema)
        k8s = yaml.safe_load(result["k8s_resources_yaml"])
        assert "nvidia.com/gpu" not in k8s["resources"]["limits"]
        assert "nvidia.com/gpu" not in k8s["resources"]["requests"]


def test_digests_are_stable_sha256(schema: dict) -> None:
    first = rr.render_pair(RESOURCES / "gateway.yaml", schema)
    second = rr.render_pair(RESOURCES / "gateway.yaml", schema)
    assert first["k8s_digest"] == second["k8s_digest"]
    assert first["karpenter_digest"] == second["karpenter_digest"]
    assert first["pair_digest"] == second["pair_digest"]
    assert len(first["pair_digest"]) == 64


def test_digest_changes_when_contract_changes(schema: dict, tmp_path: Path) -> None:
    base = rr.load_contract(RESOURCES / "gateway.yaml")
    mutated = dict(base)
    mutated["cpu_limit"] = "2000m"
    path = tmp_path / "gateway-mutated.yaml"
    path.write_text(yaml.safe_dump(mutated), encoding="utf-8")
    original = rr.render_pair(RESOURCES / "gateway.yaml", schema)
    changed = rr.render_pair(path, schema)
    assert original["pair_digest"] != changed["pair_digest"]


def test_cli_json_output_includes_all_workloads() -> None:
    proc = subprocess.run(
        [sys.executable, str(RENDERER), "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    workloads = {item["workload"] for item in payload}
    assert workloads == {"inference", "pipeline", "gateway"}
    for item in payload:
        assert item["k8s_digest"]
        assert item["karpenter_digest"]
        assert item["pair_digest"]
