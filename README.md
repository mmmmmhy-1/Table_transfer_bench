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

The dataset is organized by **subject domain** and a **unique numbered case folder**. Dataset names such as RealHiTBench are **provenance**, not directory categories; the source, original table ID, operation labels, and source-family grouping live in `metadata.json` and the central [catalog](data/catalog.json).

```text
data/
  catalog.json
  environment/
    case_1_realhitbench/
      input.xlsx
      instruction.txt
      metadata.json
      gold_output.xlsx
      gold_canonical.json
      evaluate.py
      README.md
    case_2_<other-source>/ ...
  finance/
    case_.../
  industry/
    case_.../
```

Case names use a stable case number plus a short source suffix for human readability. The suffix is only a filename hint: **domain** and **operations** are independent metadata fields, and cases from one original table share a `source_family_id` so they cannot cross evaluation splits. See [dataset conventions](data/README.md).

## Public case

[Environment / case_1_realhitbench — OP2 + OP3](data/environment/case_1_realhitbench/README.md)

Input: animal scientific procedures by anaesthesia type, Great Britain 2011. The task restores the **Total column** and **three comparison rows**, while retaining the original two-level anaesthesia header, animal categories (including Mammal/Primate), and two annual total rows.

```bash
python -m pip install -r requirements.txt
python data/environment/case_1_realhitbench/evaluate.py data/environment/case_1_realhitbench/gold_output.xlsx
python data/environment/case_1_realhitbench/evaluate.py /path/to/submission.xlsx
```

Only expose `input.xlsx` and `instruction.txt` to an agent. Gold and reference code must be held back at execution time. The public example is intended for reproducibility, **never for an unseen-test score**.

## Planned releases

The completed project aims to add independent real-data source families, atomic and compositional tasks, workbook structure diagnostics, a generalized evaluator, and source-family-separated train/dev/test splits, plus comparable agent baselines. Those materials are **not yet released**.

## Source attribution and licensing

The public demonstration is derived from [RealHiTBench](https://github.com/cspzyy/RealHiTBench), instance **environment21**, source table *Table 5 Scientific procedures by species of animal and level of anaesthesia*. RealHiTBench's official README identifies its **data license as [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)**; derivative data therefore carry non-commercial-use conditions. See the example's `metadata.json` for source provenance and modifications. Reference: Wu et al., [RealHiTBench, arXiv:2506.13405](https://arxiv.org/abs/2506.13405).

A license for this repository's *original code* has not yet been selected; do not assume that source dataset licensing grants blanket commercial-use permission.
