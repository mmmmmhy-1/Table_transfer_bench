#!/usr/bin/env python3
"""Mutation tests: valid Gold passes; distinct semantic corruptions fail."""
from __future__ import annotations
import tempfile
from pathlib import Path
from openpyxl import load_workbook
from evaluate import compare
ROOT=Path(__file__).resolve().parent
assert compare(ROOT/'gold_output.xlsx')['success']

def mutation(kind):
    w=load_workbook(ROOT/'gold_output.xlsx');s=w.active
    if kind=='swap_gap':s['AF7']='=W7-E7'
    elif kind=='wrong_original':s['G9']=s['G9'].value+1
    elif kind=='bad_header':s['G6']='Within 45 min'
    elif kind=='remove_mode_merge':s.unmerge_cells('E4:M4')
    elif kind=='drop_region_merge':s.unmerge_cells('A7:A55') if 'A7:A55' in [str(x) for x in s.merged_cells.ranges] else s.unmerge_cells(next(str(m) for m in s.merged_cells.ranges if m.min_col==1 and m.min_row>=7))
    elif kind=='wrong_region':s['A7']='Not a region'
    elif kind=='no_field_codes':s['G6'].comment=None
    elif kind=='wrong_formula':s['AF8']='=E8-X8'
    elif kind=='wrong_cached_value':s['AF10']=-100
    else:raise ValueError(kind)
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/'bad.xlsx';w.save(p)
        result=compare(p)
        if result['success']:raise AssertionError('Mutation incorrectly passed: '+kind)
        return result['errors'][0]

for kind in ['swap_gap','wrong_original','bad_header','remove_mode_merge','drop_region_merge','wrong_region','no_field_codes','wrong_formula','wrong_cached_value']:
    print('EXPECTED_FAIL',kind, mutation(kind))
print('ALL 9 MUTATIONS REJECTED')
