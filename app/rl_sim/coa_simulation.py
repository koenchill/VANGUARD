"""G-022 scoped COA-selection simulation under uncertainty.

Uses the same tool interface as app/agents/tools.py. Never connects to production
tools, data, or the AI Gateway. Policies are evaluated before any promotion —
never auto-deployed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.tools import ToolRegistry, build_default_registry


@dataclass
class MissionState:
    """Structured observation — not raw sensor data."""

    mission_id: str
    uncertainty: float
    intel_completeness: float
    threat_level: float
    step: int = 0


@dataclass
class CoaSimConfig:
    max_steps: int = 4
    success_threshold: float = 0.7
    sandbox: bool = True
    allow_production_gateway: bool = False
    allow_production_data: bool = False


@dataclass
class CoaSimulation:
    """Sandboxed training/eval harness for the production tool interface."""

    config: CoaSimConfig = field(default_factory=CoaSimConfig)
    registry: ToolRegistry = field(default_factory=build_default_registry)
    history: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.config.sandbox:
            raise RuntimeError("G-022 requires sandbox=True")
        if self.config.allow_production_gateway or self.config.allow_production_data:
            raise RuntimeError("G-022 forbids production gateway/data connectivity")

    def observe(self, state: MissionState) -> dict[str, float]:
        return {
            "uncertainty": state.uncertainty,
            "intel_completeness": state.intel_completeness,
            "threat_level": state.threat_level,
        }

    def available_actions(self) -> tuple[str, ...]:
        return tuple(self.registry.manifests.keys())

    def step(self, state: MissionState, action: str, **kwargs: Any) -> MissionState:
        if state.step >= self.config.max_steps:
            raise RuntimeError("max_steps exceeded")
        if action not in self.registry.manifests:
            raise KeyError(action)
        # Simulation stubs — do not call live HITL/gateway.
        result = {"action": action, "kwargs": kwargs, "simulated": True}
        self.history.append(result)
        state.step += 1
        if action == "request_additional_intel":
            state.intel_completeness = min(1.0, state.intel_completeness + 0.25)
            state.uncertainty = max(0.0, state.uncertainty - 0.15)
        elif action == "query_mission_data":
            state.uncertainty = max(0.0, state.uncertainty - 0.1)
        elif action == "commit_recommendation":
            state.threat_level = max(0.0, state.threat_level - 0.2)
        return state

    def reward(self, state: MissionState) -> float:
        """Mission-success proxy metric defined per scenario."""
        completeness = state.intel_completeness
        calm = 1.0 - state.threat_level
        certainty = 1.0 - state.uncertainty
        return (0.4 * completeness) + (0.3 * calm) + (0.3 * certainty)

    def success(self, state: MissionState) -> bool:
        return self.reward(state) >= self.config.success_threshold
