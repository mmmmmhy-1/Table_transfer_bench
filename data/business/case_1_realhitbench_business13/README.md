# RealHiTBench business13 — OP1 + OP2

**Case ID**: `TTB_V2_1_RHB_business13_OP1_OP2_001`

**Source**: [RealHiTBench](https://github.com/cspzyy/RealHiTBench), `business13` / `business-table13.html`. Source data license **[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)**.

This is a public reproducibility example derived from the original table. It is not a held-out test case.

- **Input**: 28 normalized records (`Country`, `Metric`, `Year`, `Value`), plus original Notes and Key.
- **OP1**: Pivot the two metrics over 2014/2015 into a six-column, two-level grouped wide table with seven country rows.
- **OP2**: Calculate 2015-over-2014 exports-of-services growth in a separate numeric ratio column, formatted `0.00%`.
- **Important**: Source `Percentage of telecoms world total` values are already percentage-point numbers. They must not be divided by 100 or formatted as Excel percentages.
- **Header merges**: `A1:A2`, `B1:C1`, `D1:E1`, `F1:F2`. Notes/Key lines retain their own merged display cells.
- **Release role**: public_demo; public Gold must never be counted as hidden Test.

For an agent, provide only `input.xlsx` and `instruction.txt`. Hold back `gold_output.xlsx` and `evaluate.py` during execution.

To regenerate and check:
```bash
python scripts/build_business13.py
python data/business/case_1_realhitbench_business13/evaluate.py data/business/case_1_realhitbench_business13/gold_output.xlsx
python scripts/validate_annotations.py
```

The generator transcribes source values and Notes/Key, with a deterministic cached ratio in the Gold formula cells. Source amounts in £m are rounded; growth is computed from those published rounded values.
