"""CI/CD gate checks for G-015 / G-019 (Phase 11).

- All third-party Actions must be pinned to a full 40-char commit SHA.
- DAST targets must be localhost (never production hostnames).
- Planted fixtures under security/sast-sca-dast/fixtures/planted/ must fail these checks.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
USES_RE = re.compile(r"^\s*-?\s*uses:\s*(.+)$", re.MULTILINE)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
LOCAL_OR_DOCKER = re.compile(r"^(\./|docker://)")

DEFAULT_BLOCKED = {
    "api.vanguard.prod",
    "gateway.vanguard.prod",
    "trino.prod.internal",
    "powerbi.microsoft.com",
}


def iter_workflow_uses(text: str) -> list[str]:
    refs: list[str] = []
    for match in USES_RE.finditer(text):
        raw = match.group(1).strip().strip("'\"")
        # Drop trailing comments
        raw = raw.split("#", 1)[0].strip()
        refs.append(raw)
    return refs


def assert_sha_pinned(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    for ref in iter_workflow_uses(text):
        if LOCAL_OR_DOCKER.match(ref):
            continue
        if "@" not in ref:
            errors.append(f"{path.name}: missing @ref in uses: {ref}")
            continue
        _, rev = ref.rsplit("@", 1)
        if not SHA_RE.match(rev):
            errors.append(f"{path.name}: Action not SHA-pinned: {ref}")
    return errors


def assert_dast_localhost(path: Path, blocked: set[str]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    # Extract target: lines near ZAP
    for line in text.splitlines():
        if "target:" in line.lower():
            lower = line.lower()
            if any(host.lower() in lower for host in blocked):
                errors.append(f"{path.name}: DAST target references blocked host: {line.strip()}")
            if "target:" in lower and "localhost" not in lower and "127.0.0.1" not in lower:
                # Allow comment-only lines
                if not line.strip().startswith("#"):
                    errors.append(
                        f"{path.name}: DAST target must be localhost (G-015): {line.strip()}"
                    )
    return errors


def verify_planted_fixtures() -> list[str]:
    """Planted bad examples must be rejected by the same validators."""
    planted = REPO / "security" / "sast-sca-dast" / "fixtures" / "planted"
    failures: list[str] = []
    unpinned = planted / "unpinned-action.yaml"
    bad_dast = planted / "unreachable-dast-target.yaml"
    vuln = planted / "hardcoded-credential.py"

    pin_errs = assert_sha_pinned(unpinned)
    if not pin_errs:
        failures.append("expected unpinned-action.yaml to fail SHA pin check")
    dast_errs = assert_dast_localhost(bad_dast, DEFAULT_BLOCKED)
    if not dast_errs:
        failures.append("expected unreachable-dast-target.yaml to fail localhost check")
    if "AKIA" not in vuln.read_text(encoding="utf-8") and "password" not in vuln.read_text(
        encoding="utf-8"
    ).lower():
        failures.append("planted hardcoded-credential.py missing obvious secret pattern")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflows", type=Path, default=None)
    parser.add_argument("--workflow", type=Path, default=None)
    parser.add_argument("--assert-dast-localhost", action="store_true")
    parser.add_argument("--blocked-hosts", default=",".join(sorted(DEFAULT_BLOCKED)))
    parser.add_argument("--verify-planted-fixtures", action="store_true")
    args = parser.parse_args(argv)

    errors: list[str] = []

    if args.verify_planted_fixtures:
        errors.extend(verify_planted_fixtures())

    workflow_files: list[Path] = []
    if args.workflows:
        workflow_files = sorted(Path(args.workflows).glob("*.y*ml"))
    if args.workflow:
        workflow_files.append(Path(args.workflow))

    blocked = {h.strip() for h in args.blocked_hosts.split(",") if h.strip()}

    for path in workflow_files:
        if "planted" in str(path):
            continue
        errors.extend(assert_sha_pinned(path))
        if args.assert_dast_localhost:
            errors.extend(assert_dast_localhost(path, blocked))

    if errors:
        print("CI/CD gate failures:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("CI/CD gates OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
