"""Validate operation boundaries and completeness of new table contracts."""
import copy
import json
import unittest
from jsonschema import Draft202012Validator
from benchmark.runner import ROOT
from scripts.validate_annotations import validate_table_contract


class OP6ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT/'schemas/case_metadata.schema.json').read_text(encoding='utf-8'))
        cls.validator = Draft202012Validator(cls.schema)
        cls.base = json.loads((ROOT/'data/environment/case_1_realhitbench_environment21/metadata.json').read_text(encoding='utf-8'))
        cls.nodes = json.loads((ROOT/'examples/op6_contracts.json').read_text(encoding='utf-8'))['nodes']

    def errors(self, node):
        meta = copy.deepcopy(self.base)
        meta.update(operations=['OP6'], operation_nodes=[node], dependency_edges=[])
        return list(self.validator.iter_errors(meta)) + validate_table_contract(node)

    def test_join_append_and_both_split_examples_are_valid(self):
        for node in self.nodes:
            with self.subTest(node=node['id']): self.assertEqual(self.errors(node), [])

    def test_multikey_join_and_cardinality_labels_are_consistent(self):
        node = copy.deepcopy(self.nodes[0])
        node['table_contract']['keys'] = node['table_contract']['keys'][:1]
        self.assertTrue(self.errors(node))
        node['subtype'] = 'J1'
        self.assertTrue(self.errors(node))  # Still many_to_one, not one_to_one.
        node['table_contract']['cardinality'] = 'one_to_one'
        self.assertEqual(self.errors(node), [])

    def test_join_requires_unmatched_and_duplicate_policies(self):
        for field in ('unmatched_policy', 'duplicate_policy', 'null_policy'):
            node = copy.deepcopy(self.nodes[0]); del node['table_contract'][field]
            self.assertTrue(self.errors(node))

    def test_concat_mapping_and_missing_fields_cannot_be_implicit(self):
        node = copy.deepcopy(self.nodes[1]); del node['table_contract']['missing_column_policy']
        self.assertTrue(self.errors(node))
        node = copy.deepcopy(self.nodes[1]); node['table_contract']['column_alignment'] = 'explicit_mapping'
        self.assertTrue(self.errors(node))

    def test_partition_requires_coverage_and_overlap_policy(self):
        node = copy.deepcopy(self.nodes[2]); del node['table_contract']['row_coverage']
        self.assertTrue(self.errors(node))
        node = copy.deepcopy(self.nodes[2]); node['table_contract']['row_coverage'] = 'specified_overlap'
        self.assertTrue(self.errors(node))

    def test_column_split_rejects_loss_duplication_and_unmapped_output(self):
        for mutation in ('loss', 'duplicate', 'output', 'key'):
            node = copy.deepcopy(self.nodes[3]); contract = node['table_contract']
            if mutation == 'loss': contract['column_groups']['sale_measures'].remove('amount')
            if mutation == 'duplicate': contract['column_groups']['sale_measures'].append('region')
            if mutation == 'output': contract['output_tables'].append('unknown')
            if mutation == 'key': contract['column_groups']['sale_measures'].append('record_id')
            self.assertTrue(self.errors(node), mutation)

    def test_cell_merge_is_not_an_op6_kind(self):
        node = copy.deepcopy(self.nodes[1]); node['table_contract']['kind'] = 'merge_cells'
        self.assertTrue(self.errors(node))

    def test_op7_remains_available(self):
        meta = copy.deepcopy(self.base)
        meta.update(operations=['OP7'], operation_nodes=[{'id':'groups','operation':'OP7','subtype':'T1'}], dependency_edges=[])
        self.assertEqual(list(self.validator.iter_errors(meta)), [])

    def test_malformed_contract_reports_errors_without_crashing(self):
        node = copy.deepcopy(self.nodes[3]); node['table_contract'] = None
        self.assertTrue(self.errors(node))
        node = copy.deepcopy(self.nodes[3]); node['table_contract']['column_groups'] = 'invalid'
        self.assertTrue(self.errors(node))


if __name__ == '__main__':
    unittest.main()
