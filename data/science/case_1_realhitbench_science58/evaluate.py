#!/usr/bin/env python3
"""Independent evaluator for Science58; validates facts, layout, structure and arithmetic.

Allows numeric results or the shared safely parsed offline Excel formula subset.
Does not execute macros, external links, Excel, or submitted Python code.
"""
from __future__ import annotations
import json
import math
import re
import sys
from pathlib import Path
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts.formula_eval import SpreadsheetFormulaEvaluator

HERE=Path(__file__).resolve().parent
HEADERS=['Set','Treatment','TNF Treatment','siRNA Target'] + [f'{g}_Expt{e}_repli{r}_Ct' for g in ('CD40','b-actin') for e in (1,2,3) for r in (1,2)]
TARGETS=['None','Control','Runx1','Runx3','Runx1 + Runx3']


def decode_treatment(raw):
    s=''.join(raw.lower().split())
    # Must be parsed from the final TNF suffix, not any earlier '+' character.
    suffix=re.search(r'([+-])tnf$',s)
    if suffix is None:raise ValueError('Unrecognized TNF state in '+raw)
    state='Yes' if suffix.group(1)=='+' else 'No'
    pre=s[:suffix.start()]
    if 'runx1+3sirna' in pre or 'runx1+runx3sirna' in pre:target='Runx1 + Runx3'
    elif 'runx1sirna' in pre:target='Runx1'
    elif 'runx3sirna' in pre:target='Runx3'
    elif 'ctrlsirna' in pre:target='Control'
    elif '-sirna' in pre:target='None'
    else:raise ValueError('Unrecognized siRNA target in '+raw)
    return state,target


def expected_rows():
    src=load_workbook(HERE/'input.xlsx',read_only=True,data_only=True)
    s=src.active
    if len(src.sheetnames)!=1:raise ValueError('Source must be single-sheet')
    if s.max_row!=14 or s.max_column!=14:raise ValueError('Unexpected source dimensions')
    if [s.cell(1,j).value for j in (3,9)]!=['CD40','b-actin']:raise ValueError('Unexpected gene hierarchy')
    if [s.cell(2,j).value for j in (3,5,7,9,11,13)]!=['Expt1','Expt2','Expt3']*2:raise ValueError('Unexpected Expt hierarchy')
    if [s.cell(3,j).value for j in range(3,15)]!=['repli1','repli2']*6:raise ValueError('Unexpected replicate hierarchy')
    if [str(s.cell(4,j).value).lower() for j in range(3,15)]!=['ct']*12:raise ValueError('Unexpected measurement hierarchy')
    raw=[]
    for r in range(5,15):
        sid=s.cell(r,1).value
        assert sid=='Set'+str(r-4)
        treat=s.cell(r,2).value
        state,target=decode_treatment(treat)
        # These are source facts, read independently of the published Gold.
        raw.append([sid,treat,state,target]+[float(s.cell(r,c).value) for c in range(3,15)])
    src.close()
    expected=[]
    for i in range(0,10,2):
        neg,pos=raw[i:i+2]
        if neg[2]!='No' or pos[2]!='Yes' or neg[3]!=pos[3] or neg[3]!=TARGETS[i//2]:
            raise ValueError('Invalid source pair')
        expected.extend([neg,pos,[f'Diff {neg[0]} vs {pos[0]}','+TNF minus -TNF','Difference',neg[3]]+[pos[j]-neg[j] for j in range(4,16)]])
    return expected


def evaluate_cell(calculator, cell):
    value=calculator.cell(cell.coordinate)
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('Expected a finite numeric Excel value at '+cell.coordinate)
    return float(value)


def evaluate(path):
    errors=[]
    status={'hard_task_success':0,'schema_success':0,'original_rows_correct':0,'difference_rows_correct':0,'numeric_cells_correct':0,'checked_numeric_cells':0,'errors':errors}
    try:
        book=load_workbook(path,read_only=False,data_only=False,keep_links=False)
    except Exception as e:
        errors.append('Cannot load workbook: '+str(e));return status
    if book.sheetnames!=['TNF Comparison']:
        errors.append(f'Expected only sheet TNF Comparison; got {book.sheetnames}')
        return status
    s=book.active
    # Ignore styling-only cells and blank outer margins; preserve logical table shape.
    # Sparse access avoids iterating a huge rectangular styling-only used range.
    populated=[cell for cell in s._cells.values() if cell.value is not None]
    if not populated:
        errors.append('Empty output table');return status
    top=min(cell.row for cell in populated)
    left=min(cell.column for cell in populated)
    bottom=max(cell.row for cell in populated)
    right=max(cell.column for cell in populated)
    if (bottom-top+1,right-left+1)!=(16,16):
        errors.append('Expected one contiguous 16-by-16 content table including header')
        return status
    for merged in s.merged_cells.ranges:
        intersects=(merged.min_row<=bottom and merged.max_row>=top and
                    merged.min_col<=right and merged.max_col>=left)
        if intersects and (merged.min_row!=merged.max_row or merged.min_col!=merged.max_col):
            errors.append('Output table must have flat, unmerged header and data cells')
    seenheaders=[s.cell(top,c).value for c in range(left,left+16)]
    if seenheaders!=HEADERS:
        errors.append('Header hierarchy mapping or column order incorrect')
    if errors:return status
    status['schema_success']=1
    calculator=SpreadsheetFormulaEvaluator(s)
    expected=expected_rows()
    originalok=0;diffok=0;valid_count=0
    for offset,want in enumerate(expected):
        r=top+offset+1
        valid=True
        for c in range(1,5):
            actual=s.cell(r,left+c-1).value
            if actual!=want[c-1]:
                errors.append(f'{s.cell(r,left+c-1).coordinate}: expected {want[c-1]!r}, got {actual!r}')
                valid=False
        for c in range(5,17):
            cell=s.cell(r,left+c-1)
            try:
                actual=evaluate_cell(calculator,cell)
                target=want[c-1]
                status['checked_numeric_cells']+=1
                if not math.isclose(actual,target,rel_tol=1e-12,abs_tol=1e-9):
                    errors.append(f'{cell.coordinate}: wrong Ct / paired difference {actual:.12g} != {target:.12g}')
                    valid=False
                else:valid_count+=1
            except Exception as e:
                errors.append(f'{cell.coordinate}: {e}')
                valid=False
        if offset%3==2:
            diffok+=int(valid)
        else:originalok+=int(valid)
    status['original_rows_correct']=originalok
    status['difference_rows_correct']=diffok
    status['numeric_cells_correct']=valid_count
    status['hard_task_success']=int(len(errors)==0)
    # Keep diagnostics bounded for tool-use reports, while failure still considers all errors.
    if len(errors)>50:
        status['error_count']=len(errors)
        del errors[50:]
    return status


def main():
    candidate=Path(sys.argv[1]) if len(sys.argv)>1 else HERE/'gold_output.xlsx'
    result=evaluate(candidate)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result['hard_task_success'] else 1)

if __name__=='__main__':main()
