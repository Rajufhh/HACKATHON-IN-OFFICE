# Synthetic Academic Integrity Dataset

This dataset is generated locally by `scripts/generate_synthetic_data.py`.
Every name, email, content hash, match source, and evidence reference is
synthetic. Email addresses use the reserved `example.invalid` domain. No
external data or real learner work is used.

## Reproduce

From `backend`:

```powershell
python scripts\generate_synthetic_data.py --seed 20261022 --submissions 10000 --flags 1000 --cases 300 --out generated_data
python scripts\generate_synthetic_data.py --seed 20261022 --submissions 10000 --flags 1000 --cases 300 --verify-reproducible
```

Default full scale is 10,000 submissions, 1,000 threshold-triggered flags, and
300 cases. Smaller scale arguments use the same generator and rule logic.

## Contents

- One CSV per relational table, plus `data.json` and MySQL `seed.sql`.
- `ground_truth.csv` and `ground_truth.json` are separate evaluation labels;
  they are deliberately excluded from `data.json`, CSV input tables, and SQL.
- `data_dictionary.json` defines core entity fields, types, nullability,
  uniqueness, validation, cardinalities, lifecycle states, and effective-date
  limits of the current application model.
- `source_manifest.json` records generator version, seed, parameters, counts,
  and SHA-256 checksums.
- `validation_summary.json` reports reconciliation metrics and expected,
  explicitly labelled edge-case anomalies.

## Domain generation rules

Scores are derived from the three synthetic match components, which reconcile
to the report score. Scores 0-39 map to `INFORMATION`, 40-69 to `REVIEW`, and
70-100 to `PRIORITY_REVIEW`; only the latter two create flags. A flag is never
itself a misconduct finding. Human decision labels are generated from the
synthetic source profile and score using the documented rule in the generator;
legitimate quotation/template overlap is labelled separately and can be
appealed successfully when the synthetic reviewer makes a false-positive
decision.

The four intentionally injected issues are recorded in `ground_truth`:
`FLAG_TREATED_AS_GUILT`, `REVIEWER_CONFLICT`,
`EVIDENCE_AFTER_DECISION_WITHOUT_HISTORY`, and
`APPEAL_CLOSED_WITHOUT_INDEPENDENT_REVIEW`. They are detectable anomalies,
not silently mixed into ordinary rows.

## Relational notes

Primary keys are deterministic integers within each table. Business codes are
stable and zero-padded. Foreign keys are explicit. `case_flags` links cases and
flags; `decision_evidence` and `appeal_evidence` link existing evidence to
decision/appeal snapshots. Case and appeal event tables retain lifecycle
history. Appeals are one per decision in this data model. See
`data_dictionary.json` for entity cardinalities and effective-time details.

## Seed loading

`seed.sql` assumes the matching application tables already exist and that the
target database is empty. Load it only into a dedicated test or analytics
database. It is not a schema migration and must not be run against production.
