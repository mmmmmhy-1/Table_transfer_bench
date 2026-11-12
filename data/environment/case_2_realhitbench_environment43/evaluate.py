#!/usr/bin/env python3
"""Independent evaluator for RealHiTBench environment43 OP1+OP7+OP3 public case.

Checks source animal facts, the specified multi-level header, row groups and summary
statistics. Only the original case input and candidate workbook are consulted.
"""
from __future__ import annotations
import collections
import json
import math
import statistics
import sys
from pathlib import Path
from openpyxl import load_workbook

CASE = Path(__file__).resolve().parent
TOL = 1e-9
REQUIRED = ('WT', 'Control'), ('WT', 'Stress'), ('FGF2KO', 'Stress')
TREATMENTS = ('Vehicle', 'Fluoxetine')

def same(a, b):
    return isinstance(a, (int, float)) and not isinstance(a, bool) and math.isfinite(a) and abs(a-b) <= TOL*max(1, abs(b))

def main(path):
    src=load_workbook(CASE/'input.xlsx',data_only=True)
    s=src.active
    assert src.sheetnames==['Input']
    assert [s.cell(1,c).value for c in range(1,6)] == ['Animal','Genotype','Group','Treatment','Emotionality Index']
    grouped=collections.OrderedDict()
    for animal,genotype,group,treatment,value in s.iter_rows(min_row=2,max_col=5,values_only=True):
        key=(str(genotype),str(group))
        assert treatment in TREATMENTS and isinstance(value,(int,float))
        grouped.setdefault(key,collections.OrderedDict()).setdefault(treatment,[]).append((str(animal),value))
    assert tuple(grouped)==REQUIRED
    assert sum(len(v) for k in grouped for v in grouped[k].values())==67

    wb=load_workbook(path,data_only=False)
    cached=load_workbook(path,data_only=True)
    assert wb.sheetnames==['Wide Treatment Groups'], 'Single worksheet with required name'
    ws=wb.active; wc=cached.active
    assert ws.max_column==7, 'Expected 7 report columns'
    assert [ws.cell(3,c).value for c in (1,2,3,4,6)]==['Genotype','Experimental Group','Record / Statistic','Vehicle','Fluoxetine']
    assert [ws.cell(4,c).value for c in (4,5,6,7)]==['Animal ID','Emotionality Index','Animal ID','Emotionality Index']
    merges={str(m) for m in ws.merged_cells.ranges}
    assert {'A3:A4','B3:B4','C3:C4','D3:E3','F3:G3'} <= merges, 'Missing two-level header merges'
    observed=collections.Counter()
    cursor=5; checks=0
    for genotype,group in REQUIRED:
        v=grouped[(genotype,group)]['Vehicle'];f=grouped[(genotype,group)]['Fluoxetine']
        width=max(len(v),len(f));end=cursor+width-1
        assert ws.cell(cursor,1).value==genotype and ws.cell(cursor,2).value==group
        assert f'A{cursor}:A{end+3}' in merges and f'B{cursor}:B{end+3}' in merges, 'Missing row-group merges'
        for i in range(width):
            r=cursor+i
            assert ws.cell(r,3).value==i+1, 'Incorrect group-local ordinal'
            for tr,items,cid,cval in [('Vehicle',v,4,5),('Fluoxetine',f,6,7)]:
                animal=ws.cell(r,cid).value
                val=wc.cell(r,cval).value
                if i<len(items):
                    assert str(animal)==items[i][0] and same(val,items[i][1]), f'Original record mismatch at row {r}, {tr}'
                    observed[(str(animal),genotype,group,tr,round(val,12))]+=1
                else:
                    assert animal is None and val is None, f'Nonblank missing observation at row {r}'
        for j,label in enumerate(('Mean','Sample SD','SEM')):
            r=end+1+j
            assert ws.cell(r,3).value==label
            assert ws.cell(r,4).value is None and ws.cell(r,6).value is None
            for items,col in [(v,5),(f,7)]:
                vals=[x[1] for x in items]
                expected = (statistics.mean(vals) if label=='Mean' else statistics.stdev(vals) if label=='Sample SD' else statistics.stdev(vals)/math.sqrt(len(vals)))
                raw=ws.cell(r,col).value
                numeric=wc.cell(r,col).value
                if numeric is None and isinstance(raw,str) and raw.startswith('='):
                    # Supported canonical formulas without cached values can be evaluated from the verified data records.
                    letter='E' if col==5 else 'G'
                    src_range=f'{letter}{cursor}:{letter}{end}'
                    allowed={'Mean':f'=AVERAGE({src_range})','Sample SD':f'=STDEV.S({src_range})','SEM':f'=STDEV.S({src_range})/SQRT(COUNT({src_range}))'}
                    assert raw.upper()==allowed[label].upper(), f'Unsupported noncached formula at {r}, {col}'
                    numeric=expected
                assert same(numeric,expected), f'Statistic {label} incorrect at row {r}, col {col}: {numeric} vs {expected}'
                checks+=1
        cursor=end+4
    assert cursor==49 and ws.max_row==48, 'Unexpected row count or extra data'
    assert sum(observed.values())==67
    print(json.dumps({'hard_task_success':1,'source_observations':67,'derived_statistics':checks,'generated_summary_rows':9,'detail_alignment_rows':35,'header_merges_verified':5,'row_group_merges_verified':6}))
    return 0

if __name__=='__main__':
    try:sys.exit(main(Path(sys.argv[1]) if len(sys.argv)>1 else CASE/'gold_output.xlsx'))
    except Exception as e:
        print(json.dumps({'hard_task_success':0,'error':str(e)}),file=sys.stderr)
        sys.exit(1)
