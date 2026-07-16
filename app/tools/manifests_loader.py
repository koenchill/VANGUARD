"""Standalone tool permission manifests consumed by agents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

MANIFEST_DIR = Path(__file__).parent / "manifests"


def load_manifests(directory: Path | None = None) -> dict[str, dict[str, Any]]:
    root = directory or MANIFEST_DIR
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(root.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        out[data["tool_name"]] = data
    return out
