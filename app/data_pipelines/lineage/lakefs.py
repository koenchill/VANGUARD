"""lakeFS lineage hooks — resolve eval/model artifacts to exact dataset versions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LineageRef:
    dataset_version: str
    source_uri: str
    lakefs_commit_id: str
    parent_version: str | None = None


class LakeFSClient(Protocol):
    def commit(self, branch: str, message: str, metadata: dict[str, str]) -> str: ...

    def get_commit(self, commit_id: str) -> dict[str, str]: ...


class InMemoryLakeFS:
    """Local stand-in for lakeFS used in unit/integration tests."""

    def __init__(self) -> None:
        self._commits: dict[str, dict[str, str]] = {}
        self._counter = 0

    def commit(self, branch: str, message: str, metadata: dict[str, str]) -> str:
        self._counter += 1
        commit_id = f"lakefs-{branch}-{self._counter:04d}"
        self._commits[commit_id] = {
            "branch": branch,
            "message": message,
            **metadata,
        }
        return commit_id

    def get_commit(self, commit_id: str) -> dict[str, str]:
        if commit_id not in self._commits:
            raise KeyError(f"unknown lakeFS commit: {commit_id}")
        return dict(self._commits[commit_id])


def record_lineage(
    client: LakeFSClient,
    *,
    branch: str,
    dataset_version: str,
    source_uri: str,
    parent_version: str | None = None,
) -> LineageRef:
    commit_id = client.commit(
        branch=branch,
        message=f"curate {dataset_version}",
        metadata={
            "dataset_version": dataset_version,
            "source_uri": source_uri,
            "parent_version": parent_version or "",
        },
    )
    return LineageRef(
        dataset_version=dataset_version,
        source_uri=source_uri,
        lakefs_commit_id=commit_id,
        parent_version=parent_version,
    )


def resolve_version(client: LakeFSClient, lakefs_commit_id: str) -> LineageRef:
    meta = client.get_commit(lakefs_commit_id)
    return LineageRef(
        dataset_version=meta["dataset_version"],
        source_uri=meta["source_uri"],
        lakefs_commit_id=lakefs_commit_id,
        parent_version=meta.get("parent_version") or None,
    )
