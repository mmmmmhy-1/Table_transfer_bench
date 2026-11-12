# Science58 | TNF paired Ct comparisons | V2.2 public preview

Source: [RealHiTBench](https://github.com/cspzyy/RealHiTBench), `science-table58.html`, input reconstructed from the user-supplied Excel/HTML derivative. Upstream dataset license: CC BY-NC 4.0 (verify conditions before broader redistribution).

**Single benchmark case**: `TTB_V2_2_RHB_science58_OP4_OP7_OP3_001` under `data/science/case_1_realhitbench_science58/`. Only one output Excel worksheet, named `TNF Comparison`. Its 15 data rows comprise ten preserved treatments and five inserted comparison rows; the 16 columns comprise four identifiers/experimental factors and 12 raw Ct measurements.

## Why these operations

- **OP4 / F3 (Field Decomposition):** interpret Treatment strings and extract TNF state and siRNA target, including the distinct meanings of `+TNF` versus `Runx1+3`.
- **OP7 / T2 (Structural Transformation):** flatten the original merged four-level gene/experiment/replicate/measurement header into unique unmerged semantic headers.
- **OP3 / G3 (Generate Rows):** insert 5 comparison rows for same-siRNA -TNF/+TNF pairs; each contains 12 signed paired differences, **Ct(+TNF) - Ct(-TNF)**. Arithmetic is part of generating rows, not an independently created derived column (so **no OP2**). No wide-to-long operation is requested (so **no OP1**).

The source has **9 merged regions** and two original Ct entries represented as numeric strings. Numeric conversion is only to support numeric output/measurement accuracy, not an independently specified general field-normalization task (so **no independent OP5 label**).

## Contents

- `input.xlsx` — original supplied input (unmodified; one sheet, 14 rows including 4 header rows).
- `instruction.txt` — **Discovery**, agent-facing; states business/output requirements without providing actual data totals, results or source cell coordinates.
- `instruction_guided.txt` — a separate Guided diagnostic; never provide together with Discovery.
- `gold_output.xlsx` — one-sheet reference workbook. Original Ct values are numeric, comparison values have Excel formulas and cached results; no rounding in underlying values.
- `gold_canonical.json` — case-specific canonical reference for review.
- `build_gold.py` — deterministic, fully offline, reference Gold builder from `input.xlsx`.
- `evaluate.py` — independently loads `input.xlsx` and computes expected facts, compares submitted output and evaluates supported numeric arithmetic formulas safely; no macro/external references.
- `test_case.py` — regression suite with reference success, valid equivalent output, and deliberately corrupt outputs.
- `metadata.json` — source provenance, case/operation labels, structure tags, dependencies, difficulty, scope and scoring rules.

## Semantics and audit notes

There are 5 independent treatment contrasts (None, Control, Runx1, Runx3, Runx1 + Runx3). Each pair has one -TNF and one +TNF Set, and each Set contains a CD40 and a b-actin Ct for Expt1–3, repli1/2. The difference is *not* biological `Delta Ct = CD40 minus b-actin`, not a mean, not an absolute difference and not a claim of pre/post sampling. In particular, `Runx1+3` is the siRNA combination, not the TNF state.

Raw Ct source precision is retained to the practical precision of Excel's numeric representation; the Gold displays 12 decimal places but does not intentionally round underlying numeric cells. Spreadsheet changes in data types for pre-existing numeric strings are explicitly specified in the instruction. The evaluator uses **abs tolerance 1e-9, relative tolerance 1e-12**, accepting correctly computed formulas or numeric constants, and rejects wrong grouping, wrong sign, missing Ct fields, truncated precision, and wrong header mapping.

## Local verification

```bash
python build_gold.py
python evaluate.py gold_output.xlsx
python test_case.py
```

Agent sees *only* `input.xlsx` and `instruction.txt` for the main Discovery track. Do not provide the Gold, builder, evaluator or Guided prompt to the model at run time. Published gold means this case is `split=example`, `release_role=public_demo` and **cannot be used as unseen/held-out test data**. As this example is derived from one source table, any later Science58 variants must share `source_family_id=RealHiTBench_science58` and must never cross evaluation splits.