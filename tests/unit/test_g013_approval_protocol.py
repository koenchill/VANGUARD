"""G-013 acceptance suite — every attack must be rejected (fail closed)."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.agents.human_in_the_loop import (
    ApprovalRejected,
    ApprovalToken,
    HumanInTheLoopGate,
    canonical_digest,
)
from app.agents.nonce_store import InMemoryNonceStore, UnavailableNonceStore
from app.agents.signing_service import KmsBackedSigningService


FIXED_NOW = datetime(2026, 7, 16, 18, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def harness():
    signing = KmsBackedSigningService()
    signing.create_key("approver-1")
    store = InMemoryNonceStore()
    gate = HumanInTheLoopGate(signing, store, clock=lambda: FIXED_NOW)
    req = gate.create_request(
        actor_id="agent-a",
        tenant="mission-tenant",
        mission_id="mission-alpha",
        tool_name="commit_recommendation",
        exact_arguments={"mission_id": "mission-alpha", "coa_id": "coa-1"},
        resource_scope="coa.commit.*",
        policy_version="2026.07",
        ttl_seconds=300,
    )
    token = gate.sign_approval(req, "approver-1")
    return gate, signing, store, token


def _authorize(gate: HumanInTheLoopGate, token: ApprovalToken, **overrides):
    fields = {
        "actor_id": token.request.actor_id,
        "tenant": token.request.tenant,
        "mission_id": token.request.mission_id,
        "tool_name": token.request.tool_name,
        "exact_arguments": dict(token.request.exact_arguments),
        "resource_scope": token.request.resource_scope,
        "policy_version": token.request.policy_version,
    }
    fields.update(overrides)
    gate.authorize_execution(token, **fields)


def test_happy_path_consumes_nonce(harness) -> None:
    gate, _, store, token = harness
    _authorize(gate, token)
    with pytest.raises(ApprovalRejected, match="already consumed|replay"):
        _authorize(gate, token)


def test_replay_rejected(harness) -> None:
    gate, _, _, token = harness
    _authorize(gate, token)
    with pytest.raises(ApprovalRejected):
        _authorize(gate, token)


def test_expiry_rejected(harness) -> None:
    signing = KmsBackedSigningService()
    signing.create_key("approver-1")
    store = InMemoryNonceStore()
    issued = HumanInTheLoopGate(signing, store, clock=lambda: FIXED_NOW)
    req = issued.create_request(
        actor_id="agent-a",
        tenant="mission-tenant",
        mission_id="mission-alpha",
        tool_name="commit_recommendation",
        exact_arguments={"mission_id": "mission-alpha", "coa_id": "coa-1"},
        resource_scope="coa.commit.*",
        policy_version="2026.07",
        ttl_seconds=60,
    )
    token = issued.sign_approval(req, "approver-1")
    expired_gate = HumanInTheLoopGate(
        signing, store, clock=lambda: FIXED_NOW + timedelta(seconds=120)
    )
    with pytest.raises(ApprovalRejected, match="expired"):
        _authorize(expired_gate, token)


def test_actor_substitution_rejected(harness) -> None:
    gate, _, _, token = harness
    with pytest.raises(ApprovalRejected):
        _authorize(gate, token, actor_id="attacker")


def test_tool_substitution_rejected(harness) -> None:
    gate, _, _, token = harness
    with pytest.raises(ApprovalRejected):
        _authorize(gate, token, tool_name="query_mission_data")


def test_argument_substitution_rejected(harness) -> None:
    gate, _, _, token = harness
    with pytest.raises(ApprovalRejected):
        _authorize(
            gate,
            token,
            exact_arguments={"mission_id": "mission-alpha", "coa_id": "coa-EVIL"},
        )


def test_signature_failure_rejected(harness) -> None:
    gate, _, _, token = harness
    bad = ApprovalToken(
        request=token.request,
        key_id=token.key_id,
        signature=b"\x00" * len(token.signature),
    )
    with pytest.raises(ApprovalRejected, match="signature"):
        _authorize(gate, bad)


def test_revoked_key_rejected(harness) -> None:
    gate, signing, _, token = harness
    signing.revoke_key("approver-1")
    with pytest.raises(ApprovalRejected):
        _authorize(gate, token)


def test_concurrent_double_consumption_one_winner(harness) -> None:
    gate, _, _, token = harness
    results: list[str] = []
    barrier = threading.Barrier(2)

    def attempt() -> None:
        barrier.wait()
        try:
            _authorize(gate, token)
            results.append("ok")
        except ApprovalRejected:
            results.append("rejected")

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: attempt(), range(2)))
    assert results.count("ok") == 1
    assert results.count("rejected") == 1


def test_store_outage_rejected() -> None:
    signing = KmsBackedSigningService()
    signing.create_key("approver-1")
    gate = HumanInTheLoopGate(signing, UnavailableNonceStore(), clock=lambda: FIXED_NOW)
    with pytest.raises(ApprovalRejected, match="unavailable"):
        gate.create_request(
            actor_id="agent-a",
            tenant="mission-tenant",
            mission_id="mission-alpha",
            tool_name="commit_recommendation",
            exact_arguments={"mission_id": "mission-alpha", "coa_id": "coa-1"},
            resource_scope="coa.commit.*",
            policy_version="2026.07",
        )


def test_store_outage_at_consume_rejected(harness) -> None:
    gate, _, store, token = harness
    store.available = False
    with pytest.raises(ApprovalRejected, match="unavailable"):
        _authorize(gate, token)


def test_canonical_digest_stable_under_key_order() -> None:
    a = {
        "actor_id": "a",
        "tenant": "t",
        "mission_id": "m",
        "tool_name": "commit_recommendation",
        "exact_arguments": {"b": 1, "a": 2},
        "resource_scope": "coa.commit.*",
        "policy_version": "1",
        "issuance_time": "t0",
        "expiration_time": "t1",
        "nonce": "n1",
    }
    b = dict(a)
    b["exact_arguments"] = {"a": 2, "b": 1}
    assert canonical_digest(a) == canonical_digest(b)


def test_forged_request_object_still_rejected(harness) -> None:
    """Mutating the frozen request via replace must not authorize a different action."""
    gate, signing, _, token = harness
    forged_req = replace(
        token.request,
        tool_name="query_mission_data",
        exact_arguments={"mission_id": "mission-alpha", "question": "x"},
    )
    # Recompute would change digest; keep old signature → must fail.
    forged = ApprovalToken(request=forged_req, key_id=token.key_id, signature=token.signature)
    with pytest.raises(ApprovalRejected):
        _authorize(
            gate,
            forged,
            tool_name="query_mission_data",
            exact_arguments={"mission_id": "mission-alpha", "question": "x"},
        )
