# Table Transfer Bench

> **Table Transformation Benchmark V2.1 — agent-oriented research preview**

This repository develops a benchmark for **instruction-driven XLSX transformations by tool-using LLM agents**. Agents inspect a workbook and a natural-language instruction, and deliver a completed workbook for deterministic evaluation.

**Status:** research preview. Currently one public, verified demonstration case is being added; this is **not** a full released benchmark or a hidden test set.

## Atomic operations

| ID | Operation | Description |
|---|---|---|
| OP1 | Reshape | Wide-to-long and multi-dimensional transformation |
| OP2 | Derive Column | Calculated or rule-based columns |
| OP3 | Generate Rows | Summary and generated records |
| OP4 | Field Decomposition | Extract components of compound fields |
| OP5 | Field Normalization | Normalize types, formats, units, and categories |
| OP6 | Relational Join | Key-based integration of tables |

We annotate table structure separately (**S0** flat, **S1** multi-level column headers, **S2** hierarchical row headers, **S3** merged cells, **S4** irregular layouts). Scale is measured continuously, not assigned fixed Small/Medium bins. Compositions and their dependencies are explicitly recorded.

## Dataset organization

Data are grouped **first by domain**, then by **source dataset**, then by **source table / source family**, and finally by individual transformation case:

```text
data/
  <domain>/
    <source_dataset>/
      <source_table_id>/
        cases/<task_id>/
          input.xlsx
          instruction.txt
          metadata.json
          gold_output.xlsx
          gold_canonical.json
          evaluate.py
          README.md
```

For example, the present case belongs to the **environment** domain and comes from **RealHiTBench**. Future environment cases may come from entirely different datasets; other domains (finance, industry, science, etc.) use the same layout. See [dataset organization](data/README.md) and [machine-readable catalog](data/catalog.json).

Domain, source and atomic operation labels are **independent attributes**; do not create separate copies of the same task under OP2 and OP3.

## Public case

[Environment / RealHiTBench / environment21 — OP2 + OP3](data/environment/realhitbench/environment21/cases/op2_op3_total_statistics/README.md)

Input: animal scientific procedures by anaesthesia type, Great Britain 2011. The task restores the **Total column** and **three comparison rows**, while retaining the original two-level anaesthesia header, animal categories (including Mammal/Primate), and two annual total rows.

```bash
python -m pip install -r requirements.txt
python data/environment/realhitbench/environment21/cases/op2_op3_total_statistics/evaluate.py data/environment/realhitbench/environment21/cases/op2_op3_total_statistics/gold_output.xlsx
python data/environment/realhitbench/environment21/cases/op2_op3_total_statistics/evaluate.py /path/to/submission.xlsx
```

Only expose `input.xlsx` and `instruction.txt` to an agent. Gold and reference code must be held back at execution time. The public example is intended for reproducibility, **never for an unseen-test score**.

## Planned releases

The completed project aims to add independent real-data source families, atomic and compositional tasks, workbook structure diagnostics, a generalized evaluator, and source-family-separated train/dev/test splits, plus comparable agent baselines. Those materials are **not yet released**.

## Source attribution and licensing

The public demonstration is derived from [RealHiTBench](https://github.com/cspzyy/RealHiTBench), instance **environment21**, source table *Table 5 Scientific procedures by species of animal and level of anaesthesia*. RealHiTBench's official README identifies its **data license as [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)**; derivative data therefore carry non-commercial-use conditions. See the example's `metadata.json` for source provenance and modifications. Reference: Wu et al., [RealHiTBench, arXiv:2506.13405](https://arxiv.org/abs/2506.13405).

A license for this repository's *original code* has not yet been selected; do not assume that source dataset licensing grants blanket commercial-use permission.
