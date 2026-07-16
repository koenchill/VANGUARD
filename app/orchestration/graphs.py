"""LangGraph-style mission workflow graphs (orchestration layer)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from app.agents.human_in_the_loop import ApprovalToken, HumanInTheLoopGate
from app.agents.supervisor import Supervisor
from app.telemetry.events import TelemetryLogger


@dataclass
class GraphState:
    mission_id: str
    tenant: str
    policy_version: str
    question: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    pending_approval: ApprovalToken | None = None
    committed: bool = False


NodeFn = Callable[[GraphState], GraphState]


@dataclass
class MissionGraph:
    """Minimal deterministic graph runner — same topology a LangGraph compile would use."""

    nodes: dict[str, NodeFn]
    edges: dict[str, str]
    start: str = "recon"

    def run(self, state: GraphState) -> GraphState:
        node = self.start
        while node != "END":
            state = self.nodes[node](state)
            node = self.edges[node]
        return state


def build_coa_graph(
    supervisor: Supervisor,
    hitl: HumanInTheLoopGate,
    *,
    signing_key_id: str,
) -> MissionGraph:
    def recon(state: GraphState) -> GraphState:
        plan = supervisor.plan_coa(state.mission_id, state.question)
        step = plan.steps[0]
        supervisor.run_step(
            step,
            tenant=state.tenant,
            policy_version=state.policy_version,
            resource_scope="mission_marts.reporting.*",
        )
        state.messages.append({"node": "recon", "result": step.result})
        return state

    def intel(state: GraphState) -> GraphState:
        plan = supervisor.plan_coa(state.mission_id, state.question)
        step = plan.steps[1]
        supervisor.run_step(
            step,
            tenant=state.tenant,
            policy_version=state.policy_version,
            resource_scope="intel.request.*",
        )
        state.messages.append({"node": "intel", "result": step.result})
        return state

    def approve_commit(state: GraphState) -> GraphState:
        args = {"mission_id": state.mission_id, "coa_id": "coa-alpha"}
        req = hitl.create_request(
            actor_id="decide",
            tenant=state.tenant,
            mission_id=state.mission_id,
            tool_name="commit_recommendation",
            exact_arguments=args,
            resource_scope="coa.commit.*",
            policy_version=state.policy_version,
        )
        state.pending_approval = hitl.sign_approval(req, signing_key_id)
        return state

    def commit(state: GraphState) -> GraphState:
        plan = supervisor.plan_coa(state.mission_id, state.question)
        step = plan.steps[2]
        supervisor.run_step(
            step,
            tenant=state.tenant,
            policy_version=state.policy_version,
            resource_scope="coa.commit.*",
            approval=state.pending_approval,
        )
        state.committed = True
        state.messages.append({"node": "commit", "result": step.result})
        return state

    return MissionGraph(
        nodes={
            "recon": recon,
            "intel": intel,
            "approve_commit": approve_commit,
            "commit": commit,
        },
        edges={
            "recon": "intel",
            "intel": "approve_commit",
            "approve_commit": "commit",
            "commit": "END",
        },
    )


def default_runtime(hitl: HumanInTheLoopGate, key_id: str) -> MissionGraph:
    supervisor = Supervisor(hitl, TelemetryLogger())
    return build_coa_graph(supervisor, hitl, signing_key_id=key_id)
