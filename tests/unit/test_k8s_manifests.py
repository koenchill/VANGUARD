"""Phase 5: manifests are generated from resource contracts (G-007)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import render_resources as rr  # noqa: E402

DIGESTS = REPO / "infra" / "k8s" / "generated" / "resource-digests.json"
NODEPOOLS = REPO / "infra" / "k8s" / "karpenter" / "nodepools.yaml"
DATASOURCES = REPO / "analytics" / "grafana" / "provisioning" / "datasources.yaml"


def test_digests_match_live_renderer() -> None:
    schema = rr.load_schema(rr.DEFAULT_SCHEMA)
    recorded = json.loads(DIGESTS.read_text(encoding="utf-8"))
    for workload, meta in recorded.items():
        path = REPO / "infra" / "docker" / "resources" / f"{workload}.yaml"
        live = rr.render_pair(path, schema)
        assert live["pair_digest"] == meta["pair_digest"], workload
        manifest = yaml.safe_load_all((REPO / meta["manifest"]).read_text(encoding="utf-8"))
        deployment = next(doc for doc in manifest if doc and doc.get("kind") == "Deployment")
        resources = deployment["spec"]["template"]["spec"]["containers"][0]["resources"]
        expected = yaml.safe_load(live["k8s_resources_yaml"])["resources"]
        assert resources == expected


def test_workloads_pin_to_exclusive_nodepools() -> None:
    recorded = json.loads(DIGESTS.read_text(encoding="utf-8"))
    assert recorded["gateway"]["nodepool"] == "gateway-general"
    assert recorded["inference"]["nodepool"] == "inference-gpu"
    assert recorded["pipeline"]["nodepool"] == "pipeline-cpu"

    for workload, meta in recorded.items():
        docs = list(yaml.safe_load_all((REPO / meta["manifest"]).read_text(encoding="utf-8")))
        dep = next(d for d in docs if d and d.get("kind") == "Deployment")
        assert dep["spec"]["template"]["spec"]["nodeSelector"]["karpenter.sh/nodepool"] == meta["nodepool"]
        taints = dep["spec"]["template"]["spec"]["tolerations"]
        assert any(t.get("value") == meta["nodepool"] for t in taints)


def test_four_mutually_exclusive_nodepools() -> None:
    docs = list(yaml.safe_load_all(NODEPOOLS.read_text(encoding="utf-8")))
    pools = [d for d in docs if d and d.get("kind") == "NodePool"]
    names = {p["metadata"]["name"] for p in pools}
    assert names == {"inference-gpu", "pipeline-cpu", "gateway-general", "sandbox-runtime"}
    families_by_pool = {}
    for p in pools:
        reqs = p["spec"]["template"]["spec"]["requirements"]
        fam = next(r["values"] for r in reqs if r["key"] == "karpenter.k8s.aws/instance-family")
        families_by_pool[p["metadata"]["name"]] = set(fam)
    # No instance family appears in more than one pool (G-016).
    seen: set[str] = set()
    for fams in families_by_pool.values():
        assert seen.isdisjoint(fams)
        seen |= fams


def test_no_powerbi_gateway_k8s_manifest() -> None:
    k8s_root = REPO / "infra" / "k8s"
    for path in k8s_root.rglob("*.yaml"):
        text = path.read_text(encoding="utf-8").lower()
        assert "powerbi" not in text, path


def test_grafana_oauth_passthru() -> None:
    data = yaml.safe_load(DATASOURCES.read_text(encoding="utf-8"))
    trino = next(d for d in data["datasources"] if d["name"] == "MissionBI-Trino")
    assert trino["jsonData"]["oauthPassThru"] is True


def test_kustomize_build_dev_and_prod() -> None:
    for env in ("dev", "prod"):
        proc = subprocess.run(
            ["kubectl", "kustomize", str(REPO / "infra" / "k8s" / "overlays" / env)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        assert "kind: Deployment" in proc.stdout
        assert "kind: NodePool" in proc.stdout
        assert "MissionBI-Trino" in proc.stdout


def test_generator_is_idempotent() -> None:
    before = DIGESTS.read_text(encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(REPO / "tools" / "generate_k8s_manifests.py")],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Phase 5 manifests generated" in proc.stdout
    assert DIGESTS.read_text(encoding="utf-8") == before
