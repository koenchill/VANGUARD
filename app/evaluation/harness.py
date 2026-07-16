"""G-010 evaluation contract loader and deterministic harness.

Ragas/TruLens are the named metric families; this harness binds them to a versioned
contract so seeded fixtures always produce the same pass/fail decision. Changing the
judge model or a threshold requires a contract_version bump.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = Path(__file__).resolve().parent / "contracts"


class ContractError(Exception):
    pass


@dataclass(frozen=True)
class EvalContract:
    raw: dict[str, Any]
    path: Path

    @property
    def version(self) -> str:
        return str(self.raw["contract_version"])

    @property
    def mission_id(self) -> str:
        return str(self.raw["mission_id"])

    @property
    def identity(self) -> str:
        """Stable identity — prior results invalid when this changes."""
        blob = json.dumps(self.raw, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass
class MetricResult:
    name: str
    value: float
    threshold: float
    direction: str
    blocking: bool
    passed: bool


@dataclass
class EvalReport:
    contract_identity: str
    contract_version: str
    mission_id: str
    judge_model_version: str
    dataset_version: str
    code_version: str
    seeds: list[int]
    metrics: list[MetricResult] = field(default_factory=list)
    passed: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_identity": self.contract_identity,
            "contract_version": self.contract_version,
            "mission_id": self.mission_id,
            "judge_model_version": self.judge_model_version,
            "dataset_version": self.dataset_version,
            "code_version": self.code_version,
            "seeds": self.seeds,
            "passed": self.passed,
            "notes": self.notes,
            "metrics": [m.__dict__ for m in self.metrics],
        }


def load_contract(mission_id: str, *, contracts_dir: Path | None = None) -> EvalContract:
    root = contracts_dir or CONTRACTS_DIR
    path = root / f"{mission_id}.yaml"
    if not path.is_file():
        raise ContractError(f"missing contract: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    _validate_contract(raw)
    return EvalContract(raw=raw, path=path)


def _validate_contract(raw: dict[str, Any]) -> None:
    required = (
        "contract_version",
        "mission_id",
        "metrics",
        "golden_set",
        "seed_protocol",
        "judge_model",
        "failure_budget",
        "rerun_policy",
    )
    missing = [k for k in required if k not in raw]
    if missing:
        raise ContractError(f"contract missing fields: {missing}")
    seeds = raw["seed_protocol"].get("seeds") or []
    repeats = int(raw["seed_protocol"].get("repeats", 0))
    if len(seeds) != repeats:
        raise ContractError("seed_protocol.seeds length must equal repeats")
    if int(raw["golden_set"].get("min_sample_size", 0)) < 1:
        raise ContractError("golden_set.min_sample_size must be >= 1")


def load_golden_set(contract: EvalContract, *, repo: Path | None = None) -> list[dict[str, Any]]:
    base = repo or REPO
    rel = contract.raw["golden_set"]["path"]
    path = base / rel
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    min_n = int(contract.raw["golden_set"]["min_sample_size"])
    if len(rows) < min_n:
        raise ContractError(f"golden set size {len(rows)} < min_sample_size {min_n}")
    return rows


def _score_sample(sample: dict[str, Any], metric: str, rng: random.Random) -> float:
    """Deterministic stand-in for Ragas/TruLens metric computation on fixtures."""
    # Fixture may embed expected metric values; otherwise derive from label.
    if "metrics" in sample and metric in sample["metrics"]:
        base = float(sample["metrics"][metric])
    elif sample.get("label") == "positive":
        base = {"faithfulness": 0.92, "answer_relevancy": 0.88, "hallucination_rate": 0.04, "task_completion": 0.95}[metric]
    else:
        base = {"faithfulness": 0.40, "answer_relevancy": 0.35, "hallucination_rate": 0.55, "task_completion": 0.20}[metric]
    # Tiny seed-dependent jitter that averages out across pinned seeds — same set => same mean.
    jitter = (rng.random() - 0.5) * 0.01
    return max(0.0, min(1.0, base + jitter))


def _passes(value: float, threshold: float, direction: str) -> bool:
    if direction == "maximize":
        return value >= threshold
    if direction == "minimize":
        return value <= threshold
    raise ContractError(f"unknown direction: {direction}")


def run_eval(
    contract: EvalContract,
    *,
    code_version: str,
    repo: Path | None = None,
    fixture_override: list[dict[str, Any]] | None = None,
) -> EvalReport:
    samples = fixture_override if fixture_override is not None else load_golden_set(contract, repo=repo)
    seeds: list[int] = list(contract.raw["seed_protocol"]["seeds"])
    metric_defs: dict[str, Any] = contract.raw["metrics"]

    # Aggregate mean across seeds then across samples (deterministic).
    aggregates: dict[str, list[float]] = {name: [] for name in metric_defs}
    for seed in seeds:
        rng = random.Random(seed)
        for sample in samples:
            for name in metric_defs:
                aggregates[name].append(_score_sample(sample, name, rng))

    results: list[MetricResult] = []
    blocking_failures = 0
    nonblocking_failures = 0
    for name, spec in metric_defs.items():
        values = aggregates[name]
        mean = sum(values) / len(values)
        passed = _passes(mean, float(spec["threshold"]), spec["direction"])
        results.append(
            MetricResult(
                name=name,
                value=round(mean, 6),
                threshold=float(spec["threshold"]),
                direction=spec["direction"],
                blocking=bool(spec["blocking"]),
                passed=passed,
            )
        )
        if not passed:
            if spec["blocking"]:
                blocking_failures += 1
            else:
                nonblocking_failures += 1

    budget = contract.raw["failure_budget"]
    ok = (
        blocking_failures <= int(budget["max_blocking_failures"])
        and nonblocking_failures <= int(budget["max_nonblocking_failures"])
    )
    report = EvalReport(
        contract_identity=contract.identity,
        contract_version=contract.version,
        mission_id=contract.mission_id,
        judge_model_version=str(contract.raw["judge_model"]["version"]),
        dataset_version=str(contract.raw["golden_set"]["dataset_version"]),
        code_version=code_version,
        seeds=seeds,
        metrics=results,
        passed=ok,
    )
    if not ok:
        report.notes.append(
            f"failures blocking={blocking_failures} nonblocking={nonblocking_failures}"
        )
    return report
