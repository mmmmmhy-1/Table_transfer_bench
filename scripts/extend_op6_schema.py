"""Reproducible schema update for the V2.2 OP6 contract addendum."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def update():
    path = ROOT / 'schemas/case_metadata.schema.json'
    schema = json.loads(path.read_text(encoding='utf-8'))
    text = {'type': 'string', 'minLength': 1, 'pattern': r'\S'}
    strings = {'type': 'array', 'items': text, 'minItems': 1, 'uniqueItems': True}
    table = {
        'type': 'object',
        'required': ['kind', 'input_tables', 'output_tables', 'duplicate_policy', 'null_policy', 'order_policy'],
        'properties': {
            'kind': {'enum': ['join', 'append_rows', 'partition_rows', 'split_columns']},
            'input_tables': strings, 'output_tables': strings,
            'duplicate_policy': text, 'null_policy': text, 'order_policy': text,
            'keys': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                     'items': {'type': 'object', 'required': ['left', 'right'],
                               'properties': {'left': text, 'right': text}, 'additionalProperties': False}},
            'join_type': {'enum': ['inner', 'left', 'right', 'full']},
            'cardinality': {'enum': ['one_to_one', 'one_to_many', 'many_to_one', 'many_to_many']},
            'unmatched_policy': text,
            'column_alignment': {'enum': ['by_name', 'explicit_mapping']},
            'schema_policy': {'enum': ['strict', 'union', 'intersection', 'explicit_mapping']},
            'missing_column_policy': text,
            'column_mapping': {'type': 'object', 'minProperties': 1, 'additionalProperties': strings},
            'partition_keys': strings, 'routing_policy': text,
            'row_coverage': {'enum': ['exactly_once', 'specified_overlap']},
            'unassigned_policy': text, 'overlap_policy': text,
            'key_columns': strings, 'source_columns': strings,
            'column_groups': {'type': 'object', 'minProperties': 2, 'additionalProperties': strings},
            'reconstruction_policy': text,
        },
        'additionalProperties': False,
        'allOf': []
    }
    rules = {
        'join': (['keys', 'join_type', 'cardinality', 'unmatched_policy'],
                 {'input_tables': {'minItems': 2, 'maxItems': 2}, 'output_tables': {'maxItems': 1}}),
        'append_rows': (['column_alignment', 'schema_policy', 'missing_column_policy'],
                        {'input_tables': {'minItems': 2}, 'output_tables': {'maxItems': 1}}),
        'partition_rows': (['partition_keys', 'routing_policy', 'row_coverage', 'unassigned_policy'],
                           {'input_tables': {'maxItems': 1}, 'output_tables': {'minItems': 2}}),
        'split_columns': (['key_columns', 'source_columns', 'column_groups', 'reconstruction_policy'],
                          {'input_tables': {'maxItems': 1}, 'output_tables': {'minItems': 2}}),
    }
    for kind, (required, properties) in rules.items():
        table['allOf'].append({'if': {'properties': {'kind': {'const': kind}}},
                               'then': {'required': required, 'properties': properties}})
    table['allOf'].extend([
        {'if': {'properties': {'column_alignment': {'const': 'explicit_mapping'}}, 'required': ['column_alignment']},
         'then': {'required': ['column_mapping']}},
        {'if': {'properties': {'schema_policy': {'const': 'explicit_mapping'}}, 'required': ['schema_policy']},
         'then': {'required': ['column_mapping'], 'properties': {'column_alignment': {'const': 'explicit_mapping'}}}},
        {'if': {'properties': {'row_coverage': {'const': 'specified_overlap'}}, 'required': ['row_coverage']},
         'then': {'required': ['overlap_policy']}},
    ])
    schema['$defs']['op6_table_contract'] = table
    node = schema['properties']['operation_nodes']['items']
    node['properties']['table_contract'] = {'$ref': '#/$defs/op6_table_contract'}
    op6 = {'required': ['subtype', 'table_contract'],
           'properties': {'subtype': {'enum': [f'J{i}' for i in range(1, 8)]}}, 'allOf': []}
    for subtype, kind in [('J1','join'), ('J2','join'), ('J3','join'), ('J4','join'),
                          ('J5','append_rows'), ('J6','partition_rows'), ('J7','split_columns')]:
        constraints = {'kind': {'const': kind}}
        if subtype in ('J1', 'J2', 'J3'):
            constraints['keys'] = {'maxItems': 1}
        if subtype == 'J1': constraints['cardinality'] = {'const': 'one_to_one'}
        if subtype == 'J2': constraints['cardinality'] = {'enum': ['one_to_many', 'many_to_one']}
        if subtype == 'J3': constraints['cardinality'] = {'const': 'many_to_many'}
        if subtype == 'J4': constraints['keys'] = {'minItems': 2}
        op6['allOf'].append({'if': {'properties': {'subtype': {'const': subtype}}},
                             'then': {'properties': {'table_contract': {'properties': constraints}}}})
    # Keep OP7 and all pre-existing node properties intact.
    node['allOf'] = [x for x in node.get('allOf', []) if x.get('if', {}).get('properties', {}).get('operation') != {'const': 'OP6'}]
    node['allOf'].append({'if': {'properties': {'operation': {'const': 'OP6'}}}, 'then': op6})
    schema['properties']['operation_taxonomy_revision'] = {
        'type': 'string', 'description': 'Optional taxonomy addendum identifier, e.g. 2.2-op6-v2.'}
    path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    update()
