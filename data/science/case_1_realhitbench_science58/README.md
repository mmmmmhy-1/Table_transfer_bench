# Science58 | TNF paired Ct comparisons | V2.2 public preview

Source: [RealHiTBench](https://github.com/cspzyy/RealHiTBench), `science-table58.html`, input reconstructed from the user-supplied Excel/HTML derivative. Upstream dataset license: CC BY-NC 4.0 (verify conditions before broader redistribution).

An upstream HTML snapshot is pinned to Hugging Face revision `68ca8e50950dc0704c53968ff9a4a0456b585e96` in `source/science-table58.html`, with its URL and SHA-256 in Metadata. The supplied XLSX omits the HTML's blank separator columns; its 120 Ct values and 20 original Set/Treatment cells match the snapshot. `verify_source.py` reconstructs the HTML header spans and checks all 12 semantic measurement paths independently of the builder and evaluator.

**Single benchmark case**: `TTB_V2_2_RHB_science58_OP4_OP7_OP3_001` under `data/science/case_1_realhitbench_science58/`. Only one output Excel worksheet, named `TNF Comparison`. Its 15 data rows comprise ten preserved treatments and five inserted comparison rows; the 16 columns comprise four identifiers/experimental factors and 12 raw Ct measurements.

## Why these operations

- **OP4 / F3 (Field Decomposition):** interpret Treatment strings and extract TNF state and siRNA target, including the distinct meanings of `+TNF` versus `Runx1+3`.
- **OP7 / T2 (Structural Transformation):** flatten the original merged four-level gene/experiment/replicate/measurement header into unique unmerged semantic headers.
- **OP3 / G3 (Generate Rows):** insert 5 comparison rows for same-siRNA -TNF/+TNF pairs; each contains 12 signed paired differences, **Ct(+TNF) - Ct(-TNF)**. Arithmetic is part of generating rows, not an independently created derived column (so **no OP2**). No wide-to-long operation is requested (so **no OP1**).

The source has **9 merged regions** and two original Ct entries represented as numeric strings. Numeric conversion is only to support numeric output/measurement accuracy, not an independently specified general field-normalization task (so **no independent OP5 label**).

**Dependency scope:** OP4 supplies the TNF/siRNA factors used by OP3. OP7 is a separately required header transformation, but flattening does not have to precede difference calculation. The DAG therefore contains only OP4 → OP3, with OP7 parallel. This is not a fully dependent three-operation chain. L4 remains a heuristic for multiple operations with complex input structure; the small input and already-adjacent pairs limit its difficulty.

## Contents

- `input.xlsx` — original supplied input (unmodified; one sheet, 14 rows including 4 header rows).
- `instruction.txt` — **Discovery**, agent-facing; states business/output requirements without providing actual data totals, results or source cell coordinates.
- `instruction_guided.txt` — a separate Guided diagnostic; never provide together with Discovery.
- `verify_source.py` and `source/science-table58.html` — independent, offline upstream provenance/fact checks.
- `gold_output.xlsx` — one-sheet reference workbook. Original Ct values are numeric, comparison values have Excel formulas and cached results; no rounding in underlying values.
- `gold_canonical.json` — case-specific canonical reference for review.
- `build_gold.py` — deterministic, fully offline, reference Gold builder from `input.xlsx`.
- `evaluate.py` — independently loads `input.xlsx` and computes expected facts, compares submitted output and evaluates supported numeric arithmetic formulas safely; no macro/external references.
- `test_case.py` — regression suite with reference success, valid equivalent output, and deliberately corrupt outputs.
- `metadata.json` — source provenance, case/operation labels, structure tags, dependencies, difficulty, scope and scoring rules.

## Semantics and audit notes

There are 5 independent treatment contrasts (None, Control, Runx1, Runx3, Runx1 + Runx3). Each pair has one -TNF and one +TNF Set, and each Set contains a CD40 and a b-actin Ct for Expt1–3, repli1/2. The difference is *not* biological `Delta Ct = CD40 minus b-actin`, not a mean, not an absolute difference and not a claim of pre/post sampling. In particular, `Runx1+3` is the siRNA combination, not the TNF state.

Raw Ct source precision is retained to the practical precision of Excel's numeric representation; the Gold displays 12 decimal places but does not intentionally round underlying numeric cells. Spreadsheet changes in data types for pre-existing numeric strings are explicitly specified in the instruction. The evaluator uses **abs tolerance 1e-9, relative tolerance 1e-12**, accepting correctly computed formulas or numeric constants, and rejects wrong grouping, wrong sign, missing Ct fields, truncated precision, and wrong header mapping.

Checker revision `science58_tnf_pair_v2_2_002` accepts the repository's safe offline formula subset, including arithmetic and `SUM`; it evaluates formulas directly without relying on cached results. Functions outside the stated subset must be submitted as numeric values. Font, font size, color, borders and cell dimensions do not affect correctness. Blank outer margins, styling-only empty cells and singleton merge records are equivalent; the logical table must remain contiguous and ordered. Guided contains the complete Discovery text unchanged, prefixed only by source structure locations.

Audit corrections: the original checker incorrectly rejected a correct `SUM(E3,-E2)` expression and style-only used-range extensions, and the original Guided text abbreviated business requirements. No input or Gold measurements were changed. Scores from checker revision 001 must be recomputed before comparison with revision 002.

## Local verification

```bash
python build_gold.py
python evaluate.py gold_output.xlsx
python verify_package.py
python test_case.py
```

Agent sees *only* `input.xlsx` and `instruction.txt` for the main Discovery track. Do not provide the Gold, builder, evaluator or Guided prompt to the model at run time. Published gold means this case is `split=example`, `release_role=public_demo` and **cannot be used as unseen/held-out test data**. As this example is derived from one source table, any later Science58 variants must share `source_family_id=RealHiTBench_science58` and must never cross evaluation splits.
