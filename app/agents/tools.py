"""Sandboxed, scope-declared tool wrappers (Section 1 / G-013 least privilege)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from app.agents.human_in_the_loop import ApprovalRejected, ApprovalToken, HumanInTheLoopGate


@dataclass(frozen=True)
class ToolScopeManifest:
    tool_name: str
    description: str
    allowed_resource_scopes: tuple[str, ...]
    requires_hitl: bool
    max_concurrency: int = 1
    sandbox: str = "gvisor"  # code-exec tools run on sandbox-runtime NodePool


@dataclass
class ToolRegistry:
    manifests: dict[str, ToolScopeManifest] = field(default_factory=dict)
    implementations: dict[str, Callable[..., Any]] = field(default_factory=dict)

    def register(
        self,
        manifest: ToolScopeManifest,
        impl: Callable[..., Any],
    ) -> None:
        self.manifests[manifest.tool_name] = manifest
        self.implementations[manifest.tool_name] = impl

    def get_manifest(self, tool_name: str) -> ToolScopeManifest:
        if tool_name not in self.manifests:
            raise KeyError(f"undeclared tool: {tool_name}")
        return self.manifests[tool_name]


DEFAULT_MANIFESTS = (
    ToolScopeManifest(
        tool_name="query_mission_data",
        description="Read curated mission marts via Trino under caller identity",
        allowed_resource_scopes=("mission_marts.reporting.*",),
        requires_hitl=False,
    ),
    ToolScopeManifest(
        tool_name="request_additional_intel",
        description="Request supplemental intel package for a mission",
        allowed_resource_scopes=("intel.request.*",),
        requires_hitl=False,
    ),
    ToolScopeManifest(
        tool_name="escalate_to_human",
        description="Escalate decision to human operator",
        allowed_resource_scopes=("hitl.escalate.*",),
        requires_hitl=False,
    ),
    ToolScopeManifest(
        tool_name="commit_recommendation",
        description="Commit a COA recommendation — high consequence",
        allowed_resource_scopes=("coa.commit.*",),
        requires_hitl=True,
    ),
)


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()

    def query_mission_data(*, mission_id: str, question: str) -> dict[str, Any]:
        return {"mission_id": mission_id, "answer": f"stub:{question}", "source": "marts"}

    def request_additional_intel(*, mission_id: str, topic: str) -> dict[str, Any]:
        return {"mission_id": mission_id, "intel_ticket": f"intel-{topic}", "status": "queued"}

    def escalate_to_human(*, mission_id: str, reason: str) -> dict[str, Any]:
        return {"mission_id": mission_id, "escalation": reason, "status": "pending_human"}

    def commit_recommendation(*, mission_id: str, coa_id: str) -> dict[str, Any]:
        return {"mission_id": mission_id, "coa_id": coa_id, "status": "committed"}

    mapping = {
        "query_mission_data": query_mission_data,
        "request_additional_intel": request_additional_intel,
        "escalate_to_human": escalate_to_human,
        "commit_recommendation": commit_recommendation,
    }
    for manifest in DEFAULT_MANIFESTS:
        registry.register(manifest, mapping[manifest.tool_name])
    return registry


class ScopedToolExecutor:
    """Enforces scope manifests and G-013 HITL before high-consequence tools."""

    def __init__(self, registry: ToolRegistry, hitl: HumanInTheLoopGate) -> None:
        self._registry = registry
        self._hitl = hitl

    def execute(
        self,
        tool_name: str,
        *,
        actor_id: str,
        tenant: str,
        mission_id: str,
        resource_scope: str,
        policy_version: str,
        arguments: dict[str, Any],
        approval: ApprovalToken | None = None,
    ) -> Any:
        manifest = self._registry.get_manifest(tool_name)
        if resource_scope not in manifest.allowed_resource_scopes:
            raise ApprovalRejected(f"resource_scope not permitted for {tool_name}")
        if manifest.requires_hitl:
            if approval is None:
                raise ApprovalRejected(f"{tool_name} requires human approval")
            self._hitl.authorize_execution(
                approval,
                actor_id=actor_id,
                tenant=tenant,
                mission_id=mission_id,
                tool_name=tool_name,
                exact_arguments=arguments,
                resource_scope=resource_scope,
                policy_version=policy_version,
            )
        return self._registry.implementations[tool_name](**arguments)
