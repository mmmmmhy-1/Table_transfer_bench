# Benchmark documentation

**Current specification: Table Transformation Benchmark V2.1 (Agent-Oriented).** These documents describe the proposed and adopted **construction and annotation requirements**, not a claim that the target dataset has already been collected.

- [V2.1 Benchmark Construction Standard — 中文](benchmark_standard_v2.1_zh.md): aims, six operations, independent structural/scale dimensions, composition, quality, evaluation, split, baselines.
- [V2.1 Annotation and Construction SOP — 中文](annotation_guidelines_v2.1_zh.md): case-by-case labeling procedure, boundary decisions, metadata fields, review checklists and rejection rules.
- [Agentic task instruction authoring / Discovery–Guided policy — 中文](instruction_authoring_v2.1_zh.md): leakage checks, necessary business constraints, prompt/Gold/Evaluator alignment, and public-case examples.
- [Metadata JSON Schema](../schemas/case_metadata.schema.json): machine-readable validation contract for each case.
- [Dataset case naming and organization](../data/README.md): `data/<domain>/case_<N>_<source-slug>/`.

**Note for international collaborators:** labels and file paths use English identifiers, while the normative research-workflow text is currently maintained in Chinese. An English translation may be added later; do not silently diverge from the V2.1 scope.

To validate existing case metadata:

```bash
python -m pip install -r requirements.txt
python scripts/validate_annotations.py
```

This command checks JSON Schema compatibility, catalog-to-case links and source-family split consistency. It does **not** replace the case's XLSX output evaluator or human quality review.
