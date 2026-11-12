#!/usr/bin/env python3
"""Independent, source-grounded JTS0402 OP7+OP2 evaluator (not a Gold-file comparison)."""
from __future__ import annotations
import json, math, re, sys
from pathlib import Path
from openpyxl import load_workbook

HERE = Path(__file__).resolve().parent
MODE_NAMES = ['Public transport / walking', 'Cycling', 'Car']
METRICS = ['Average minimum journey time (min)',
           'Origin indicator: accessible schools (mean number)',
           'Destination indicator: children with access (%)']
LEAVES = ['Nearest primary school'] + [f'Within {x} min' for x in (15,30,45,60)] * 2
GEO = ['Region','LA code','Local authority','Primary-school-age population (5–10)']
DERIVED = ['Derived comparison','Average minimum journey time gap (min)',
           'Public transport / walking - Car']


def compare(candidate: Path) -> dict:
    errors=[]
    try:
        src=load_workbook(HERE/'input.xlsx',read_only=True,data_only=True)
        src_ws=src.active;src_ws.reset_dimensions()
        rows=[r[:31] for n,r in enumerate(src_ws.iter_rows(values_only=True),1) if 8 <= n <= 368]
        fw=load_workbook(candidate,data_only=False)
        vw=load_workbook(candidate,data_only=True)
    except Exception as exc:
        return {'success':False,'errors':[f'Failed to open input or output: {exc}']}
    if len(fw.worksheets)!=1:
        errors.append(f'Exactly one worksheet required; got {len(fw.worksheets)}')
    ws=fw.active;cached=vw.active
    if ws.max_column!=32:errors.append(f'Expected 32 columns; found {ws.max_column}')
    # Find level-one header row without requiring one fixed number of title rows.
    headers=[r for r in range(1,min(16,ws.max_row)+1)
             if ws.cell(r,5).value==MODE_NAMES[0]
             and ws.cell(r,14).value==MODE_NAMES[1]
             and ws.cell(r,23).value==MODE_NAMES[2]]
    if len(headers)!=1:
        errors.append(f'Expected exactly one 3-mode header row; found {headers}')
        return {'success':False,'errors':errors}
    h=headers[0];start=h+3;end=start+360
    if ws.max_row!=end:errors.append(f'Expected exactly 361 data rows ending at row {end}; got last row {ws.max_row}')
    expected_merges=set()
    for col in range(1,5):
        expected_merges.add((h,col,h+2,col))
        if ws.cell(h,col).value != GEO[col-1]: errors.append(f'Geography header {col} mismatch')
    for mi,mode in enumerate(MODE_NAMES):
        first=5+mi*9
        expected_merges.add((h,first,h,first+8))
        if ws.cell(h,first).value!=mode:errors.append(f'Mode header {mode} mismatch')
        for off,metric_index,stop in ((0,0,0),(1,1,4),(5,2,8)):
            c=first+off
            if off<stop: expected_merges.add((h+1,c,h+1,first+stop))
            if ws.cell(h+1,c).value!=METRICS[metric_index]:
                errors.append(f'Metric header {c} mismatch')
        for off,label in enumerate(LEAVES):
            c=first+off
            if ws.cell(h+2,c).value != label:errors.append(f'Leaf header {c} mismatch')
    for t,v in enumerate(DERIVED):
        if ws.cell(h+t,32).value!=v:errors.append(f'Derived header row {h+t} mismatch')
    actual_merges={(m.min_row,m.min_col,m.max_row,m.max_col) for m in ws.merged_cells.ranges}
    missing=expected_merges-actual_merges
    if missing: errors.append(f'Missing {len(missing)} mandatory header merges: {sorted(missing)[:5]}')
    # All semantic group ranges in the header must be present. Do not demand title merges.
    if len(rows)!=361:errors.append('Source does not contain exactly 361 records')
    value_errors=[];gap_errors=[];formula_errors=[];region_errors=[]
    by_region=[];region_start=0
    while region_start<len(rows):
        region_end=region_start+1
        while region_end<len(rows) and rows[region_end][0]==rows[region_start][0]:region_end+=1
        by_region.append((start+region_start,start+region_end-1,rows[region_start][0]))
        region_start=region_end
    for first,last,name in by_region:
        if first<last and (first,1,last,1) not in actual_merges:
            region_errors.append(f'Expected merged Region {name} rows {first}:{last}')
    for idx,source_row in enumerate(rows):
        r=start+idx
        for col,expected in enumerate(source_row,1):
            if col==1:
                # First row of each actual source Region group should have the name;
                # any other row should be empty due to a proper vertical merge.
                first=next(a for a,b,n in by_region if a<=r<=b)
                cell=ws.cell(r,1)
                if r==first and cell.value != expected:region_errors.append(f'Region first-row mismatch at {r}')
                elif r!=first and cell.value is not None:region_errors.append(f'Region inner cell not merged at {r}')
                continue
            actual=cached.cell(r,col).value
            if actual!=expected:value_errors.append((r,col,expected,actual))
        pt,car=source_row[4],source_row[22]
        expected_gap=pt-car
        formula=ws.cell(r,32).value
        value=cached.cell(r,32).value
        if isinstance(formula,str) and formula.startswith('='):
            normalized=formula.replace('$','').replace(' ','').upper()
            if normalized != f'=E{r}-W{r}':formula_errors.append((r,formula))
        elif isinstance(formula,(float,int)) and not isinstance(formula,bool):pass
        else:formula_errors.append((r,formula))
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isclose(value,expected_gap,rel_tol=1e-12,abs_tol=1e-9):
            gap_errors.append((r,expected_gap,value))
    if value_errors: errors.append(f'{len(value_errors)} original source values changed; first: {value_errors[:3]}')
    if region_errors:errors.append(f'{len(region_errors)} Region grouping errors; first: {region_errors[:3]}')
    if formula_errors:errors.append(f'{len(formula_errors)} invalid formula/value expressions; first: {formula_errors[:3]}')
    if gap_errors:errors.append(f'{len(gap_errors)} incorrect or uncached signed gap values; first: {gap_errors[:3]}')
    # Output must retain source code mapping as Excel header comments (one field per original column).
    source_fields=list(load_workbook(HERE/'input.xlsx',data_only=True,read_only=False).active.iter_rows(min_row=6,max_row=7,max_col=31,values_only=True))
    id_row,code_row=source_fields
    comment_errors=[]
    for col in range(1,32):
        cell=ws.cell(h if col<=4 else h+2,col)
        comment=(cell.comment.text if cell.comment else '')
        if str(id_row[col-1]) not in comment or str(code_row[col-1]) not in comment:
            comment_errors.append(col)
    if comment_errors:errors.append(f'Missing source-field traceability in header comments at columns {comment_errors[:8]}')
    return {'success':not errors,'errors':errors,'data_rows':len(rows),'original_value_cells_checked':len(rows)*31,
            'derived_values_checked':len(rows),'mandatory_header_merges':len(expected_merges),
            'region_groups':len(by_region),'operation_labels':['OP7','OP2']}

if __name__=='__main__':
    result=compare(Path(sys.argv[1]) if len(sys.argv)>1 else HERE/'gold_output.xlsx')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    sys.exit(0 if result['success'] else 1)
