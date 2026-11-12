"""Offline upstream -> input -> Gold audit independent of builder/evaluator logic."""
from collections import defaultdict
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import json
import re

from lxml import html
from openpyxl import load_workbook

HERE=Path(__file__).resolve().parent


def verify_source():
    metadata=json.loads((HERE/'metadata.json').read_text(encoding='utf-8'))
    snapshot=(HERE/metadata['source']['upstream_snapshot_path']).read_bytes()
    assert sha256(snapshot).hexdigest()==metadata['source']['upstream_snapshot_sha256']
    # Expand HTML spans before selecting measurement fields; blank separators are omitted.
    grid={}
    rows=html.fromstring(snapshot).xpath('//table//tr')
    for r,row in enumerate(rows):
        col=0
        for cell in row.xpath('./td|./th'):
            while (r,col) in grid:
                col+=1
            value=cell.text_content().strip()
            width=int(cell.get('colspan','1'))
            height=int(cell.get('rowspan','1'))
            for dr in range(height):
                for dc in range(width):
                    grid[r+dr,col+dc]=value
            col+=width
    measure_cols=[col for (r,col),value in grid.items() if r==3 and value.lower()=='ct']
    measure_cols.sort()
    assert len(rows)==14 and len(measure_cols)==12
    paths=['_'.join(grid[r,col] for r in range(3))+'_Ct' for col in measure_cols]
    source=load_workbook(HERE/'input.xlsx',data_only=True)
    gold=load_workbook(HERE/'gold_output.xlsx',data_only=True)
    canonical=json.loads((HERE/'gold_canonical.json').read_text(encoding='utf-8'))
    try:
        sheet=source.active
        def source_header(row,col):
            for merged in sheet.merged_cells.ranges:
                if merged.min_row<=row<=merged.max_row and merged.min_col<=col<=merged.max_col:
                    return sheet.cell(merged.min_row,merged.min_col).value
            return sheet.cell(row,col).value
        assert paths==['_'.join(str(source_header(r,c)) for r in range(1,4))+'_Ct' for c in range(3,15)]
        assert canonical['headers'][4:]==paths
        assert [gold.active.cell(1,c).value for c in range(5,17)]==paths
        mapping={'DC-siRNA':'None','DC+CtrlsiRNA':'Control','DC+Runx1siRNA':'Runx1',
                 'DC+Runx3siRNA':'Runx3','DC+Runx1+3siRNA':'Runx1 + Runx3'}
        pairs=defaultdict(dict)
        raw=[]
        max_input_error=Decimal(0)
        for r in range(4,14):
            sid,treatment=grid[r,0],grid[r,1]
            assert [sheet.cell(r+1,c).value for c in (1,2)]==[sid,treatment]
            compact=re.sub(r'\s+','',treatment)
            match=re.fullmatch(r'(.+)([+-])TNF',compact)
            assert match, treatment
            target=mapping[match[1]]
            state='Yes' if match[2]=='+' else 'No'
            values=[Decimal(grid[r,c]) for c in measure_cols]
            for c,value in enumerate(values,3):
                error=abs(Decimal(str(sheet.cell(r+1,c).value))-value)
                max_input_error=max(max_input_error,error)
                assert error<=Decimal('1e-12'), (sid,c,error)
            record=[sid,treatment,state,target]+values
            raw.append(record)
            assert state not in pairs[target]
            pairs[target][state]=record
        expected=[]
        for target,pair in pairs.items():
            assert set(pair)=={'No','Yes'}
            neg,pos=pair['No'],pair['Yes']
            diff=[f'Diff {neg[0]} vs {pos[0]}','+TNF minus -TNF','Difference',target]
            expected.extend([neg,pos,diff+[p-n for n,p in zip(neg[4:],pos[4:])]])
        assert [row[0] for row in expected if not row[0].startswith('Diff')]==[row[0] for row in raw]
        assert len(canonical['data_rows'])==15 and gold.active.max_row==16
        max_gold_error=Decimal(0)
        for i,want in enumerate(expected):
            canonical_row=canonical['data_rows'][i]
            assert canonical_row['row_type']==('difference' if i%3==2 else 'positive' if i%3==1 else 'negative')
            if i%3==2:
                assert canonical_row['comparison']=={'minus_set':expected[i-2][0],'plus_set':expected[i-1][0]}
            for c,value in enumerate(want,1):
                for actual in (gold.active.cell(i+2,c).value,canonical_row['values'][c-1]):
                    if c<=4:
                        assert actual==value,(i,c,actual,value)
                    else:
                        assert type(actual) in (int,float)
                        error=abs(Decimal(str(actual))-value)
                        max_gold_error=max(max_gold_error,error)
                        assert error<=Decimal('1e-9'),(i,c,error)
        return dict(upstream_url=metadata['source']['upstream_snapshot_url'],
                    upstream_sha256=sha256(snapshot).hexdigest(),
                    source_ct_values_checked=120,semantic_header_paths_checked=12,
                    source_identifier_cells_checked=20,gold_numeric_values_checked=180,
                    canonical_numeric_values_checked=180,
                    max_input_absolute_error=str(max_input_error),
                    max_gold_or_canonical_absolute_error=str(max_gold_error))
    finally:
        source.close()
        gold.close()


if __name__=='__main__':
    print(json.dumps(verify_source(),indent=2))
