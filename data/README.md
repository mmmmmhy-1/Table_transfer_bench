# Dataset layout and classification

Each case belongs to a **domain** (subject area) independently of its **source dataset** and its **operation labels**. A single case may involve multiple operations (e.g., OP2 + OP3) and multiple structure tags (S1, S2, etc.) but is stored only once.

```text
data/
  catalog.json
  environment/
    README.md
    realhitbench/
      environment21/
        cases/
          op2_op3_total_statistics/
            input.xlsx
            instruction.txt
            metadata.json
            gold_output.xlsx
            gold_canonical.json
            evaluate.py
            README.md
  <other_domain>/
    <other_source_dataset>/
      <source_table_id>/
        cases/<task_id>/...
```

**Future examples**: `data/environment/<another_source>/<original_table_id>/cases/<task_id>/` for more environmental data; `data/finance/<source>/<table>/cases/<task>/` for financial data. Source names and source instance IDs should be stable lowercase slugs; preserve the official spelling in `metadata.json`.

Metadata must record `case_id`, `domain`, `source_family_id`, `source` (including license / attribution), `operations`, `structure_tags`, `split`, and the relative path to the case. All derivatives of one original table use the same `source_family_id` for leakage-safe splitting.

**Releasing data:** `split: example` and `release_role: public_demo` indicate fully public example answers; they are not held-out test tasks. Future train/dev/test publication must separately manage gold-output access. Follow upstream redistribution licenses for every source. The current RealHiTBench-derived case is **CC BY-NC 4.0**.

`catalog.json` indexes cases by independent classification attributes; update it whenever a new task is added.
