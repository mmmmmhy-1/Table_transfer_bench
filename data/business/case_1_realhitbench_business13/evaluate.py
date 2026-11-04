#!/usr/bin/env python3
"""Semantic evaluator: grouped header + row facts + YoY + preserved notes.

Accepts business-equivalent placement/merging of the Notes and Key section.
Does not force Gold's arbitrary A12/B13... coordinates.
"""
import json, math, sys
from pathlib import Path
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts.formula_eval import SpreadsheetFormulaEvaluator, FormulaError
BASE=Path(__file__).resolve().parent

def evaluate(path):
    errors=[]
    try:
        b=load_workbook(path,data_only=False)
        cached=load_workbook(path,data_only=True)
        reference=json.loads((BASE/'gold_canonical.json').read_text(encoding='utf-8'))
    except Exception as exc:return {'hard_task_success':0,'error_count':1,'errors':[str(exc)]}
    if b.sheetnames!=[reference['sheet']]:errors.append('Expected exactly one worksheet named Exports of services')
    w=b.active;v=cached.active;calc=SpreadsheetFormulaEvaluator(w,v)
    if w.max_column>6:
        if any(w.cell(r,c).value is not None for r in range(1,w.max_row+1) for c in range(7,w.max_column+1)):
            errors.append('Extra populated data columns')
    needed_merges=set(reference['header_merges'])
    merges={str(m) for m in w.merged_cells.ranges}
    if not needed_merges.issubset(merges):errors.append('Missing grouped header merges')
    if any(m.min_row<=9 and m.max_row>=3 for m in w.merged_cells.ranges):errors.append('Unexpected merge across data records')
    for row in range(1,10):
      for col in range(1,7):
        coord=w.cell(row,col).coordinate
        expected=reference['cells'].get(coord)
        try: actual=calc.cell(coord)
        except Exception as exc:
            errors.append(f'{coord}: unevaluable formula: {exc}');continue
        if isinstance(expected,(int,float)) and not isinstance(expected,bool):
            if not isinstance(actual,(int,float)) or isinstance(actual,bool) or not math.isclose(actual,expected,rel_tol=1e-10,abs_tol=1e-12):
                errors.append(f'{coord}: expected {expected!r}, got {actual!r}')
        elif actual != expected:errors.append(f'{coord}: expected {expected!r}, got {actual!r}')
    for r in range(3,10):
        if w[f'F{r}'].number_format!='0.00%':errors.append(f'F{r}: expected 0.00% format')
        for c in (4,5):
            if '%' in w.cell(r,c).number_format:errors.append(f'{w.cell(r,c).coordinate}: share must be percentage-point units')
    # Flatten the nonempty notes/key cells in row-major order: their absolute
    # coordinates, section spacing, and decorative merge widths are irrelevant.
    after=[]
    for row in w.iter_rows(min_row=10):
        for c in row:
            if c.value is not None:
                try: after.append(calc.cell(c.coordinate))
                except Exception:after.append(c.value)
    expected_section=['Notes',reference['notes'][0],reference['notes'][1],
                      'Key',reference['notes'][2],reference['notes'][3]]
    if after!=expected_section:errors.append('Notes / Key changed, missing, duplicated, reordered or extra text')
    # No unaccounted values in the data region: the header+record schema is exact.
    if len(errors)>60:errors=errors[:60]
    return {'hard_task_success':int(not errors),'error_count':len(errors),'errors':errors[:40]}

if __name__=='__main__':
    file=Path(sys.argv[1]) if len(sys.argv)>1 else BASE/'gold_output.xlsx'
    result=evaluate(file)
    print(json.dumps(result,indent=2,ensure_ascii=False))
    sys.exit(0 if result['hard_task_success'] else 1)
