#!/usr/bin/env python3
"""Executable regression tests for public examples (run after workbook generators)."""
from pathlib import Path
from tempfile import TemporaryDirectory
from importlib.util import spec_from_file_location, module_from_spec
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ROOT/'data/environment/case_1_realhitbench_environment21',
    ROOT/'data/labor/case_1_realhitbench_labor43',
    ROOT/'data/business/case_1_realhitbench_business13',
]

def load_evaluator(case):
    spec = spec_from_file_location('eval_'+case.name,case/'evaluate.py')
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.evaluate

def main():
    for case in CASES:
        eval_case = load_evaluator(case)
        ref = case/'gold_output.xlsx'
        r=eval_case(ref)
        assert r['hard_task_success']==1,(case,r)
        with TemporaryDirectory() as temp:
            temp=Path(temp)
            changed=load_workbook(ref)
            w=changed.active
            name=case.name
            if 'business' in name: w['C3']=999999
            elif 'labor' in name: w['E2']='corrupted skill'
            else: w['B7']=999999
            out=temp/'bad_content.xlsx';changed.save(out)
            assert eval_case(out)['hard_task_success']==0,(name,'bad content accepted')
            changed=load_workbook(ref)
            w=changed.active
            if 'business' in name: w.unmerge_cells('B1:C1')
            elif 'labor' in name: w.unmerge_cells('A2:A4')
            else: w.unmerge_cells('C4:F4')
            out=temp/'bad_merge.xlsx';changed.save(out)
            assert eval_case(out)['hard_task_success']==0,(name,'bad merge accepted')
            changed=load_workbook(ref)
            w=changed.active
            if 'business' in name:
                w['F3']='=C3/B3-1'
            elif 'labor' in name:
                w['B2']='=COUNTA(C2:C4)'
            else:
                w['G7']='=SUM(B7:F7)'
            out=temp/'valid_uncached.xlsx';changed.save(out)
            assert eval_case(out)['hard_task_success']==1,(name,'valid uncached rejected',eval_case(out))
            changed=load_workbook(ref)
            w=changed.active
            if 'business' in name:w['F3']='=C3/B3+1'
            elif 'labor' in name:w['B2']='=COUNTA(C2:C4)+1'
            else:w['G7']='=SUM(B7:F7)+1'
            out=temp/'invalid_uncached.xlsx';changed.save(out)
            assert eval_case(out)['hard_task_success']==0,(name,'wrong uncached accepted')
        print('PASS', name)
if __name__=='__main__': main()
