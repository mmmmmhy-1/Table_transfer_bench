#!/usr/bin/env python3
"""Positive equivalence checks and negative fault injection for this case."""
from copy import copy
from pathlib import Path
from tempfile import TemporaryDirectory
from openpyxl import load_workbook
from evaluate import evaluate

HERE=Path(__file__).resolve().parent
REF=HERE/'gold_output.xlsx'

def save_modified(path, change):
    wb=load_workbook(REF)
    change(wb.active)
    wb.save(path)

def main():
    result=evaluate(REF)
    assert result['hard_task_success']==1, result
    assert result['numeric_cells_correct']==180,result
    assert result['original_rows_correct']==10,result
    assert result['difference_rows_correct']==5,result
    with TemporaryDirectory() as d:
        d=Path(d)
        # Alternative legal representation: replace formula by equivalent numeric constant.
        from openpyxl import load_workbook
        cached=load_workbook(REF,data_only=True)
        number=cached.active['E4'].value
        save_modified(d/'valid_number.xlsx',lambda s: setattr(s['E4'],'value',number))
        assert evaluate(d/'valid_number.xlsx')['hard_task_success']==1

        cases={
            'wrong_sign':lambda s:setattr(s['E4'],'value','=E2-E3'),
            'wrong_replicate':lambda s:setattr(s['E4'],'value','=F3-E2'),
            'wrong_gene':lambda s:setattr(s['E4'],'value','=K3-E2'),
            'wrong_ct':lambda s:setattr(s['F2'],'value',99),
            'wrong_tnf':lambda s:setattr(s['C3'],'value','No'),
            'wrong_target':lambda s:setattr(s['D15'],'value','Runx1'),
            'wrong_pair_label':lambda s:setattr(s['A4'],'value','Diff Set2 vs Set1'),
            'wrong_source_treatment':lambda s:setattr(s['B2'],'value','DC -siRNA + TNF'),
            'wrong_heading':lambda s:setattr(s['E1'],'value','CD40_Expt2_repli1_Ct'),
            'wrong_precision':lambda s:setattr(s['E2'],'value',round(float(s['E2'].value),3)),
            'missing_measurement':lambda s:setattr(s['G12'],'value',None),
            'unsupported_function':lambda s:setattr(s['E4'],'value','=SUM(E3,-E2)'),
            'merged_header':lambda s:s.merge_cells('E1:F1'),
            'extra_row':lambda s:s.append(['extra']),
            'missing_row':lambda s:s.delete_rows(7),
        }
        for name,change in cases.items():
            filename=d/(name+'.xlsx')
            save_modified(filename,change)
            outcome=evaluate(filename)
            assert outcome['hard_task_success']==0,(name,outcome)
            print('PASS rejected',name)
    print('PASS reference / equivalent representation / 15 negative injections')

if __name__=='__main__':main()