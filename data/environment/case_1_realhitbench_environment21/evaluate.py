#!/usr/bin/env python3
"""Evaluate environment21 data and hierarchy, accepting valid uncached formulas."""
from pathlib import Path
from openpyxl import load_workbook
import json,math,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts.formula_eval import SpreadsheetFormulaEvaluator, FormulaError
BASE=Path(__file__).resolve().parent

def evaluate(path):
    try:
        gold=load_workbook(BASE/'gold_output.xlsx',data_only=True)
        book=load_workbook(path,data_only=False)
        cached=load_workbook(path,data_only=True)
    except Exception as exc:return {'hard_task_success':0,'error_count':1,'errors':[str(exc)]}
    errors=[]
    if book.sheetnames!=gold.sheetnames:errors.append('Original sheet name/count must be preserved')
    w=book.active;g=gold.active;calc=SpreadsheetFormulaEvaluator(w,cached.active)
    if w.max_column!=7:errors.append('Expected original fields plus rightmost Total')
    if w.max_row!=32:errors.append('Unexpected row count')
    required={'A4:A5','B4:B5','C4:F4','G4:G5','A1:G1','A32:G32'}
    actual={str(x) for x in w.merged_cells.ranges}
    if not required.issubset(actual):errors.append('Incorrect original/group/Total header or title/footnote merges')
    for row in range(1,max(32,w.max_row)+1):
        for col in range(1,max(7,w.max_column)+1):
            coordinate=w.cell(row,col).coordinate
            need=g.cell(row,col).value if row<=32 and col<=7 else None
            try:have=calc.cell(coordinate)
            except Exception as exc:
                errors.append(f'{coordinate}: unevaluable formula: {exc}');continue
            if isinstance(need,(float,int)) and not isinstance(need,bool):
                if not isinstance(have,(float,int)) or isinstance(have,bool) or not math.isclose(have,need,rel_tol=1e-10,abs_tol=1e-12):
                    errors.append(f'{coordinate}: expected {need!r}, got {have!r}')
            elif have!=need:errors.append(f'{coordinate}: expected {need!r}, got {have!r}')
            if len(errors)>100:break
        if len(errors)>100:break
    for row in (29,30):
        for col in range(2,8):
            if w.cell(row,col).number_format not in ('0%','0%;[Red]-0%;0%'):
                errors.append(f'{w.cell(row,col).coordinate}: wrong percent format')
    return {'hard_task_success':int(not errors),'error_count':len(errors),'errors':errors[:40]}

if __name__=='__main__':
    target=Path(sys.argv[1]) if len(sys.argv)>1 else BASE/'gold_output.xlsx'
    result=evaluate(target)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    sys.exit(0 if result['hard_task_success'] else 1)
