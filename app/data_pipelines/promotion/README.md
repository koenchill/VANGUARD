# app/data_pipelines/promotion/

Staged promotion controller (G-014): stage non-active candidates, validate quality/lineage,
atomically flip `active_dataset_pointer`, compensate/orphan on failure. Consumers resolve
versions only through the active pointer.
