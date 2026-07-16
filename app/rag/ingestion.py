"""RAG ingestion — curated/approved content only (never raw landing zone)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    doc_id: str
    dataset_version: str
    curation_stage: str
    text: str


ALLOWED_STAGES = frozenset({"approved", "active"})


def ingest_documents(docs: list[Document]) -> list[Document]:
    accepted: list[Document] = []
    for doc in docs:
        if doc.curation_stage not in ALLOWED_STAGES:
            raise ValueError(
                f"refusing non-curated document {doc.doc_id} stage={doc.curation_stage}"
            )
        accepted.append(doc)
    return accepted
