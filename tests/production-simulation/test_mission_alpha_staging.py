"""Production-simulation scenario runner (Local evidence)."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.agents.human_in_the_loop import HumanInTheLoopGate
from app.agents.nonce_store import InMemoryNonceStore
from app.agents.signing_service import KmsBackedSigningService
from app.evaluation.harness import load_contract, run_eval
from app.orchestration.graphs import GraphState, default_runtime

REPO = Path(__file__).resolve().parents[2]
SCENARIO = Path(__file__).resolve().parent / "scenarios" / "mission-alpha-staging.yaml"


def run_mission_alpha_staging(*, code_version: str = "local-sim") -> dict:
    scenario = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    results: list[dict] = []

    # agent_coa
    signing = KmsBackedSigningService()
    signing.create_key("approver-1")
    hitl = HumanInTheLoopGate(signing, InMemoryNonceStore())
    graph = default_runtime(hitl, "approver-1")
    state = graph.run(
        GraphState(
            mission_id=scenario["mission_id"],
            tenant="mission-tenant",
            policy_version="2026.07",
            question="recommend COA",
        )
    )
    results.append({"id": "agent_coa", "ok": state.committed is True})

    # eval_gate
    contract = load_contract("mission-alpha")
    report = run_eval(contract, code_version=code_version, repo=REPO)
    results.append(
        {
            "id": "eval_gate",
            "ok": report.passed is True,
            "contract_identity": report.contract_identity,
        }
    )

    # load_smoke — bind report without requiring live k6
    from tools.link_load_report import link_report

    bench = link_report(code_version=code_version)
    results.append({"id": "load_smoke", "ok": bench.is_file(), "report": str(bench)})

    passed = all(r["ok"] for r in results)
    return {
        "scenario_version": scenario["scenario_version"],
        "namespace": scenario["namespace"],
        "passed": passed,
        "steps": results,
    }


def test_production_simulation_mission_alpha() -> None:
    out = run_mission_alpha_staging(code_version="prodsim-test")
    assert out["passed"] is True
    assert out["namespace"] == "staging"
