# RealHiTBench labor43 — public review example

**Case ID:** `TTB_V2_1_RHB_labor43_OP1_OP2_001`

Source: [RealHiTBench](https://github.com/cspzyy/RealHiTBench), original table `labor43` (`labor-table43.html`). The input XLSX reconstructs the provided HTML with its original six fields and eight Company merge regions; the worker names are demonstration placeholders. The source dataset is documented as CC BY-NC 4.0; maintain upstream attribution and noncommercial conditions.

**Task:** OP1 (R3 grouped multi-field unpivot) + OP2 (derive company employee count and individual skill count). Input structure tags: S2, S3. Output: 52 data rows, six columns, 42 employees, 11 companies, 48 Skill occurrences and 48 Area occurrences. Company / Company Employee Count merge by company; Name / Employee Skill Count merge by employee. Singleton Skill or Area values merge over multirow employee blocks. Skill and Area are independent lists: visual alignment does not imply a one-to-one skill/area pairing.

Only provide `input.xlsx` and `instruction.txt` to agents. Hold back `gold_output.xlsx`, `gold_canonical.json`, and `evaluate.py` for scoring. The gold is openly published and **not** a held-out test example.

## Files

`input.xlsx`: source-derived XLSX; `instruction.txt`: agent instruction; `metadata.json`: source provenance and operation DAG; `gold_output.xlsx`: reference workbook with numeric count formulas and caches; `gold_canonical.json`: expected values and merge ranges; `evaluate.py`: strict deterministic evaluator.

## Check

```bash
python data/labor/case_1_realhitbench_labor43/evaluate.py data/labor/case_1_realhitbench_labor43/gold_output.xlsx
python scripts/validate_annotations.py
```

Excel semantics: F7:F8 is vertically merged for demo name 6's Manchester, whose Skill values occupy two separate rows. The evaluator checks exact values, row order, grouping and merges, with limited support for valid uncached COUNT formulas.

## Agentic instruction tracks (V2.1)

- **Main / Discovery:** pass only `input.xlsx` and `instruction.txt` to the agent. Prompts state business requirements and output invariants without revealing unnecessary coordinates, original-data totals or sample answers.
- **Guided diagnostic:** use `instruction_guided.txt` *instead of*, never together with, the Discovery prompt; report results separately. Do not add guided examples to the main leaderboard.
- **Gold / Evaluator:** reference layout is illustrative where the main prompt does not prescribe a location; this case's evaluator checks specified business semantics, values and required merges, including supported uncached numeric formulas.

See [agentic prompt authoring](../../../docs/instruction_authoring_v2.1_zh.md). These public examples must not be counted in a held-out test set.
