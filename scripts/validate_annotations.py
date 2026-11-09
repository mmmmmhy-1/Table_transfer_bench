#!/usr/bin/env python3
"""Validate Table Transfer Bench V2.2 case annotations and catalog consistency.

This is a metadata-only checker. The case-specific evaluator must separately
validate workbook content, gold output and error injection.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog.json"
SCHEMA = ROOT / "schemas" / "case_metadata.schema.json"


def validate_table_contract(node):
    """Cross-field checks not expressible by the annotation JSON Schema."""
    if node.get('operation') != 'OP6':
        return []
    contract = node.get('table_contract', {})
    if not isinstance(contract, dict):
        return ['OP6 table_contract must be an object']
    errors = []
    if contract.get('kind') == 'split_columns':
        groups = contract.get('column_groups', {})
        if not isinstance(groups, dict) or any(not isinstance(fields, list) or any(not isinstance(field, str) for field in fields) for fields in groups.values()):
            return ['OP6 split_columns column_groups must map table names to field-name lists']
        outputs = set(contract.get('output_tables', []))
        if set(groups) != outputs:
            errors.append('OP6 split_columns column_groups must name every output table exactly')
        keys = set(contract.get('key_columns', []))
        payload = [field for columns in groups.values() for field in columns]
        if keys.intersection(payload):
            errors.append('OP6 split_columns key columns belong in key_columns, not payload groups')
        if len(payload) != len(set(payload)):
            errors.append('OP6 split_columns non-key columns must occur exactly once')
        if keys.union(payload) != set(contract.get('source_columns', [])):
            errors.append('OP6 split_columns must preserve every source column without inventing columns')
    if contract.get('kind') == 'join':
        pairs = contract.get('keys', [])
        for side in ('left', 'right'):
            columns = [pair.get(side) for pair in pairs if isinstance(pair, dict)]
            if len(columns) != len(set(columns)):
                errors.append('OP6 join repeats a key field on the ' + side + ' side')
    return errors


def main() -> int:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    errors = []
    seen_case_ids = set()
    seen_paths = set()
    seen_numbers = set()
    family_splits = defaultdict(set)

    entries = catalog.get("cases", [])
    for entry in entries:
        case_id = entry.get("case_id")
        path = entry.get("path")
        if case_id in seen_case_ids:
            errors.append(f"Duplicate case ID in catalog: {case_id}")
        seen_case_ids.add(case_id)
        if path in seen_paths:
            errors.append(f"Duplicate path in catalog: {path}")
        seen_paths.add(path)
        case_dir = ROOT / (path or "")
        if not path or not case_dir.is_dir():
            errors.append(f"Catalog path missing: {path}")
            continue
        meta_path = case_dir / "metadata.json"
        if not meta_path.is_file():
            errors.append(f"Missing metadata.json: {meta_path}")
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            errors.append(f"Cannot parse {meta_path}: {exc}")
            continue
        for err in validator.iter_errors(meta):
            loc = ".".join(map(str, err.absolute_path)) or "(root)"
            errors.append(f"{path}: schema violation at {loc}: {err.message}")
        for key, catalog_key in (
            ("case_id", "case_id"),
            ("domain", "domain"),
            ("source_family_id", "source_family_id"),
            ("operations", "operations"),
            ("structure_tags", "structure_tags"),
            ("split", "split"),
            ("release_role", "release_role"),
            ("case_number", "case_number"),
            ("case_slug", "case_slug"),
        ):
            if catalog_key in entry and meta.get(key) != entry[catalog_key]:
                errors.append(f"{path}: catalog/metadata mismatch in {key}")
        if meta.get("case_relative_path") != path:
            errors.append(f"{path}: metadata case_relative_path mismatch")
        if meta.get("source", {}).get("source_dataset") != entry.get("source_dataset"):
            errors.append(f"{path}: source_dataset differs from catalog")
        if meta.get("source", {}).get("source_instance") != entry.get("source_table_id"):
            errors.append(f"{path}: source_instance differs from catalog source_table_id")
        if meta.get("case_slug") and Path(path).name != meta["case_slug"]:
            errors.append(f"{path}: folder name differs from case_slug")
        number = meta.get("case_number")
        if number is not None:
            pair = (meta.get("domain"), number)
            if pair in seen_numbers:
                errors.append(f"Duplicate case number within domain: {pair}")
            seen_numbers.add(pair)
        if "S0" in meta.get("structure_tags", []) and len(meta["structure_tags"]) > 1:
            errors.append(f"{path}: S0 flat must not coexist with S1-S4")
        nodes = meta.get("operation_nodes", [])
        if 'OP6' in meta.get('operations', []) and not any(n.get('operation') == 'OP6' for n in nodes):
            errors.append(f'{path}: OP6 requires an operation node and a table_contract')
        for node in nodes:
            errors.extend(f'{path}: {err}' for err in validate_table_contract(node))
        if nodes:
            ids = [n["id"] for n in nodes]
            if len(ids) != len(set(ids)):
                errors.append(f"{path}: duplicate operation node ID")
            node_ops = {n["operation"] for n in nodes}
            if node_ops != set(meta.get("operations", [])):
                errors.append(f"{path}: operation_nodes and operations disagree")
            graph = {node_id: [] for node_id in ids}
            for src, dst in meta.get("dependency_edges", []):
                if src not in graph or dst not in graph:
                    errors.append(f"{path}: DAG references unknown node {src} / {dst}")
                else:
                    graph[src].append(dst)
            state = {}
            def visit(node):
                if state.get(node) == "visiting":
                    return False
                if state.get(node) == "done":
                    return True
                state[node] = "visiting"
                for target in graph[node]:
                    if not visit(target):
                        return False
                state[node] = "done"
                return True
            if not all(visit(node) for node in graph):
                errors.append(f"{path}: cyclic operation dependencies")
        elif meta.get("dependency_edges"):
            errors.append(f"{path}: dependency_edges provided without operation_nodes")
        family_splits[meta.get("source_family_id")].add(meta.get("split"))

    for family, splits in family_splits.items():
        production = splits.intersection({"train", "dev", "test"})
        if len(production) > 1:
            errors.append(f"Source-family leakage across train/dev/test: {family}: {sorted(production)}")
        if "example" in splits and production:
            errors.append(f"Public example family mixed with production splits: {family}: {sorted(splits)}")

    # Do not allow an unindexed case to silently bypass schema checks.
    for meta_path in (ROOT / "data").glob("*/case_*/metadata.json"):
        rel_dir = meta_path.parent.relative_to(ROOT).as_posix()
        if rel_dir not in seen_paths:
            errors.append(f"Unindexed case folder: {rel_dir}")

    print(f"Scanned {len(entries)} cataloged cases")
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1
    print("PASS: schema, catalog, operation DAG, and split isolation checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
