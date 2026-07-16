# app/data_pipelines/ingestion/

Enterprise onboarding (Section 4): **bulk** (`bulk.py` + DataSync/Snowball configs) and
**ongoing** (`ongoing.py` + incremental DataSync/CDC configs) are separate code paths.
Both land only under `landing/raw/`, pass through shared checksum/count validation, and
quarantine failures — never write bronze/silver/gold directly.
