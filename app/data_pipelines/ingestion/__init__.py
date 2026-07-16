"""Enterprise data ingestion — bulk and ongoing paths kept separate (Section 4)."""

from app.data_pipelines.ingestion.bulk import (
    DataSyncTaskConfig,
    SnowballJobConfig,
    run_bulk_onboarding,
    write_datasync_task_config,
    write_snowball_job_config,
)
from app.data_pipelines.ingestion.ongoing import (
    CdcStreamJob,
    IncrementalDataSyncJob,
    run_ongoing_sync,
    write_cdc_stream_job,
    write_incremental_datasync_job,
)
from app.data_pipelines.ingestion.types import TransferPath
from app.data_pipelines.ingestion.validation import (
    InMemoryObjectStore,
    validate_landing_batch,
)

__all__ = [
    "CdcStreamJob",
    "DataSyncTaskConfig",
    "InMemoryObjectStore",
    "IncrementalDataSyncJob",
    "SnowballJobConfig",
    "TransferPath",
    "run_bulk_onboarding",
    "run_ongoing_sync",
    "validate_landing_batch",
    "write_cdc_stream_job",
    "write_datasync_task_config",
    "write_incremental_datasync_job",
    "write_snowball_job_config",
]
