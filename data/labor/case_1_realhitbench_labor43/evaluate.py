#!/usr/bin/env python3
"""Evaluate grouped labor long-form content, counts, and required merges."""
from pathlib import Path
from openpyxl import load_workbook
import json, sys, math
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts.formula_eval import SpreadsheetFormulaEvaluator, FormulaError
BASE=Path(__file__).resolve().parent

def evaluate(path):
    try:
        c=json.loads((BASE/'gold_canonical.json').read_text(encoding='utf-8'))
        wb=load_workbook(path,data_only=False)
        values=load_workbook(path,data_only=True)
    except Exception as exc:return {'hard_task_success':0,'error_count':1,'errors':[str(exc)]}
    errors=[]
    if wb.sheetnames!=[c['sheet_name']]:errors.append('Incorrect sheet name/count')
    w=wb.active
    if w.max_row!=c['used_rows'] or w.max_column!=c['used_columns']:
        errors.append('Workbook dimensions differ from specified schema')
    expected=set(c['merged_ranges'])
    actual={str(x) for x in w.merged_cells.ranges
            if x.min_row != x.max_row or x.min_col != x.max_col}
    if expected!=actual:errors.append('Merge mismatch: missing '+str(sorted(expected-actual)[:10])+' extra '+str(sorted(actual-expected)[:10]))
    calc=SpreadsheetFormulaEvaluator(w,values.active)
    for row in range(1,max(c['used_rows'],w.max_row)+1):
        for col in range(1,max(c['used_columns'],w.max_column)+1):
            coordinate=w.cell(row,col).coordinate;need=c['cells'].get(coordinate)
            try:have=calc.cell(coordinate)
            except Exception as exc:
                errors.append(f'{coordinate}: invalid formula {exc}');continue
            if isinstance(need,(int,float)) and not isinstance(need,bool):
                if not isinstance(have,(int,float)) or isinstance(have,bool) or not math.isclose(have,need,abs_tol=1e-9,rel_tol=1e-12):
                    errors.append(f'{coordinate}: expected {need!r}, got {have!r}')
            elif have!=need:errors.append(f'{coordinate}: expected {need!r}, got {have!r}')
            if len(errors)>100:break
        if len(errors)>100:break
    return {'hard_task_success':int(not errors),'error_count':len(errors),'errors':errors[:40]}

if __name__=='__main__':
    target=Path(sys.argv[1]) if len(sys.argv)>1 else BASE/'gold_output.xlsx'
    result=evaluate(target)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    sys.exit(0 if result['hard_task_success'] else 1)
