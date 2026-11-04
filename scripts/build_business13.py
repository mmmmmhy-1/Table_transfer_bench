#!/usr/bin/env python3
"""Rebuild public RealHiTBench business13 demo from source-transcribed table data."""
from pathlib import Path
from tempfile import NamedTemporaryFile
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED
import json, os
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment

DEST=Path(__file__).resolve().parents[1]/"data/business/case_1_realhitbench_business13"
ROWS=[
("Bahrain",61,47,0.9,0.7),
("Kuwait",6,4,0.1,0.1),
("Oman",2,3,0.0,0.0),
("Qatar",69,100,1.0,1.6),
("Saudi Arabia",51,67,0.8,1.0),
("UAE",206,196,3.0,3.1),
("World total",6779,6433,100.0,100.0),
]
EXPORT="Exports of services (£m)"
SHARE="Percentage of telecoms world total"
GROWTH="Export services YoY growth (2015 vs 2014)"
NOTES=["1. Data cover exports of services only (not goods)",
"2. Data are in current prices (i.e. have not been adjusted for inflation)."]
KEYS=['"-" Figure has been suppressed due to disclosiveness',
'"0" The value of trade is less than £0.5 million (figures in this table are rounded to the nearest million)']

def pretty(w, widths):
    w.sheet_view.showGridLines=False
    for c,width in widths.items():w.column_dimensions[c].width=width
    for row in w:
        for cell in row: cell.alignment=Alignment(vertical="center",wrap_text=(cell.row<=2))
    for row in (1,2) if w.title=="Exports of services" else (1,):
        for cell in w[row]:
            cell.fill=PatternFill("solid",fgColor="244B65")
            if cell.value is not None:cell.font=Font(bold=True,color="FFFFFF")
            cell.alignment=Alignment(vertical="center",horizontal="center",wrap_text=True)
    for row in w:w.row_dimensions[row[0].row].height=23
    w.row_dimensions[1].height=38
    w.freeze_panes="B3" if w.title=="Exports of services" else "A2"

def make_input():
    b=Workbook();w=b.active;w.title="Long Data"
    w.append(["Country","Metric","Year","Value"])
    for country,a,c,x,y in ROWS:
        for metric, pairs in ((EXPORT,[(2014,a),(2015,c)]),(SHARE,[(2014,x),(2015,y)])):
            for year,value in pairs:w.append([country,metric,year,value])
    w["A32"]="Notes";w["B33"]=NOTES[0];w["B34"]=NOTES[1]
    w["A35"]="Key";w["B36"]=KEYS[0];w["B37"]=KEYS[1]
    for row in range(32,38):w.merge_cells(start_row=row,start_column=2,end_row=row,end_column=4)
    pretty(w,{"A":25,"B":49,"C":14,"D":20})
    for row in range(2,30):w.cell(row,4).number_format="0.0" if w.cell(row,2).value==SHARE else "#,##0"
    return b

def make_gold():
    b=Workbook();w=b.active;w.title="Exports of services"
    for rg in ("A1:A2","B1:C1","D1:E1","F1:F2"):w.merge_cells(rg)
    for cell,value in {"A1":"Country","B1":EXPORT,"D1":SHARE,"F1":GROWTH,
                       "B2":"2014","C2":"2015","D2":"2014","E2":"2015"}.items():w[cell]=value
    for row,(name,a,c,x,y) in enumerate(ROWS,3):
        for col,val in enumerate((name,a,c,x,y),1):w.cell(row,col,val)
        w.cell(row,6,f'=IF(B{row}=0,"",(C{row}-B{row})/B{row})')
        w.cell(row,6).number_format="0.00%"
        for col in (2,3):w.cell(row,col).number_format="#,##0"
        for col in (4,5):w.cell(row,col).number_format="0.0"
    w["A12"]="Notes";w["B13"]=NOTES[0];w["B14"]=NOTES[1]
    w["A15"]="Key";w["B16"]=KEYS[0];w["B17"]=KEYS[1]
    for row in range(12,18):w.merge_cells(start_row=row,start_column=2,end_row=row,end_column=6)
    pretty(w,{"A":26,"B":25,"C":25,"D":25,"E":25,"F":35})
    w.row_dimensions[2].height=27
    for row in (13,14,16,17):w.row_dimensions[row].height=35
    return b

def cache_growth(path):
    ns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    with ZipFile(path,"r") as z:
        parts={key:z.read(key) for key in z.namelist()}
    root=ET.fromstring(parts["xl/worksheets/sheet1.xml"])
    for row,(_,a,c,_,_) in enumerate(ROWS,3):
        addr=f"F{row}"
        target=next(el for el in root.iter(f"{{{ns}}}c") if el.attrib.get("r")==addr)
        value=target.find(f"{{{ns}}}v")
        if value is None:value=ET.SubElement(target,f"{{{ns}}}v")
        value.text=repr((c-a)/a)
    parts["xl/worksheets/sheet1.xml"]=ET.tostring(root,encoding="utf-8",xml_declaration=True)
    with NamedTemporaryFile(dir=path.parent,suffix=".xlsx",delete=False) as tmp:temp=Path(tmp.name)
    try:
        with ZipFile(temp,"w",ZIP_DEFLATED) as z:
            for name,data in parts.items():z.writestr(name,data)
        os.replace(temp,path)
    finally:
        if temp.exists():temp.unlink()

def canonical(gold):
    w=gold.active
    cells={}
    for row in w:
        for c in row:
            if c.value is not None:
                cells[c.coordinate]=(ROWS[c.row-3][2]-ROWS[c.row-3][1])/ROWS[c.row-3][1] if c.data_type=="f" else c.value
    return {"sheet":"Exports of services","header_merges":["A1:A2","B1:C1","D1:E1","F1:F2"],
            "cells":cells,"growth_values":{f"F{r}":(c-a)/a for r,(_,a,c,_,_) in enumerate(ROWS,3)},
            "source_data":ROWS,"notes":NOTES+KEYS}

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    source=make_input()
    source.save(DEST/"input.xlsx")
    gold=make_gold()
    gold.save(DEST/"gold_output.xlsx")
    cache_growth(DEST/"gold_output.xlsx")
    (DEST/"gold_canonical.json").write_text(json.dumps(canonical(gold),indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("business13: rebuilt input, gold and canonical")
if __name__=="__main__":main()
