#!/usr/bin/env python3
"""Validate labor43 OP1+OP2 output. Usage: python evaluate.py submission.xlsx"""
from pathlib import Path
from openpyxl import load_workbook
import json,sys,math
BASE=Path(__file__).resolve().parent
def evaluate(path):
    c=json.loads((BASE/"gold_canonical.json").read_text(encoding="utf-8"))
    try:
        wb=load_workbook(path,data_only=False)
        vals=load_workbook(path,data_only=True)
    except Exception as ex:return {"hard_task_success":0,"error_count":1,"errors":[str(ex)]}
    errors=[]
    if wb.sheetnames!=[c["sheet_name"]]: errors.append("Expected one correctly named sheet")
    w=wb.active;v=vals.active
    if w.max_row!=c["used_rows"] or w.max_column!=c["used_columns"]:errors.append("Wrong workbook dimensions")
    expected=set(c["merged_ranges"]); actual={str(x) for x in w.merged_cells.ranges}
    if expected!=actual: errors.append("Wrong merged regions: missing="+str(sorted(expected-actual)[:10])+" extra="+str(sorted(actual-expected)[:10]))
    for row in range(1,max(c["used_rows"],w.max_row)+1):
        for col in range(1,max(c["used_columns"],w.max_column)+1):
            cell=w.cell(row,col)
            coord=cell.coordinate
            need=c["cells"].get(coord)
            have=v[coord].value
            if isinstance(need,(int,float)) and not isinstance(need,bool):
                if not isinstance(have,(int,float)) or not math.isclose(have,need,abs_tol=1e-9,rel_tol=1e-12):
                    # A formula with no cached value may still be accepted only for a precise,
                    # matching expression against the employee/company block.
                    if cell.data_type=="f" and have is None:
                        group=(c["company_blocks"] if col==2 else c["employee_blocks"] if col==4 else [])
                        block=next((x for x in group if x["start"]==row),None)
                        rng=("C" if col==2 else "E")+str(row)+":"+("C" if col==2 else "E")+str(block["end"]) if block else None
                        if rng and str(cell.value).replace(" ","").upper()=="=COUNTA("+rng+")":continue
                    errors.append(coord+": expected numeric "+repr(need)+", got "+repr(have))
            elif have!=need: errors.append(coord+": expected "+repr(need)+", got "+repr(have))
            if len(errors)>150:break
        if len(errors)>150:break
    return {"hard_task_success":int(not errors),"error_count":len(errors),"errors":errors[:50]}
if __name__=="__main__":
    target=Path(sys.argv[1]) if len(sys.argv)>1 else BASE/"gold_output.xlsx"
    result=evaluate(target)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    sys.exit(0 if result["hard_task_success"] else 1)
