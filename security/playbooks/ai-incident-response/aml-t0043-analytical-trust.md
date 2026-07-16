# Playbook — Exploiting Analytical Trust (ATLAS AML.T0043)

**Mapped resources (this build):**
- Detection: `analytics/grafana/dashboards/data_quality_drift.json`,
  `analytics/powerbi/data_quality_drift.pbix.json`,
  `app/data_pipelines/db/models.py` (`quality_score`, lineage)
- Containment: mark mart rows / panels unverified in Mission BI folders
- Rollback: `app/data_pipelines/lineage/`, `app/data_pipelines/promotion/`, `backup-dr/`
- Structural mitigation: dashboards must show provenance + confidence (Section 5)

## 1. Detection
Dashboard-layer anomaly: a `quality_score` or lineage chain that does not reconcile
against the curation metadata DB audit trail, or a confidence interval outside the
range the eval harness would produce for that data class.

## 2. Containment
Flag the affected Mission BI panel and underlying `sql/marts/reporting/` rows as
**unverified**. The BI layer must display this state — not only the numeric metric
(`analytics/bi_metrics.yaml` provenance expectation).

## 3. Triage & Rollback
Trace poisoned records through lakeFS lineage to the curation run / `dataset_version`,
then roll back per the backup/restore process. Flip `active_dataset_pointer` only after
validation (G-014).

## 4. Structural mitigation
Every Mission BI dashboard displays data provenance and agent confidence alongside the
metric so decision-makers can see low-confidence or unverified curation output.

**Owner:** Mission BI + Data Engineering  
**Assurance:** Design + Local (RLS/provenance artifacts); live falsified-score drill is Cloud-Integration.
