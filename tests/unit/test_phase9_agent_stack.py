"""Phase 9 smoke — agent stack modules wire together without production side effects."""

from __future__ import annotations

from app.agents.human_in_the_loop import HumanInTheLoopGate
from app.agents.nonce_store import InMemoryNonceStore
from app.agents.signing_service import KmsBackedSigningService
from app.agents.supervisor import Supervisor
from app.gateway import load_policies, require_end_user_identity
from app.orchestration import default_runtime
from app.rag import Document, HnswParams, MilvusAdapter, chunk_document, ingest_documents
from app.rl_sim import CoaSimConfig, CoaSimulation, MissionState
from app.telemetry import TelemetryLogger
from app.tools import load_manifests


def test_orchestration_coa_graph_with_hitl() -> None:
    signing = KmsBackedSigningService()
    signing.create_key("approver-1")
    gate = HumanInTheLoopGate(signing, InMemoryNonceStore())
    graph = default_runtime(gate, "approver-1")
    from app.orchestration.graphs import GraphState

    state = GraphState(
        mission_id="mission-alpha",
        tenant="mission-tenant",
        policy_version="2026.07",
        question="best COA?",
    )
    final = graph.run(state)
    assert final.committed is True
    assert len(final.messages) == 3


def test_rag_rejects_uncurated_and_exposes_hnsw() -> None:
    with __import__("pytest").raises(ValueError):
        ingest_documents(
            [Document("d1", "v1", "landed", "secret raw text")]
        )
    docs = ingest_documents([Document("d1", "v1", "approved", "alpha " * 40)])
    chunks = chunk_document(docs[0], max_chars=40, overlap=5)
    adapter = MilvusAdapter(hnsw=HnswParams(M=16, efConstruction=200, efSearch=64))
    adapter.upsert_chunks(chunks, [[0.1] * 8 for _ in chunks])
    params = adapter.index_params()
    assert params["index_type"] == "HNSW"
    assert params["M"] == 16
    assert adapter.search([0.1] * 8)


def test_gateway_policies_fail_closed() -> None:
    policies = load_policies()
    assert policies["plugins"]
    with __import__("pytest").raises(PermissionError):
        require_end_user_identity({})
    assert require_end_user_identity({"X-End-User-Identity": "user-a"}) == "user-a"


def test_rl_sim_uses_same_tool_interface_and_stays_sandboxed() -> None:
    sim = CoaSimulation(config=CoaSimConfig())
    assert set(sim.available_actions()) == set(
        Supervisor(HumanInTheLoopGate(KmsBackedSigningService(), InMemoryNonceStore()), TelemetryLogger())
        .registry.manifests.keys()
    )
    state = MissionState("m1", uncertainty=0.8, intel_completeness=0.2, threat_level=0.6)
    state = sim.step(state, "query_mission_data", mission_id="m1", question="x")
    state = sim.step(state, "request_additional_intel", mission_id="m1", topic="y")
    assert sim.reward(state) > 0
    with __import__("pytest").raises(RuntimeError):
        CoaSimulation(config=CoaSimConfig(allow_production_gateway=True))


def test_tool_manifests_on_disk() -> None:
    manifests = load_manifests()
    assert "commit_recommendation" in manifests
    assert manifests["commit_recommendation"]["requires_hitl"] is True
