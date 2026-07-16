"""Map and execute Section 14 walkthrough phases against Local evidence suites."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "docs" / "validation"

# Section 14 walkthrough phases → Local pytest paths that constitute evidence.
WALKTHROUGH = [
    {
        "phase": 0,
        "name": "Agent constraints / repo consistency",
        "suites": ["tests/unit/test_terraform_separation.py"],
        "notes": "tfvars-only under infra/terraform/app/; baseline separations",
    },
    {
        "phase": 1,
        "name": "Scaffolding / resource contracts",
        "suites": ["tests/unit/test_render_resources.py"],
        "notes": "G-007 renderer + digest SSOT",
    },
    {
        "phase": 2,
        "name": "Infra plan / BI mode / K8s contracts",
        "suites": ["tests/unit/test_k8s_manifests.py", "tests/unit/test_terraform_separation.py"],
        "notes": "NodePools exclusive; no PowerBI in K8s; oauthPassThru",
    },
    {
        "phase": 3,
        "name": "K8s scheduling / hardening fixtures",
        "suites": ["tests/unit/test_phase10_security_artifacts.py"],
        "notes": "Kyverno/OPA/RuntimeClass artifacts; STRIDE present",
    },
    {
        "phase": 4,
        "name": "Enterprise ingestion",
        "suites": ["tests/integration/test_enterprise_ingestion.py"],
        "notes": "Bulk vs ongoing; quarantine gate",
    },
    {
        "phase": 5,
        "name": "Data & metadata / promotion",
        "suites": [
            "tests/integration/test_promotion_controller.py",
            "tests/unit/test_explain_full_scan.py",
        ],
        "notes": "G-014 atomic promotion fault-injection; EXPLAIN CI gate",
    },
    {
        "phase": 6,
        "name": "BI connectivity (build-side)",
        "suites": ["tests/integration/test_bi_dual_path.py"],
        "notes": "Four dashboards × 2 paths; RLS distinct counts",
    },
    {
        "phase": 7,
        "name": "Backup/DR restore drill (Local)",
        "suites": ["tests/integration/test_g006_recovery_manifest.py"],
        "notes": "G-006 stale-manifest rejection",
    },
    {
        "phase": 8,
        "name": "Security pipeline dry-run (Local)",
        "suites": ["tests/unit/test_phase11_cicd_gates.py"],
        "notes": "G-015/G-019 planted fixtures caught; SHA pins",
    },
    {
        "phase": 9,
        "name": "STRIDE/ATLAS + G-013 + audit drills",
        "suites": [
            "tests/unit/test_g013_approval_protocol.py",
            "tests/unit/test_phase9_agent_stack.py",
            "tests/security/test_g018_audit_drills.py",
        ],
        "notes": "G-013 fail-closed; G-018 tamper/deletion/replay",
    },
    {
        "phase": 10,
        "name": "Production simulation smoke",
        "suites": ["tests/production-simulation/test_mission_alpha_staging.py"],
        "notes": "Staging scenario Local runner",
    },
    {
        "phase": 11,
        "name": "Go/No-Go inputs (eval + load + chaos)",
        "suites": [
            "tests/agent-eval/test_g010_determinism.py",
            "tests/load/test_workload_manifest.py",
            "tests/chaos/test_hitl_fallback.py",
        ],
        "notes": "G-010/G-011 Local contracts; chaos HITL",
    },
]


def run_phase(phase: dict) -> dict:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *phase["suites"],
        "-q",
        "--tb=no",
    ]
    proc = subprocess.run(
        cmd,
        cwd=REPO,
        capture_output=True,
        text=True,
        env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(REPO)},
    )
    passed = proc.returncode == 0
    return {
        "phase": phase["phase"],
        "name": phase["name"],
        "suites": phase["suites"],
        "notes": phase["notes"],
        "passed": passed,
        "returncode": proc.returncode,
        "summary": (proc.stdout or "").strip().splitlines()[-1] if proc.stdout else "",
        "stderr_tail": (proc.stderr or "").strip().splitlines()[-5:],
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = [run_phase(p) for p in WALKTHROUGH]
    all_passed = all(r["passed"] for r in results)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "assurance_boundary": "G-001 portfolio Local evidence — not ATO",
        "all_phases_passed": all_passed,
        "phases": results,
    }
    out = OUT_DIR / "section14-walkthrough-report.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Section 14 Walkthrough Report (Local)",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"**Overall:** {'PASS' if all_passed else 'FAIL'} — Local evidence only (G-001).",
        "",
        "| Phase | Name | Result | Suites |",
        "|------:|------|--------|--------|",
    ]
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        suites = "<br>".join(f"`{s}`" for s in r["suites"])
        lines.append(f"| {r['phase']} | {r['name']} | {mark} | {suites} |")
    lines.append("")
    (OUT_DIR / "section14-walkthrough-report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"all_phases_passed": all_passed, "report": str(out)}))
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
