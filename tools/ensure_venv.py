#!/usr/bin/env python3
"""Create repo-local .venv (prefer Python 3.11) and install test requirements.

Prints the venv python path on stdout (last line) for wrappers to consume.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VENV = REPO / ".venv"
REQUIREMENTS = REPO / "tests" / "requirements.txt"


def venv_python(venv: Path = VENV) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _candidate_creators() -> list[list[str]]:
    """Prefer CI-aligned 3.11, then the interpreter running this script."""
    cands: list[list[str]] = []
    if os.name == "nt" and shutil.which("py"):
        cands.append(["py", "-3.11"])
    for name in ("python3.11", "python3", "python"):
        path = shutil.which(name)
        if path:
            cands.append([path])
    cands.append([sys.executable])
    # de-dupe
    seen: set[tuple[str, ...]] = set()
    out: list[list[str]] = []
    for cmd in cands:
        key = tuple(cmd)
        if key not in seen:
            seen.add(key)
            out.append(cmd)
    return out


def _python_version(cmd: list[str]) -> tuple[int, int] | None:
    try:
        proc = subprocess.run(
            [*cmd, "-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return None
        major, minor = proc.stdout.strip().split(".", 1)
        return int(major), int(minor)
    except (OSError, ValueError):
        return None


def create_venv(*, force: bool = False) -> Path:
    py = venv_python()
    if py.is_file() and not force:
        return py

    if force and VENV.exists():
        shutil.rmtree(VENV)

    last_err = ""
    for base in _candidate_creators():
        ver = _python_version(base)
        if ver is None:
            continue
        # Prefer 3.11+; allow 3.12/3.13 if 3.11 missing. Reject <3.11 for portfolio gates.
        if ver < (3, 11):
            last_err = f"{base} is Python {ver[0]}.{ver[1]} (<3.11)"
            continue
        print(f"# ensure-venv: creating {VENV} with {' '.join(base)} (Python {ver[0]}.{ver[1]})", file=sys.stderr)
        proc = subprocess.run([*base, "-m", "venv", str(VENV)], cwd=REPO)
        if proc.returncode == 0 and venv_python().is_file():
            return venv_python()
        last_err = f"{' '.join(base)} -m venv failed rc={proc.returncode}"

    raise SystemExit(
        "Could not create .venv with Python >=3.11. "
        f"Install Python 3.11+ and retry. Last error: {last_err}"
    )


def install_requirements(py: Path) -> None:
    print(f"# ensure-venv: installing {REQUIREMENTS.relative_to(REPO)} into .venv", file=sys.stderr)
    subprocess.run(
        [str(py), "-m", "pip", "install", "-q", "--upgrade", "pip"],
        cwd=REPO,
        check=True,
    )
    subprocess.run(
        [str(py), "-m", "pip", "install", "-q", "-r", str(REQUIREMENTS)],
        cwd=REPO,
        check=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Recreate .venv from scratch")
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Only ensure the venv exists (no pip install)",
    )
    args = parser.parse_args(argv)

    py = create_venv(force=args.force)
    if not args.skip_install:
        install_requirements(py)
    # Wrappers parse the last line as the interpreter path.
    print(py.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
