#!/usr/bin/env python3
"""Positive equivalence checks and negative fault injection for this case."""
from copy import copy
from pathlib import Path
from tempfile import TemporaryDirectory
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill
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

        def restyle(s):
            for row in s:
                for cell in row:
                    cell.font=Font(name='Arial',size=14,color='123456')
                    cell.fill=PatternFill('solid',fgColor='EEEEEE')
            s.row_dimensions[1].height=60
            s.column_dimensions['E'].width=35

        def blank_styled_extent(s):
            s['XFD1048576'].fill=PatternFill('solid',fgColor='FFFF00')

        def shift_table(s):
            s.move_range('A1:P16',rows=2,cols=1,translate=True)

        positives={
            'valid_SUM':lambda s:setattr(s['E4'],'value','=SUM(E3,-E2)'),
            'valid_absolute_lowercase':lambda s:setattr(s['E4'],'value','= $e$3 - $e$2'),
            'valid_parentheses':lambda s:setattr(s['E4'],'value','=(E3 + (-E2))'),
            'valid_styles':restyle,
            'valid_blank_styled_extent':blank_styled_extent,
            'valid_blank_margins':shift_table,
            'valid_singleton_merge':lambda s:s.merge_cells('E1:E1'),
        }
        for name,change in positives.items():
            filename=d/(name+'.xlsx')
            save_modified(filename,change)
            outcome=evaluate(filename)
            assert outcome['hard_task_success']==1,(name,outcome)
            print('PASS accepted',name)

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
            'wrong_SUM':lambda s:setattr(s['E4'],'value','=SUM(E3,E2)'),
            'numeric_text':lambda s:setattr(s['E2'],'value',str(s['E2'].value)),
            'boolean_measurement':lambda s:setattr(s['E2'],'value',True),
            'cyclic_formula':lambda s:setattr(s['E4'],'value','=E4'),
            'external_formula':lambda s:setattr(s['E4'],'value',"='[other.xlsx]Sheet1'!E3-E2"),
            'unsupported_function':lambda s:setattr(s['E4'],'value','=INDIRECT("E3")-E2'),
            'python_numeric_literal':lambda s:setattr(s['E4'],'value','=0x10'),
            'invalid_whitespace_literal':lambda s:setattr(s['E2'],'value','=2 3'),
            'wrong_formula_with_space':lambda s:setattr(s['E4'],'value','= E2 - E3'),
            'merged_header':lambda s:s.merge_cells('E1:F1'),
            'extra_row':lambda s:s.append(['extra']),
            'missing_row':lambda s:s.delete_rows(7),
            'duplicate_row':lambda s:s.append([c.value for c in s[2]]),
            'extra_column':lambda s:setattr(s['Q1'],'value','extra'),
            'duplicate_pair_row':lambda s:setattr(s['A5'],'value','Set1'),
            'wrong_sheet_name':lambda s:setattr(s,'title','Other'),
        }
        for name,change in cases.items():
            filename=d/(name+'.xlsx')
            save_modified(filename,change)
            outcome=evaluate(filename)
            assert outcome['hard_task_success']==0,(name,outcome)
            print('PASS rejected',name)
        wb=load_workbook(REF)
        wb.create_sheet('Unrequested')
        wb.save(d/'extra_sheet.xlsx')
        assert evaluate(d/'extra_sheet.xlsx')['hard_task_success']==0
    summary={'reference':1,'equivalent_outputs':len(positives)+1,'negative_injections':len(cases)+1}
    print('PASS',summary)
    return summary

if __name__=='__main__':main()
