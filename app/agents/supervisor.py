"""Multi-agent supervisor / planner — composes tools + HITL + telemetry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.human_in_the_loop import ApprovalToken, HumanInTheLoopGate
from app.agents.tools import ScopedToolExecutor, ToolRegistry, build_default_registry
from app.telemetry.events import TelemetryLogger


@dataclass
class AgentStep:
    agent_id: str
    tool_name: str
    arguments: dict[str, Any]
    result: Any = None
    status: str = "pending"


@dataclass
class MissionPlan:
    mission_id: str
    steps: list[AgentStep] = field(default_factory=list)


class Supervisor:
    """Coordinates tool-using agents under least-privilege scopes."""

    def __init__(
        self,
        hitl: HumanInTheLoopGate,
        telemetry: TelemetryLogger,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.registry = registry or build_default_registry()
        self.executor = ScopedToolExecutor(self.registry, hitl)
        self.hitl = hitl
        self.telemetry = telemetry

    def plan_coa(self, mission_id: str, question: str) -> MissionPlan:
        return MissionPlan(
            mission_id=mission_id,
            steps=[
                AgentStep("recon", "query_mission_data", {"mission_id": mission_id, "question": question}),
                AgentStep(
                    "intel",
                    "request_additional_intel",
                    {"mission_id": mission_id, "topic": "delta"},
                ),
                AgentStep(
                    "decide",
                    "commit_recommendation",
                    {"mission_id": mission_id, "coa_id": "coa-alpha"},
                ),
            ],
        )

    def run_step(
        self,
        step: AgentStep,
        *,
        tenant: str,
        policy_version: str,
        resource_scope: str,
        approval: ApprovalToken | None = None,
    ) -> AgentStep:
        result = self.executor.execute(
            step.tool_name,
            actor_id=step.agent_id,
            tenant=tenant,
            mission_id=step.arguments["mission_id"],
            resource_scope=resource_scope,
            policy_version=policy_version,
            arguments=step.arguments,
            approval=approval,
        )
        step.result = result
        step.status = "ok"
        self.telemetry.log_step(
            agent_id=step.agent_id,
            mission_id=step.arguments["mission_id"],
            step_name=step.tool_name,
            payload={"arguments": step.arguments, "result": result},
        )
        return step
