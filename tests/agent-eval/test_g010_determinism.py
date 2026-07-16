"""G-010 agent-eval — deterministic pass/fail against versioned contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.evaluation.harness import ContractError, load_contract, run_eval

REPO = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_positive_fixtures_pass_deterministically() -> None:
    contract = load_contract("mission-alpha")
    r1 = run_eval(contract, code_version="dev-test", repo=REPO)
    r2 = run_eval(contract, code_version="dev-test", repo=REPO)
    assert r1.passed is True
    assert r2.passed is True
    assert r1.to_dict()["metrics"] == r2.to_dict()["metrics"]
    assert r1.contract_identity == r2.contract_identity
    assert r1.seeds == [101, 102, 103, 104, 105]


def test_negative_fixtures_fail_blocking_metrics() -> None:
    contract = load_contract("mission-alpha")
    negatives = _load_jsonl(FIXTURES / "mission-alpha-negative.jsonl")
    report = run_eval(
        contract,
        code_version="dev-test",
        repo=REPO,
        fixture_override=negatives,
    )
    assert report.passed is False
    blocking_failed = [m for m in report.metrics if m.blocking and not m.passed]
    assert blocking_failed


def test_contract_change_changes_identity() -> None:
    contract = load_contract("mission-alpha")
    before = contract.identity
    bumped = dict(contract.raw)
    bumped["contract_version"] = "1.0.1"
    bumped["metrics"] = dict(bumped["metrics"])
    bumped["metrics"]["faithfulness"] = dict(bumped["metrics"]["faithfulness"])
    bumped["metrics"]["faithfulness"]["threshold"] = 0.99
    from app.evaluation.harness import EvalContract

    other = EvalContract(raw=bumped, path=contract.path)
    assert other.identity != before
    assert other.raw["rerun_policy"]["invalidate_prior_results_on_contract_change"] is True


def test_mission_bravo_contract_loads_and_passes() -> None:
    contract = load_contract("mission-bravo")
    report = run_eval(contract, code_version="dev-test", repo=REPO)
    assert report.passed is True
    assert report.judge_model_version == "2026.07.1"


def test_undersized_golden_set_rejected(tmp_path: Path) -> None:
    contract = load_contract("mission-alpha")
    tiny = [{"id": "x", "label": "positive", "metrics": {"faithfulness": 1.0, "answer_relevancy": 1.0, "hallucination_rate": 0.0, "task_completion": 1.0}}]
    # Bypass file min check by override — contract still requires min via load_golden_set;
    # ensure load_golden_set enforces when reading a short file.
    short = tmp_path / "short.jsonl"
    short.write_text(json.dumps(tiny[0]) + "\n", encoding="utf-8")
    mutated = dict(contract.raw)
    mutated["golden_set"] = dict(mutated["golden_set"])
    mutated["golden_set"]["path"] = str(short.relative_to(tmp_path))
    from app.evaluation.harness import EvalContract, load_golden_set

    c = EvalContract(raw=mutated, path=contract.path)
    with pytest.raises(ContractError):
        load_golden_set(c, repo=tmp_path)
