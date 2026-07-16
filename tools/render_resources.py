#!/usr/bin/env python3
"""Render Docker resource contracts into K8s and Karpenter fragments (G-007)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "PyYAML is required. Install with: pip install -r tests/requirements.txt"
    ) from exc

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "jsonschema is required. Install with: pip install -r tests/requirements.txt"
    ) from exc

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = REPO_ROOT / "infra" / "docker" / "resources" / "schema.json"
DEFAULT_RESOURCES_DIR = REPO_ROOT / "infra" / "docker" / "resources"


def load_schema(schema_path: Path) -> dict[str, Any]:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def load_contract(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Contract must be a mapping: {path}")
    return data


def validate_contract(contract: dict[str, Any], schema: dict[str, Any]) -> None:
    jsonschema.validate(instance=contract, schema=schema)
    if contract["gpu_count"] > 0 and not contract.get("gpu_type"):
        raise jsonschema.ValidationError(
            "gpu_type is required when gpu_count > 0"
        )
    if contract["gpu_count"] == 0 and contract.get("gpu_type") not in (None,):
        raise jsonschema.ValidationError(
            "gpu_type must be null when gpu_count == 0"
        )


def render_k8s_resources(contract: dict[str, Any]) -> str:
    resources: dict[str, Any] = {
        "requests": {
            "cpu": contract["cpu_request"],
            "memory": contract["memory_request"],
            "ephemeral-storage": contract["ephemeral_storage"],
        },
        "limits": {
            "cpu": contract["cpu_limit"],
            "memory": contract["memory_limit"],
            "ephemeral-storage": contract["ephemeral_storage"],
        },
    }
    if contract["gpu_count"] > 0:
        resources["limits"]["nvidia.com/gpu"] = str(contract["gpu_count"])
        resources["requests"]["nvidia.com/gpu"] = str(contract["gpu_count"])

    fragment = {"resources": resources}
    return yaml.safe_dump(fragment, sort_keys=False).rstrip() + "\n"


def render_karpenter_capacity(contract: dict[str, Any]) -> str:
    fragment: dict[str, Any] = {
        "karpenter_capacity_assumption": {
            "nodepool": contract["nodepool"],
            "architecture": contract["architecture"],
            "cpu": contract["cpu_limit"],
            "memory": contract["memory_limit"],
            "ephemeral_storage": contract["ephemeral_storage"],
            "gpu_count": contract["gpu_count"],
            "gpu_type": contract["gpu_type"],
            "workload": contract["workload"],
        }
    }
    return yaml.safe_dump(fragment, sort_keys=False).rstrip() + "\n"


def content_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_pair(
    contract_path: Path, schema: dict[str, Any]
) -> dict[str, Any]:
    contract = load_contract(contract_path)
    validate_contract(contract, schema)
    k8s = render_k8s_resources(contract)
    karpenter = render_karpenter_capacity(contract)
    return {
        "workload": contract["workload"],
        "source": str(contract_path.as_posix()),
        "k8s_resources_yaml": k8s,
        "karpenter_capacity_yaml": karpenter,
        "k8s_digest": content_digest(k8s),
        "karpenter_digest": content_digest(karpenter),
        "pair_digest": content_digest(k8s + "\n" + karpenter),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render VANGUARD Docker resource contracts (G-007)."
    )
    parser.add_argument(
        "contracts",
        nargs="*",
        type=Path,
        help="Path(s) to resources/*.yaml (default: all under infra/docker/resources)",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help="JSON Schema path",
    )
    parser.add_argument(
        "--resources-dir",
        type=Path,
        default=DEFAULT_RESOURCES_DIR,
        help="Directory of contract YAML files",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON summary (digests + fragments)",
    )
    args = parser.parse_args(argv)

    schema = load_schema(args.schema)
    paths = args.contracts
    if not paths:
        paths = sorted(args.resources_dir.glob("*.yaml"))

    if not paths:
        print("No resource contracts found.", file=sys.stderr)
        return 1

    results = []
    for path in paths:
        result = render_pair(path, schema)
        results.append(result)
        if not args.json:
            print(f"=== {result['workload']} ({path}) ===")
            print("--- k8s resources ---")
            print(result["k8s_resources_yaml"], end="")
            print(f"k8s_digest: {result['k8s_digest']}")
            print("--- karpenter capacity ---")
            print(result["karpenter_capacity_yaml"], end="")
            print(f"karpenter_digest: {result['karpenter_digest']}")
            print(f"pair_digest: {result['pair_digest']}")
            print()

    if args.json:
        json.dump(results, sys.stdout, indent=2)
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
