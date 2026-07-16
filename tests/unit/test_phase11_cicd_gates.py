"""Phase 11 — CI/CD supply-chain gates (G-015 / G-019)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CHECK = REPO / "tools" / "check_cicd_gates.py"
WORKFLOWS = REPO / ".github" / "workflows"


def test_real_workflows_are_sha_pinned() -> None:
    proc = subprocess.run(
        [sys.executable, str(CHECK), "--workflows", str(WORKFLOWS)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_dast_target_is_localhost_only() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(CHECK),
            "--assert-dast-localhost",
            "--workflow",
            str(WORKFLOWS / "ci-cd-pipeline.yaml"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_planted_fixtures_are_caught() -> None:
    proc = subprocess.run(
        [sys.executable, str(CHECK), "--verify-planted-fixtures"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_workflows_document_g015_dast_pattern() -> None:
    text = (WORKFLOWS / "ci-cd-pipeline.yaml").read_text(encoding="utf-8")
    assert "readyz" in text
    assert "openapi.json" in text
    assert "localhost:8000" in text
    assert "gateway.Dockerfile" in text
    assert "cosign" in text
    assert "syft" in text or "SBOM" in text


def test_runner_network_policy_denies_prod_hosts() -> None:
    import yaml

    policy = yaml.safe_load(
        (REPO / "security" / "sast-sca-dast" / "runner-network-policy.yaml").read_text(
            encoding="utf-8"
        )
    )
    deny = set(policy["spec"]["deny"])
    assert "api.vanguard.prod" in deny
    assert "localhost" in policy["spec"]["dast"]["requireTargetHost"]


def test_finding_policy_ignores_planted_paths() -> None:
    import yaml

    policy = yaml.safe_load(
        (REPO / "security" / "sast-sca-dast" / "finding-policy.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert any("planted" in p for p in policy["ignore"]["paths"])
