# Playbook — RAG / Training-Data Poisoning (ATLAS AML.T0044)

**Mapped resources:** `app/rag/ingestion.py`, `app/data_pipelines/ingestion/validation.py`,
landing quarantine prefix.

## Detection
Ingest attempt with `curation_stage` not in `{approved, active}`, or landing checksum
mismatch.

## Containment
Reject ingest; quarantine objects under `landing/quarantine/`; block promotion.

## Triage & Rollback
Identify source batch via `TransferBatch.batch_id` / `dataset_version`; restore prior
vector snapshot if index already polluted.

**Owner:** Data Engineering
