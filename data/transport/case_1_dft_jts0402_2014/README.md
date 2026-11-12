# JTS0402 (2014) — OP7 + OP2 public example

**Source:** UK Department for Transport, *Journey Time Statistics: access to services 2014*, JTS0402 (primary schools), England. Source family `DfT_JTS0402_2014`. The original source worksheet is supplied as `input.xlsx`; `gold_output.xlsx` represents the requested transformation.

**Operations:** OP7 (reconstruct three-level semantic column headers and contiguous Region groupings), OP2 (derive a signed travel-time-gap column). One input sheet, one output sheet; 361 records, 31 unchanged original fields plus one numeric difference column. Source field IDs and short codes are retained in Excel header comments and `field_mapping.json`.

**Derived metric:** `PSPTt - PSCart`, minutes: area-level mean minimum journey time for public transport/walking minus car, *not* a household-level before/after comparison. Preserve negative results and source percentage-point values.

**Reproducibility:** `python build_gold.py` rebuilds Gold from `input.xlsx`. `python evaluate.py gold_output.xlsx` performs independent source-grounded checks. `python test_case.py` tests rejection of deliberate corruption. Gold/evaluator/mapping must not be exposed to an agent in the benchmark environment; give only `input.xlsx` and English `instruction.txt`.

**Source attribution:** Contains public sector information from UK Department for Transport, *Journey Time Statistics: access to services 2014*, licensed under the Open Government Licence v3.0 except where otherwise stated. The benchmark-specific transformations are derivative work.

- https://www.gov.uk/government/statistics/journey-time-statistics-access-2014
- https://www.gov.uk/government/statistical-data-sets/journey-time-statistics-data-tables-jts
- https://www.gov.uk/government/publications/journey-time-statistics-guidance
- https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/

**Release:** `split=example`, `release_role=public_demo`; NOT a held-out test sample. No real agent inference run has been conducted. All numeric/structure checks below are deterministic offline checks.
