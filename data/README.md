# Data layout and case conventions

**Primary organization:** domain → numbered case. A case is a **single benchmark task**, including its instruction, input workbook and reference output. The source dataset is recorded in JSON, not used as a directory category.

```text
data/
  README.md
  catalog.json
  environment/
    README.md
    case_1_realhitbench_environment21/
      input.xlsx
      instruction.txt
      metadata.json
      gold_output.xlsx
      gold_canonical.json
      evaluate.py
      README.md
    case_2_<source-short-name>/ ...
  finance/
    case_<N>_<source-short-name>/
      ...
  industry/
    case_<N>_<source-short-name>/
      ...
```

- **Domain:** `environment`, `finance`, `industry`, `science`, etc. Chosen for the *subject of the table*, not for the originating benchmark.
- **Case name:** `case_<N>_<source-slug>`. Assign a unique, stable number **within a domain**; use the same standard on every future case. Do not renumber published cases.
- **Source/provenance:** `metadata.json` must record the actual `source_dataset`, `source_instance`, `source_url`, original filename, license, transformation history, and `source_family_id`.
- **Operations:** `operations` can hold OP1–OP6 and their combinations. Do not create extra copies of the same case under different operation folders.
- **Structure and scale:** preserve independent `structure_tags` and continuous workbook statistics in metadata.
- **Cross-case isolation:** variants derived from the same original table share the same `source_family_id`, even when they live in separate case folders. Keep that family together for train/dev/test splits.
- **Public examples:** cases with `split: example` and `release_role: public_demo` may contain public gold. Never score them as held-out test cases. Keep hidden-test answers private.
- **Index:** append each case to [catalog.json](catalog.json) with its domain, source, source family, operations, split and relative path.

The current RealHiTBench-derived example is subject to **CC BY-NC 4.0**. Licensing must be checked per source dataset; the benchmark repository does not automatically own the underlying data.

- Labor public review example: `data/labor/case_1_realhitbench_labor43/` (RealHiTBench labor43, OP1+OP2).
