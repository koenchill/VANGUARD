#!/usr/bin/env python3
"""CI gate: Terraform structure/config separation (Section 7 / G-009)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP_DIR = REPO / "infra" / "terraform" / "app"
MODULES_DIR = REPO / "infra" / "terraform" / "modules"

# Environment-specific patterns that must not appear as bare literals in modules.
FORBIDDEN_IN_MODULES = [
    (re.compile(r'"10\.\d+\.\d+\.\d+/\d+"'), "hardcoded CIDR"),
    (re.compile(r'"us-gov-(west|east)-\d+"'), "hardcoded region"),
    (re.compile(r'"[mgcrp]\d+[a-z]?\.(nano|micro|small|medium|large|xlarge|2xlarge|4xlarge|24xlarge)"'), "hardcoded instance type"),
    (re.compile(r'"db\.[a-z0-9]+\.[a-z0-9]+"'), "hardcoded DB instance class"),
]


def main() -> int:
    errors: list[str] = []

    if not APP_DIR.is_dir():
        errors.append(f"missing {APP_DIR}")
    else:
        tf_files = list(APP_DIR.rglob("*.tf"))
        if tf_files:
            for path in tf_files:
                errors.append(f".tf file forbidden under infra/terraform/app/: {path.relative_to(REPO)}")
        allowed = {"dev.tfvars.json", "prod.tfvars.json", "README.md"}
        for path in APP_DIR.iterdir():
            if path.name.startswith("."):
                continue
            if path.name not in allowed:
                errors.append(
                    f"unexpected file in infra/terraform/app/ (only tfvars JSON + README allowed): {path.name}"
                )

    for tf_path in MODULES_DIR.rglob("*.tf"):
        text = tf_path.read_text(encoding="utf-8")
        for pattern, label in FORBIDDEN_IN_MODULES:
            if pattern.search(text):
                errors.append(f"{label} in {tf_path.relative_to(REPO)}")

    if errors:
        print("Terraform separation check FAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("Terraform separation check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
