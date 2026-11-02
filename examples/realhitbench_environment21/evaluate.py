#!/usr/bin/env python3
"""Case-specific strict evaluator. Run: python evaluate.py /path/to/submission.xlsx."""
import sys,json,math
from pathlib import Path
from openpyxl import load_workbook
BASE=Path(__file__).resolve().parent

def evaluate(path):
    gold=load_workbook(BASE/"gold_output.xlsx",data_only=True)
    sub=load_workbook(path,data_only=True)
    errors=[]
    if len(sub.sheetnames)!=1:errors.append("Expected exactly one worksheet")
    sw=sub.active;gw=gold.active
    if sw.max_column!=7:errors.append("Expected seven columns")
    need={"A4:A5","B4:B5","C4:F4","G4:G5"}
    actual={str(x) for x in sw.merged_cells.ranges}
    if not need.issubset(actual):errors.append("Incorrect merged header ranges")
    for cell,value in {"A4":"Species of animal","B4":"No anaesthesia","C4":"Type of anaesthesia","G4":"Total"}.items():
        if sw[cell].value!=value:errors.append("Wrong header "+cell)
    for row in range(1,33):
        for col in range(1,8):
            a=sw.cell(row,col).value;b=gw.cell(row,col).value
            same=(math.isclose(a,b,rel_tol=1e-11,abs_tol=1e-12) if isinstance(a,(int,float)) and isinstance(b,(int,float)) else a==b)
            if not same:errors.append(f"{sw.cell(row,col).coordinate}: expected {b!r}, got {a!r}")
    for row in sw.iter_rows(min_row=33):
        if any(c.value is not None for c in row):
            errors.append("Extra populated rows");break
    for r,label in ((6,"Mammal"),(19,"Primate")):
        if sw.cell(r,1).value!=label:errors.append("Missing group "+label)
    for r in (20,21):
        if (sw.cell(r,1).alignment.indent or 0)<2:errors.append("Incorrect child indent at "+str(r))
    for r in (29,30):
        for c in range(2,8):
            if sw.cell(r,c).number_format not in ("0%","0%;[Red]-0%;0%"):
                errors.append("Wrong percentage format at "+sw.cell(r,c).coordinate)
    return {"hard_task_success":int(not errors),"error_count":len(errors),"errors":errors[:40]}

if __name__=="__main__":
    f=Path(sys.argv[1]) if len(sys.argv)>1 else BASE/"gold_output.xlsx"
    outcome=evaluate(f)
    print(json.dumps(outcome,ensure_ascii=False,indent=2))
    raise SystemExit(0 if outcome["hard_task_success"] else 1)
