#!/usr/bin/env python3
"""Mimic production-like Local evidence against VANGUARD (G-001 portfolio).

Stages (skip with --skip-*):
  0 deps          — pip install tests/requirements.txt
  1 pyramid-core  — unit + integration (same gates as CI)
  2 gateway       — build/run gateway image; probe /readyz /healthz /openapi.json
  3 security      — CI pin/DAST host gates + live security-header probes
  4 load          — optional k6 against the live gateway + G-011 report bind
  5 resilience    — chaos HITL + G-018 audit + G-010 agent-eval
  6 prod-sim      — staging mission-alpha production-simulation gate
  7 walkthrough   — optional full Section 14 Local report regen

This is Local/portfolio mimicry — not Cloud-Integration or ATO evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "docs" / "validation"
REPORT_JSON = OUT_DIR / "mimic-prod-report.json"
REPORT_MD = OUT_DIR / "mimic-prod-report.md"
GATEWAY_IMAGE = "local/vanguard-gateway:mimic-prod"
GATEWAY_NAME = "vanguard-mimic-prod"
GATEWAY_PORT = int(os.getenv("VANGUARD_GATEWAY_PORT", "8000"))
K6_SUMMARY = REPO / "tests" / "load" / "reports" / "k6-summary-mimic.json"


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    return env


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    check: bool = False,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd or REPO,
        env=_env(),
        text=True,
        capture_output=capture,
        check=check,
    )


def _which(name: str) -> str | None:
    return shutil.which(name)


def _http_get(url: str, timeout: float = 5.0) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        headers = {k.lower(): v for k, v in resp.headers.items()}
        return resp.status, headers, resp.read()


def _wait_ready(url: str, attempts: int = 30, delay: float = 2.0) -> bool:
    for _ in range(attempts):
        try:
            status, _, _ = _http_get(url, timeout=3.0)
            if status == 200:
                return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(delay)
    return False


class StageResult(dict):
    @staticmethod
    def make(name: str, *, passed: bool, detail: str = "", skipped: bool = False) -> dict:
        return {
            "stage": name,
            "passed": passed,
            "skipped": skipped,
            "detail": detail,
        }


def stage_deps() -> dict:
    req = REPO / "tests" / "requirements.txt"
    proc = _run([sys.executable, "-m", "pip", "install", "-q", "-r", str(req)])
    ok = proc.returncode == 0
    return StageResult.make(
        "deps",
        passed=ok,
        detail=(
            f"pip install -r tests/requirements.txt into {sys.executable}"
            + ("" if ok else f" rc={proc.returncode}")
        ),
    )


def stage_pyramid_core() -> dict:
    proc = _run(
        [sys.executable, "-m", "pytest", "tests/unit", "tests/integration", "-q", "--tb=line"]
    )
    tail = (proc.stdout or "").strip().splitlines()[-1:] or [(proc.stderr or "").strip()[:200]]
    return StageResult.make(
        "pyramid-core",
        passed=proc.returncode == 0,
        detail=tail[0] if tail else f"rc={proc.returncode}",
    )


def _gateway_cleanup() -> None:
    _run(["docker", "rm", "-f", GATEWAY_NAME], capture=True)


def stage_gateway(*, skip: bool) -> dict:
    if skip:
        return StageResult.make("gateway", passed=True, skipped=True, detail="--skip-gateway")
    if not _which("docker"):
        return StageResult.make(
            "gateway",
            passed=False,
            detail="docker not on PATH (use --skip-gateway to omit live smoke)",
        )

    _gateway_cleanup()
    build = _run(
        [
            "docker",
            "build",
            "-t",
            GATEWAY_IMAGE,
            "-f",
            "infra/docker/gateway.Dockerfile",
            ".",
        ]
    )
    if build.returncode != 0:
        err = (build.stderr or build.stdout or "")[-500:]
        return StageResult.make("gateway", passed=False, detail=f"docker build failed: {err}")

    run = _run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            GATEWAY_NAME,
            "-p",
            f"{GATEWAY_PORT}:8000",
            "-e",
            "AUTH_MODE=test-only",
            "-e",
            "API_KEY=dast-test-only",
            "-e",
            "VANGUARD_WORKLOAD=gateway",
            GATEWAY_IMAGE,
        ]
    )
    if run.returncode != 0:
        return StageResult.make(
            "gateway",
            passed=False,
            detail=f"docker run failed: {(run.stderr or run.stdout or '')[-300:]}",
        )

    base = f"http://127.0.0.1:{GATEWAY_PORT}"
    if not _wait_ready(f"{base}/readyz"):
        logs = _run(["docker", "logs", GATEWAY_NAME])
        return StageResult.make(
            "gateway",
            passed=False,
            detail=f"/readyz not ready; logs={(logs.stdout or logs.stderr or '')[-400:]}",
        )

    failures: list[str] = []
    for path in ("/readyz", "/healthz", "/openapi.json"):
        try:
            status, headers, _ = _http_get(f"{base}{path}")
            if status != 200:
                failures.append(f"{path} status={status}")
            if headers.get("x-content-type-options", "").lower() != "nosniff":
                failures.append(f"{path} missing X-Content-Type-Options")
            if headers.get("cross-origin-resource-policy", "").lower() != "same-origin":
                failures.append(f"{path} missing Cross-Origin-Resource-Policy")
        except Exception as exc:  # noqa: BLE001 — surface probe errors in report
            failures.append(f"{path} error={exc}")

    if failures:
        return StageResult.make("gateway", passed=False, detail="; ".join(failures))
    return StageResult.make(
        "gateway",
        passed=True,
        detail=f"image={GATEWAY_IMAGE} probes ok on :{GATEWAY_PORT}",
    )


def stage_security(*, gateway_up: bool) -> dict:
    proc = _run(
        [
            sys.executable,
            "tools/check_cicd_gates.py",
            "--workflows",
            ".github/workflows",
        ]
    )
    parts = [f"cicd_gates rc={proc.returncode}"]
    ok = proc.returncode == 0

    dast = _run(
        [
            sys.executable,
            "tools/check_cicd_gates.py",
            "--assert-dast-localhost",
            "--workflow",
            ".github/workflows/ci-cd-pipeline.yaml",
            "--blocked-hosts",
            "api.vanguard.prod,gateway.vanguard.prod,trino.prod.internal,powerbi.microsoft.com",
        ]
    )
    parts.append(f"dast_localhost rc={dast.returncode}")
    ok = ok and dast.returncode == 0

    if gateway_up:
        try:
            status, headers, _ = _http_get(f"http://127.0.0.1:{GATEWAY_PORT}/readyz")
            hdr_ok = (
                status == 200
                and headers.get("x-content-type-options", "").lower() == "nosniff"
                and headers.get("cross-origin-resource-policy", "").lower() == "same-origin"
            )
            parts.append("live_headers=" + ("ok" if hdr_ok else "FAIL"))
            ok = ok and hdr_ok
        except Exception as exc:  # noqa: BLE001
            parts.append(f"live_headers error={exc}")
            ok = False
    else:
        parts.append("live_headers=skipped")

    return StageResult.make("security", passed=ok, detail="; ".join(parts))


def stage_load(*, skip: bool, quick: bool, gateway_up: bool) -> dict:
    if skip:
        return StageResult.make("load", passed=True, skipped=True, detail="--skip-k6")
    if not gateway_up:
        return StageResult.make(
            "load",
            passed=True,
            skipped=True,
            detail="gateway not running; bound synthetic G-011 report only",
        )

    code_version = f"mimic-{_git_short()}"
    if not _which("k6"):
        bind = _run(
            [
                sys.executable,
                "tools/link_load_report.py",
                "--code-version",
                code_version,
            ]
        )
        return StageResult.make(
            "load",
            passed=bind.returncode == 0,
            skipped=True,
            detail="k6 not on PATH; linked report without live metrics (Local-degraded)",
        )

    vus = "5" if quick else "20"
    duration = "30s" if quick else "2m"
    K6_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    k6 = _run(
        [
            "k6",
            "run",
            "-e",
            f"GATEWAY_URL=http://127.0.0.1:{GATEWAY_PORT}",
            "-e",
            f"VUS={vus}",
            "-e",
            f"DURATION={duration}",
            "--summary-export",
            str(K6_SUMMARY),
            "tests/load/k6/marts_workload.js",
        ]
    )
    bind = _run(
        [
            sys.executable,
            "tools/link_load_report.py",
            "--code-version",
            code_version,
            "--k6-summary",
            str(K6_SUMMARY),
        ]
    )
    ok = k6.returncode == 0 and bind.returncode == 0
    return StageResult.make(
        "load",
        passed=ok,
        detail=f"k6 rc={k6.returncode} bind rc={bind.returncode} vus={vus} duration={duration}",
    )


def stage_resilience(*, skip: bool = False) -> dict:
    if skip:
        return StageResult.make("resilience", passed=True, skipped=True, detail="--skip-resilience")
    proc = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/chaos",
            "tests/security",
            "tests/agent-eval",
            "-q",
            "--tb=line",
        ]
    )
    tail = (proc.stdout or "").strip().splitlines()[-1:] or [""]
    return StageResult.make(
        "resilience",
        passed=proc.returncode == 0,
        detail=tail[0] if tail else f"rc={proc.returncode}",
    )


def stage_prod_sim(*, skip: bool = False) -> dict:
    if skip:
        return StageResult.make("prod-sim", passed=True, skipped=True, detail="--skip-prod-sim")
    proc = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/production-simulation",
            "-q",
            "--tb=line",
        ]
    )
    tail = (proc.stdout or "").strip().splitlines()[-1:] or [""]
    return StageResult.make(
        "prod-sim",
        passed=proc.returncode == 0,
        detail=tail[0] if tail else f"rc={proc.returncode}",
    )


def stage_walkthrough(*, skip: bool) -> dict:
    if skip:
        return StageResult.make("walkthrough", passed=True, skipped=True, detail="--skip-walkthrough")
    proc = _run([sys.executable, "tools/run_section14_walkthrough.py"])
    return StageResult.make(
        "walkthrough",
        passed=proc.returncode == 0,
        detail=(proc.stdout or "").strip()[-300:] or f"rc={proc.returncode}",
    )


def _git_short() -> str:
    proc = _run(["git", "rev-parse", "--short", "HEAD"])
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    return "unknown"


def _write_reports(results: list[dict], *, overall: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "assurance_boundary": "G-001 portfolio Local mimic-prod — not Cloud-Integration / not ATO",
        "code_version": _git_short(),
        "overall_passed": overall,
        "stages": results,
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Mimic-Prod Report (Local)",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Code: `{report['code_version']}`",
        "",
        f"**Overall:** {'PASS' if overall else 'FAIL'} — Local evidence only (G-001).",
        "",
        "| Stage | Result | Detail |",
        "|-------|--------|--------|",
    ]
    for r in results:
        if r.get("skipped"):
            mark = "SKIP"
        else:
            mark = "PASS" if r["passed"] else "FAIL"
        detail = str(r.get("detail", "")).replace("|", "\\|")
        lines.append(f"| `{r['stage']}` | {mark} | {detail} |")
    lines.extend(
        [
            "",
            "## How to re-run",
            "",
            "```bash",
            "./scripts/ensure-venv.sh   # or .\\scripts\\ensure-venv.ps1",
            "./scripts/mimic-prod.sh",
            "```",
            "",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-deps", action="store_true")
    parser.add_argument("--skip-gateway", action="store_true", help="Skip Docker gateway smoke")
    parser.add_argument("--skip-k6", action="store_true", help="Skip live k6 load stage")
    parser.add_argument("--skip-resilience", action="store_true", help="Skip chaos/security/eval")
    parser.add_argument("--skip-prod-sim", action="store_true", help="Skip production-simulation")
    parser.add_argument("--skip-walkthrough", action="store_true", help="Skip Section 14 regen")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Shorter k6 profile (5 VUs / 30s hold)",
    )
    parser.add_argument(
        "--keep-gateway",
        action="store_true",
        help="Leave gateway container running after the run",
    )
    args = parser.parse_args(argv)

    results: list[dict] = []
    gateway_up = False

    try:
        if not args.skip_deps:
            results.append(stage_deps())
            if not results[-1]["passed"]:
                _write_reports(results, overall=False)
                print(json.dumps({"overall_passed": False, "report": str(REPORT_JSON)}))
                return 1
        else:
            results.append(StageResult.make("deps", passed=True, skipped=True, detail="--skip-deps"))

        results.append(stage_pyramid_core())
        if not results[-1]["passed"]:
            _write_reports(results, overall=False)
            print(json.dumps({"overall_passed": False, "report": str(REPORT_JSON)}))
            return 1

        gw = stage_gateway(skip=args.skip_gateway)
        results.append(gw)
        gateway_up = gw["passed"] and not gw.get("skipped")
        if not gw["passed"] and not gw.get("skipped"):
            _write_reports(results, overall=False)
            print(json.dumps({"overall_passed": False, "report": str(REPORT_JSON)}))
            return 1

        results.append(stage_security(gateway_up=gateway_up))
        results.append(stage_load(skip=args.skip_k6, quick=args.quick, gateway_up=gateway_up))
        results.append(stage_resilience(skip=args.skip_resilience))
        results.append(stage_prod_sim(skip=args.skip_prod_sim))
        results.append(stage_walkthrough(skip=args.skip_walkthrough))

        overall = all(r["passed"] for r in results)
        _write_reports(results, overall=overall)
        print(json.dumps({"overall_passed": overall, "report": str(REPORT_JSON)}, indent=2))
        return 0 if overall else 1
    finally:
        if gateway_up and not args.keep_gateway and _which("docker"):
            _gateway_cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
