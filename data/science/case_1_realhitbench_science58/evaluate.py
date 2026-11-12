#!/usr/bin/env python3
"""Independent evaluator for Science58; validates facts, layout, structure and arithmetic.

Allows numeric results or safely parsed arithmetic formulas using local cell refs.
Does not execute macros, external links, Excel, or submitted Python code.
"""
from __future__ import annotations
import ast
import json
import math
import re
import sys
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.utils.cell import column_index_from_string

HERE=Path(__file__).resolve().parent
HEADERS=['Set','Treatment','TNF Treatment','siRNA Target'] + [f'{g}_Expt{e}_repli{r}_Ct' for g in ('CD40','b-actin') for e in (1,2,3) for r in (1,2)]
TARGETS=['None','Control','Runx1','Runx3','Runx1 + Runx3']
CELLREF=re.compile(r'(?<![A-Za-z0-9_])\$?([A-Z]{1,3})\$?([1-9][0-9]*)(?![A-Za-z0-9_])')


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
    expected=[]
    for i in range(0,10,2):
        neg,pos=raw[i:i+2]
        if neg[2]!='No' or pos[2]!='Yes' or neg[3]!=pos[3] or neg[3]!=TARGETS[i//2]:
            raise ValueError('Invalid source pair')
        expected.extend([neg,pos,[f'Diff {neg[0]} vs {pos[0]}','+TNF minus -TNF','Difference',neg[3]]+[pos[j]-neg[j] for j in range(4,16)]])
    return expected


def evaluate_cell(sheet, cell, seen=None):
    """Safely evaluate arithmetic in a formula; only local refs and +,-,*,/, parentheses.
    No functions, range operators, external references, calls or names.
    """
    if seen is None:seen=set()
    address=cell.coordinate
    if address in seen:raise ValueError('Cyclic formula: '+address)
    if cell.data_type!='f':
        if isinstance(cell.value,bool) or not isinstance(cell.value,(int,float)):
            raise ValueError(f'Non-numeric value: {address}={cell.value!r}')
        v=float(cell.value)
        if not math.isfinite(v):raise ValueError('Non-finite')
        return v
    expr=str(cell.value)[1:]
    if len(expr)>200 or any(c in expr for c in '!:;[]"\'{}'):
        raise ValueError('Unsupported formula syntax: '+address)
    references={}
    def sub(m):
        col, row=m.groups()
        idx=column_index_from_string(col)
        r=int(row)
        if idx>16 or r>16:raise ValueError('Reference out of range')
        key=f'cell_{len(references)}'
        references[key]=sheet.cell(r,idx)
        return key
    expr=CELLREF.sub(sub,expr)
    tree=ast.parse(expr,mode='eval')
    def walk(node,depth=0):
        if depth>16:raise ValueError('Deep formula')
        if isinstance(node,ast.Expression):return walk(node.body,depth+1)
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):return float(node.value)
        if isinstance(node,ast.Name) and node.id in references:
            return evaluate_cell(sheet,references[node.id],seen|{address})
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            n=walk(node.operand,depth+1);return n if isinstance(node.op,ast.UAdd) else -n
        if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Sub,ast.Mult,ast.Div)):
            left=walk(node.left,depth+1);right=walk(node.right,depth+1)
            if isinstance(node.op,ast.Add):return left+right
            if isinstance(node.op,ast.Sub):return left-right
            if isinstance(node.op,ast.Mult):return left*right
            if right==0:raise ValueError('Divide by zero')
            return left/right
        raise ValueError('Unsupported formula node: '+type(node).__name__)
    v=walk(tree)
    if not math.isfinite(v):raise ValueError('Non-finite result')
    return v


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
    if s.max_row!=16 or s.max_column!=16:
        errors.append(f'Expected 16 rows including header and 16 columns, got {s.max_row}x{s.max_column}')
    if s.merged_cells.ranges:
        errors.append('Output must have flat, unmerged header and no merged data cells')
    seenheaders=[s.cell(1,c).value for c in range(1,17)]
    if seenheaders!=HEADERS:
        errors.append('Header hierarchy mapping or column order incorrect')
    if errors:return status
    status['schema_success']=1
    expected=expected_rows()
    originalok=0;diffok=0;valid_count=0
    for offset,want in enumerate(expected):
        r=offset+2
        valid=True
        for c in range(1,5):
            actual=s.cell(r,c).value
            if actual!=want[c-1]:
                errors.append(f'{s.cell(r,c).coordinate}: expected {want[c-1]!r}, got {actual!r}')
                valid=False
        for c in range(5,17):
            cell=s.cell(r,c)
            try:
                actual=evaluate_cell(s,cell)
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