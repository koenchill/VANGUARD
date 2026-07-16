"""Chunking for curated corpus before embedding."""

from __future__ import annotations

from dataclasses import dataclass

from app.rag.ingestion import Document


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    dataset_version: str
    text: str
    ordinal: int


def chunk_document(doc: Document, *, max_chars: int = 500, overlap: int = 50) -> list[Chunk]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    text = doc.text.strip()
    if not text:
        return []
    chunks: list[Chunk] = []
    start = 0
    ordinal = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        piece = text[start:end]
        chunks.append(
            Chunk(
                chunk_id=f"{doc.doc_id}:{ordinal}",
                doc_id=doc.doc_id,
                dataset_version=doc.dataset_version,
                text=piece,
                ordinal=ordinal,
            )
        )
        if end == len(text):
            break
        start = max(0, end - overlap)
        ordinal += 1
    return chunks
