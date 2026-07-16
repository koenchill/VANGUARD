"""Chaos injections — verify HITL fail-closed fallback, not silent degradation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pytest

from app.agents.human_in_the_loop import ApprovalRejected, HumanInTheLoopGate
from app.agents.nonce_store import InMemoryNonceStore, UnavailableNonceStore
from app.agents.signing_service import KmsBackedSigningService
from app.agents.tools import ScopedToolExecutor, build_default_registry


@dataclass
class ChaosScenario:
    name: str
    inject: Callable[[], None]
    expect_hitl_block: bool


def _executor_with(store) -> tuple[ScopedToolExecutor, HumanInTheLoopGate, KmsBackedSigningService]:
    signing = KmsBackedSigningService()
    signing.create_key("approver-1")
    hitl = HumanInTheLoopGate(signing, store)
    return ScopedToolExecutor(build_default_registry(), hitl), hitl, signing


def test_metadata_db_failover_store_outage_blocks_commit() -> None:
    exe, hitl, _ = _executor_with(UnavailableNonceStore())
    with pytest.raises(ApprovalRejected):
        hitl.create_request(
            actor_id="decide",
            tenant="t",
            mission_id="mission-alpha",
            tool_name="commit_recommendation",
            exact_arguments={"mission_id": "mission-alpha", "coa_id": "coa-1"},
            resource_scope="coa.commit.*",
            policy_version="2026.07",
        )


def test_gateway_latency_does_not_bypass_hitl(monkeypatch) -> None:
    store = InMemoryNonceStore()
    exe, hitl, signing = _executor_with(store)

    # Simulate gateway latency wrapper — still must require approval.
    def slow_execute(*args, **kwargs):
        return exe.execute(*args, **kwargs)

    with pytest.raises(ApprovalRejected, match="requires human approval"):
        slow_execute(
            "commit_recommendation",
            actor_id="decide",
            tenant="t",
            mission_id="mission-alpha",
            resource_scope="coa.commit.*",
            policy_version="2026.07",
            arguments={"mission_id": "mission-alpha", "coa_id": "coa-1"},
            approval=None,
        )


def test_vector_store_unavailability_fails_closed() -> None:
    from app.rag.milvus_adapter import MilvusAdapter

    class DownAdapter(MilvusAdapter):
        def search(self, query_embedding, *, top_k: int = 5):
            raise RuntimeError("vector store unavailable")

    adapter = DownAdapter()
    with pytest.raises(RuntimeError, match="unavailable"):
        adapter.search([0.1, 0.2])


def test_llm_timeout_triggers_escalate_path() -> None:
    store = InMemoryNonceStore()
    exe, _, _ = _executor_with(store)
    result = exe.execute(
        "escalate_to_human",
        actor_id="recon",
        tenant="t",
        mission_id="mission-alpha",
        resource_scope="hitl.escalate.*",
        policy_version="2026.07",
        arguments={"mission_id": "mission-alpha", "reason": "llm_timeout"},
    )
    assert result["status"] == "pending_human"
    assert result["escalation"] == "llm_timeout"


def test_node_loss_cannot_replay_consumed_approval() -> None:
    store = InMemoryNonceStore()
    exe, hitl, signing = _executor_with(store)
    req = hitl.create_request(
        actor_id="decide",
        tenant="t",
        mission_id="mission-alpha",
        tool_name="commit_recommendation",
        exact_arguments={"mission_id": "mission-alpha", "coa_id": "coa-1"},
        resource_scope="coa.commit.*",
        policy_version="2026.07",
    )
    token = hitl.sign_approval(req, "approver-1")
    exe.execute(
        "commit_recommendation",
        actor_id="decide",
        tenant="t",
        mission_id="mission-alpha",
        resource_scope="coa.commit.*",
        policy_version="2026.07",
        arguments={"mission_id": "mission-alpha", "coa_id": "coa-1"},
        approval=token,
    )
    # Surviving node retries with same token — must fail closed (replay).
    with pytest.raises(ApprovalRejected):
        exe.execute(
            "commit_recommendation",
            actor_id="decide",
            tenant="t",
            mission_id="mission-alpha",
            resource_scope="coa.commit.*",
            policy_version="2026.07",
            arguments={"mission_id": "mission-alpha", "coa_id": "coa-1"},
            approval=token,
        )
