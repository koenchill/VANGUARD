# analytics/rls/

Build-side simulation of Trino/OPA row-level security used by both BI paths.
Production enforcement lives in the Trino OPA sidecar; this package proves the
§14 Phase 6 gate locally (two identities → different row counts, fail-closed).
