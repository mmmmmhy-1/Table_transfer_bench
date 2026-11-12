# RealHiTBench environment43 — OP1 + OP7 + OP3

**Case ID:** `TTB_V2_2_RHB_environment43_OP1_OP7_OP3_001`

**Source:** RealHiTBench (original table `environment-table43.html`, table identifier `environment43`), [official repository](https://github.com/cspzyy/RealHiTBench), [dataset](https://huggingface.co/datasets/spzy/RealHiTBench). Source table is categorized as *environment* in RealHiTBench; this project's domain is **science**, because the observations are an animal genotype/treatment experiment. Source dataset license: **CC BY-NC 4.0**; attribution retained.

**Task:** Convert 67 animal-level records into a wide, two-level treatment header format, retaining every ID and measurement. For each of the three observed genotype/group combinations, compute three new statistic rows (Mean, sample SD, SEM), separately for Vehicle and Fluoxetine.

- `input.xlsx`: 67 original animal records, with precomputed `average`, `stdv`, `sterror` rows and blank separators removed.
- `instruction.txt`: the English main/Discovery task instruction.
- `gold_output.xlsx`: the target, with treatment parent headers, 35 aligned individual-data rows and 9 generated summary rows (18 calculated cells).
- `metadata.json`: source information, operations, structure and evaluation rules.
- `evaluate.py`: deterministic structural, content and statistics check for the proposed output workbook.
- `build_gold.py`: reproducible source-to-case generator, which reads the committed `input.xlsx` and regenerates the reference output including cached formula values.

**Grouping:** `WT / Control`, `WT / Stress`, and `FGF2KO / Stress`. Do **not** introduce `FGF2KO / Control`: the source has no such observations. In each treatment, animals are distinct and unpaired; side-by-side display is not a matched measurement.

**Statistical conventions:** Sample standard deviation uses `n-1`; `SEM = STDEV.S / SQRT(N)`. Original published summaries were used to audit the constructed reference and are **not** part of the input. Empty cells in the shorter treatment list must not be treated as zero.

Check the provided Gold:

```bash
python data/science/case_2_realhitbench_environment43/evaluate.py data/science/case_2_realhitbench_environment43/gold_output.xlsx
```

For the main benchmark, give an agent **only `input.xlsx` and `instruction.txt`**; withhold Gold and evaluation scripts. This is an openly released *public demo* and **not** a held-out test instance.
