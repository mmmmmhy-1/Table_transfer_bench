#!/usr/bin/env python3
"""Validate the Business13 OP1+OP2 demo; accept correct uncached formulas."""
from pathlib import Path
from openpyxl import load_workbook
import json, math, re, sys
ROOT=Path(__file__).resolve().parent
def valid_formula(formula,row):
    if not isinstance(formula,str) or not formula.startswith("="):return False
    s=re.sub(r"\s+","",formula).upper()
    b,c=f"B{row}",f"C{row}"
    return s in (f"=({c}-{b})/{b}",f'=IF({b}=0,"",({c}-{b})/{b})',
                 f'=IFERROR(({c}-{b})/{b},"")')
def evaluate(path):
    try:
        wb=load_workbook(path,data_only=False);data=load_workbook(path,data_only=True)
    except Exception as e:return {"hard_task_success":0,"error_count":1,"errors":[str(e)]}
    canonical=json.loads((ROOT/"gold_canonical.json").read_text(encoding="utf-8"))
    errors=[]
    if wb.sheetnames!=[canonical["sheet"]]:errors.append("Wrong worksheet names or count")
    w=wb.active;d=data.active
    if (d.max_row,d.max_column)!=(17,6):errors.append("Expected A1:F17")
    expect=set(canonical["header_merges"])|{f"B{r}:F{r}" for r in range(12,18)}
    actual={str(x) for x in w.merged_cells.ranges}
    if actual!=expect:errors.append("Incorrect merged ranges")
    for r in range(1,max(d.max_row,17)+1):
        for col in range(1,max(d.max_column,6)+1):
            cell=d.cell(r,col);c=w[cell.coordinate];addr=cell.coordinate
            need=canonical["cells"].get(addr);got=cell.value
            if addr in canonical["growth_values"] and c.data_type=="f":
                if not valid_formula(c.value,r):errors.append(f"{addr}: invalid formula")
                elif got is None:continue
            if isinstance(need,(float,int)) and not isinstance(need,bool):
                if isinstance(got,bool) or not isinstance(got,(float,int)) or not math.isclose(got,need,rel_tol=1e-10,abs_tol=1e-12):
                    errors.append(f"{addr}: expected {need!r}, got {got!r}")
            elif got!=need:errors.append(f"{addr}: expected {need!r}, got {got!r}")
    for r in range(3,10):
        if w[f"F{r}"].number_format!="0.00%":errors.append(f"F{r}: percent format")
        for col in (4,5):
            if w.cell(r,col).number_format not in ("0.0","0.00"):errors.append(f"{w.cell(r,col).coordinate}: share format")
    return {"hard_task_success":int(not errors),"error_count":len(errors),"errors":errors[:40]}
if __name__=="__main__":
    path=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/"gold_output.xlsx"
    result=evaluate(path)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    sys.exit(0 if result["hard_task_success"] else 1)
