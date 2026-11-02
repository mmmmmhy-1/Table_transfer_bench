# RealHiTBench environment21 — public example

**Case ID:** `TTB_V2_1_RHB_environment21_OP2_OP3_001`

**Source:** [RealHiTBench](https://github.com/cspzyy/RealHiTBench), `environment21`, Table 5 *Scientific procedures by species of animal and level of anaesthesia* (Great Britain 2011). **Data license: CC BY-NC 4.0**; this is a modified derivative for a non-commercial academic benchmark.

**Operations:** OP2 (Derive Column) + OP3 (Generate Rows). Restore a separate Total column and three derived statistical rows. Preserve existing 2011 Total and 2010 Totals rows, Mammal/Primate hierarchy, and the original column header nesting.

**Important:** `No anaesthesia` is a standalone header, **not** a child of `Type of anaesthesia`; the latter covers only the four following anaesthesia types.

The validated XLSX input and gold files were constructed from the user-supplied HTML. They are temporarily distributed in the accompanying case archive while the repository's binary artifact publication is being completed. Do not treat the public example as a held-out benchmark sample. The sample's `metadata.json`, task instructions, source and verification workflow will be published here.

Reference: Wu et al., [RealHiTBench](https://arxiv.org/abs/2506.13405).
