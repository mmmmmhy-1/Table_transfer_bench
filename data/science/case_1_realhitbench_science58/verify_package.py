#!/usr/bin/env python3
"""Package audit, source preservation, cached formulas, and annotation consistency."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
import sys
from openpyxl import load_workbook
from evaluate import evaluate, expected_rows
from verify_source import verify_source
ROOT=Path(__file__).resolve().parent

def main():
    upstream_audit=verify_source()
    m=json.loads((ROOT/'metadata.json').read_text(encoding='utf-8'))
    c=json.loads((ROOT/'gold_canonical.json').read_text(encoding='utf-8'))
    assert m['benchmark_version']=='2.2'
    assert set(m['operations'])=={'OP3','OP4','OP7'}
    assert m['structure_tags']==['S1','S3']
    ids={x['id'] for x in m['operation_nodes']}
    assert all(a in ids and b in ids for a,b in m['dependency_edges'])
    assert m['dependency_edges']==[['extract_treatment_factors','insert_paired_tnf_differences']]
    discovery=(ROOT/'instruction.txt').read_text(encoding='utf-8')
    guided=(ROOT/'instruction_guided.txt').read_text(encoding='utf-8')
    assert guided.endswith(discovery), 'Guided must add structure locations to identical business requirements'
    assert c['headers']==list(list(load_workbook(ROOT/'gold_output.xlsx',data_only=True).active.values)[0])
    assert c['data_rows'][2]['comparison']['minus_set']=='Set1'
    assert c['data_rows'][-1]['comparison']['plus_set']=='Set10'
    src=load_workbook(ROOT/'input.xlsx',data_only=True);s=src.active
    gold=load_workbook(ROOT/'gold_output.xlsx',data_only=True)
    form=load_workbook(ROOT/'gold_output.xlsx',data_only=False)
    assert len(s.merged_cells.ranges)==9 and len(form.active.merged_cells.ranges)==0
    assert sum(1 for row in s.iter_rows(min_row=5,min_col=3,max_col=14) for v in row if isinstance(v.value,str))==2
    assert len(gold.sheetnames)==1 and gold.active.max_row==16 and gold.active.max_column==16
    assert sum(1 for row in form.active.iter_rows() for x in row if x.data_type=='f')==60
    original=expected_rows()
    errors=[];counts={'raw_ct':0,'differences':0}
    for i in range(15):
        for col in range(5,17):
            actual=gold.active.cell(i+2,col).value
            expect=original[i][col-1]
            if not isinstance(actual,(int,float)) or abs(actual-expect)>1e-9:
                errors.append([i+2,col,actual,expect])
            counts['differences' if i%3==2 else 'raw_ct']+=1
    assert not errors,errors[:5]
    assert not any(str(value) in discovery for row in original for value in row[4:])
    with TemporaryDirectory() as temporary:
        temporary=Path(temporary)
        for name in ('input.xlsx','build_gold.py'):
            shutil.copyfile(ROOT/name,temporary/name)
        subprocess.run([sys.executable,str(temporary/'build_gold.py')],check=True,capture_output=True,text=True)
        rebuilt=json.loads((temporary/'gold_canonical.json').read_text(encoding='utf-8'))
        assert rebuilt==c, 'Rebuilt canonical reference changed'
        for data_only in (True,False):
            actual=load_workbook(temporary/'gold_output.xlsx',data_only=data_only)
            reference=gold if data_only else form
            assert actual.sheetnames==reference.sheetnames
            assert list(actual.active.values)==list(reference.active.values), 'Gold rebuild differs'
            actual.close()
    result=evaluate(ROOT/'gold_output.xlsx')
    assert result['hard_task_success']==1,result
    report={
        'case_id':m['case_id'],
        'benchmark_version':'2.2',
        'checker_version':m['evaluation']['checker_version'],
        'automated_prompt_checks':{
            'guided_has_identical_discovery_business_requirements':guided.endswith(discovery),
            'discovery_contains_no_literal_source_or_difference_numeric_answers':
                not any(str(value) in discovery for row in original for value in row[4:])
        },
        'upstream_independent_audit':upstream_audit,
        'semantic_gold_rebuild_matches':True,
        'dependency_edges':m['dependency_edges'],
        'input_sha256':hashlib.sha256((ROOT/'input.xlsx').read_bytes()).hexdigest(),
        'gold_sha256':hashlib.sha256((ROOT/'gold_output.xlsx').read_bytes()).hexdigest(),
        'input_merged_regions':len(s.merged_cells.ranges),
        'output_merged_regions':len(form.active.merged_cells.ranges),
        'original_set_rows':10,
        'generated_difference_rows':5,
        'output_columns':16,
        'original_ct_values_checked':counts['raw_ct'],
        'difference_values_checked':counts['differences'],
        'formula_cells_checked':60,
        'reference_hard_task_success':result['hard_task_success'],
        'independent_match_errors':errors,
        'numeric_tolerance_abs':1e-9,
        'review_note':'Deterministic source, Gold, prompt parity and evaluator audit; no model/API run and no independent human research review. L4 is heuristic; OP7 is parallel to the OP4 -> OP3 dependency, and source pairs are adjacent.'
    }
    (ROOT/'audit_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
