# Environment — table transformation cases

Each case is filed directly under the **environment** domain, irrespective of the data source. Source datasets such as RealHiTBench appear only as case-name hints and in metadata, **not** as subcategories.

| Case folder | Source dataset / original table | Operations | Release role |
|---|---|---|---|
| [case_1_realhitbench_environment21](case_1_realhitbench_environment21/README.md) | [RealHiTBench](https://github.com/cspzyy/RealHiTBench), environment21 | OP2 + OP3 | Public demonstration |
| [case_2_realhitbench_environment43](case_2_realhitbench_environment43/README.md) | [RealHiTBench](https://github.com/cspzyy/RealHiTBench), environment43 | OP1 + OP7 + OP3 | Public demonstration |

Future environmental cases from other datasets should be added as `case_3_<source>`, `case_4_<source>` and so on. A second transformation derived from environment21 should share the same `source_family_id` as case_1, even though it gets its own case number.

Consult [catalog.json](../catalog.json) to filter by source, operations, structure tags or split without creating parallel directory trees.
