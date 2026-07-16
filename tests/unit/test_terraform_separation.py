"""Tests for Terraform separation CI gate and BI mode conditional."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CHECK = REPO / "tools" / "check_terraform_separation.py"
PROD_MAIN = REPO / "infra" / "terraform" / "environments" / "prod" / "main.tf"
APP = REPO / "infra" / "terraform" / "app"


def test_separation_check_passes_on_clean_tree() -> None:
    proc = subprocess.run([sys.executable, str(CHECK)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_separation_check_fails_on_tf_in_app(tmp_path: Path, monkeypatch) -> None:
    # Run check against repo; temporarily create a forbidden file then remove.
    rogue = APP / "rogue.tf"
    try:
        rogue.write_text('resource "null_resource" "x" {}\n', encoding="utf-8")
        proc = subprocess.run([sys.executable, str(CHECK)], capture_output=True, text=True)
        assert proc.returncode != 0
        assert "rogue.tf" in proc.stdout
    finally:
        if rogue.exists():
            rogue.unlink()


def test_powerbi_gateway_enabled_conditional_in_main() -> None:
    text = PROD_MAIN.read_text(encoding="utf-8")
    assert 'enabled               = var.bi_deployment_mode == "hybrid"' in text


def test_tfvars_keys_cover_main_var_references() -> None:
    main = PROD_MAIN.read_text(encoding="utf-8")
    # Collect var.X references from main (simple scan).
    import re

    refs = set(re.findall(r"var\.([a-zA-Z0-9_]+)", main))
    # Also scan variables used only in other root files via providers
    providers = (REPO / "infra/terraform/environments/prod/providers.tf").read_text(encoding="utf-8")
    refs |= set(re.findall(r"var\.([a-zA-Z0-9_]+)", providers))

    prod = json.loads((APP / "prod.tfvars.json").read_text(encoding="utf-8"))
    dev = json.loads((APP / "dev.tfvars.json").read_text(encoding="utf-8"))

    missing_prod = sorted(r for r in refs if r not in prod)
    missing_dev = sorted(r for r in refs if r not in dev)
    assert not missing_prod, f"prod.tfvars.json missing keys used in main/providers: {missing_prod}"
    assert not missing_dev, f"dev.tfvars.json missing keys used in main/providers: {missing_dev}"


def test_all_section7_modules_wired() -> None:
    text = PROD_MAIN.read_text(encoding="utf-8")
    for name in (
        "vpc",
        "eks",
        "karpenter",
        "storage",
        "metadata_db",
        "trino_query_engine",
        "powerbi_gateway_cluster",
        "data_transfer",
        "backup_dr",
        "observability",
    ):
        assert f'module "{name}"' in text, f"missing module {name}"
