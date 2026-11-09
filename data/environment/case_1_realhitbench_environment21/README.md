# RealHiTBench environment21 — public example

**Case ID:** `TTB_V2_1_RHB_environment21_OP2_OP3_001`

This case is part of the research-preview **Table Transformation Benchmark V2.1**. Source: [RealHiTBench](https://github.com/cspzyy/RealHiTBench), instance `environment21`, Table 5 *Scientific procedures by species of animal and level of anaesthesia* (Great Britain 2011). The original data are documented by the upstream project as **[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)**. This is a modified derivative; non-commercial and attribution conditions apply.

## Task

- **OP2 Derive Column**: create a separate `Total` column by summing the five anaesthesia-count fields.
- **OP3 Generate Rows**: insert `Increase on 2010`, `Percentage change from 2010`, `Percentage of total for 2011`.
- Preserve the original 2011 `Total` and `2010 Totals` rows, the Mammal/Primate hierarchy, footnote, and existing counts.
- **Critical header relation:** `No anaesthesia` is independent; only four later columns are beneath `Type of anaesthesia`.

## Domain and provenance

This case is classified under **environment** (domain), **RealHiTBench** (source provenance), **environment21** (source table ID), and **OP2 + OP3** (task operations). The case is stored directly under `data/environment/case_1_realhitbench_environment21/`; RealHiTBench is not a taxonomy folder. Other sources use their own numbered case folders directly under `data/environment/`.

## Files and reproduction

`metadata.json` provides source attribution, operation taxonomy and structure annotations. `instruction.txt` is the English agent-facing instruction. `evaluate.py` checks a completed workbook.

The repository includes the self-contained workbook generator `scripts/build_environment21.py`. The XLSX assets are also checked into this public example folder. To regenerate and validate:

```bash
python -m pip install -r requirements.txt
python scripts/build_environment21.py
python data/environment/case_1_realhitbench_environment21/evaluate.py data/environment/case_1_realhitbench_environment21/gold_output.xlsx
```

This produces `input.xlsx`, `gold_output.xlsx` and `gold_canonical.json`. The workflow `.github/workflows/example-check.yml` also attempts to publish verified generated assets; repository Actions permissions may need to permit workflow execution and writing contents.

For agent testing give **only** `input.xlsx` and `instruction.txt`; reserve the gold, generator and evaluator for scoring. The public example's answer is intentionally open, so it **must not** count as held-out testing.

The generated workbooks reproduce original data and the important semantic header/group relationships, with simplified styling rather than an exact pixel-level clone. They are not byte-identical to the original local reconstruction.

**Reference:** Pengzuo Wu et al., [*RealHiTBench: A Comprehensive Realistic Hierarchical Table Benchmark for Evaluating LLM-Based Table Analysis*](https://arxiv.org/abs/2506.13405).

## Agentic instruction tracks (V2.1)

- **Main / Discovery:** pass only `input.xlsx` and `instruction.txt` to the agent. Prompts state business requirements and output invariants without revealing unnecessary coordinates, original-data totals or sample answers.
- **Guided diagnostic:** use `instruction_guided.txt` *instead of*, never together with, the Discovery prompt; report results separately. Do not add guided examples to the main leaderboard.
- **Shared output contract:** Guided adds source locations to exactly the same Discovery business instruction. Fonts, sizes, colors, borders and decorative title/footnote merge widths are flexible. The standalone Total header may be vertically merged or left unmerged.
- **Gold / Evaluator:** preserve original semantic header groups and keep Total outside Type of anaesthesia. Values, row order, hierarchy, source text and percentage precision remain strict. Gold's title/footnote merge widths are illustrative. The evaluator accepts supported uncached numeric formulas.

See [agentic prompt authoring](../../../docs/instruction_authoring_v2.1_zh.md). These public examples must not be counted in a held-out test set.
