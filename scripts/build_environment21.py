#!/usr/bin/env python3
"""Rebuild the public RealHiTBench environment21 example from source-derived numeric records.
Only for this public example; not an unseen-test generator.
"""
from pathlib import Path
import json
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parents[1] / "data" / "environment" / "realhitbench" / "environment21" / "cases" / "op2_op3_total_statistics"
DATA = [
("Mammal",None,None,None,None,None),
("Mouse",1984204,396591,144433,106142,48393),
("Rat",143674,76465,712,27083,23601),
("All other rodents",11722,2863,548,1721,1081),
("Rabbit",9010,760,1861,1678,2152),
("Cat",148,87,"-","-","-"),
("Dog",3944,264,35,188,121),
("Ferret",83,565,"-",31,12),
("Other carnivore",402,393,"-","-","-"),
("Horse and other equids",362,"-",8014,4,"-"),
("Pig",3269,606,25,19,421),
("Sheep",36362,1019,259,51,23),
("All other ungulates",5418,87,110,"-",2),
("Primate",None,None,None,None,None),
("New World monkey",195,53,"-",33,70),
("Old World monkey",1497,598,"-",6,23),
("All other mammals",401,3,131,"-",10),
("Bird",45092,340,88,116052,1046),
("Reptile",383,"-","-","-","-"),
("Amphibian",15304,430,"-",107,74),
("Fish",434251,77343,85,51516,708),
]
T2010=[2568286,622464,206350,232337,95289]
HEADERS=["General anaesthesia, with recovery","Local anaesthesia","General anaesthesia at end of procedure, without recovery","General anaesthesia throughout, without recovery"]
FOOTNOTE="Note. Neuromuscular blocking agents (NMBA) were used in 2,547 procedures in 2011. All of these procedures involved the use of general anaesthesia."

def render(gold=False):
    wb=Workbook(); w=wb.active; w.title="Table 5"
    w.sheet_view.showGridLines=False
    w.column_dimensions["A"].width=34
    for x in "BCDEF":w.column_dimensions[x].width=35
    w.column_dimensions["G"].width=20
    w.merge_cells("A1:G1" if gold else "A1:F1")
    w["A1"]="Table 5 Scientific procedures by species of animal and level of anaesthesia"
    w["A3"]="Great Britain 2011"
    w.merge_cells("A4:A5");w["A4"]="Species of animal"
    w.merge_cells("B4:B5");w["B4"]="No anaesthesia"
    w.merge_cells("C4:F4");w["C4"]="Type of anaesthesia"
    for col,name in enumerate(HEADERS,3):w.cell(5,col,name)
    if gold:w.merge_cells("G4:G5");w["G4"]="Total"
    for col in range(1,8 if gold else 7):
        for row in (4,5):
            c=w.cell(row,col);c.fill=PatternFill("solid",fgColor="E8ECF2")
            c.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True)
            if c.value is not None:c.font=Font(bold=True,color="283B4A")
    w.row_dimensions[4].height=25;w.row_dimensions[5].height=70
    for row_num, values in enumerate(DATA,6):
        for col,value in enumerate(values,1):
            if value is not None:w.cell(row_num,col,value)
        label=values[0]
        if label in ("Mammal","Primate"):
            for col in range(1,8 if gold else 7):
                w.cell(row_num,col).fill=PatternFill("solid",fgColor="EDF2F6")
            w.cell(row_num,1).font=Font(bold=True,color="35556D")
        elif row_num in (20,21):
            w.cell(row_num,1).alignment=Alignment(indent=2)
        elif row_num<23:
            w.cell(row_num,1).alignment=Alignment(indent=1)
    annual=[sum((row[c] if isinstance(row[c],int) else 0) for row in DATA) for c in range(1,6)]
    assert annual==[2695721,558467,156301,304631,77737]
    for c,v in enumerate(annual,2):w.cell(27,c,v)
    w["A27"]="Total"
    if gold:
        for c in range(2,7):
            a=annual[c-2];b=T2010[c-2]
            w.cell(28,c,a-b)
            w.cell(29,c,(a-b)/abs(b))
            w.cell(30,c,a/sum(annual))
        w["A28"]="Increase on 2010"
        w["A29"]="Percentage change from 2010"
        w["A30"]="Percentage of total for 2011"
    r2010=31 if gold else 28
    w.cell(r2010,1,"2010 Totals")
    for c,v in enumerate(T2010,2):w.cell(r2010,c,v)
    if gold:
        for r in list(range(7,19))+list(range(20,28))+[31]:
            w.cell(r,7,sum((w.cell(r,c).value if isinstance(w.cell(r,c).value,(int,float)) else 0) for c in range(2,7)))
        w["G28"]=sum(annual)-sum(T2010)
        w["G29"]=(sum(annual)-sum(T2010))/sum(T2010)
        w["G30"]=1
        for r in (29,30):
            for c in range(2,8):w.cell(r,c).number_format="0%"
    if gold:
        w["G30"].number_format="0%"
    note_row=32 if gold else 29
    w.merge_cells(start_row=note_row,start_column=1,end_row=note_row,end_column=7 if gold else 6)
    w.cell(note_row,1,FOOTNOTE)
    w.cell(note_row,1).alignment=Alignment(wrap_text=True)
    w.row_dimensions[note_row].height=35
    for row in w.iter_rows(min_row=6,max_row=r2010,min_col=2,max_col=7 if gold else 6):
        for cell in row:
            if isinstance(cell.value,int):cell.number_format='#,##0;[Red]-#,##0;"-"'
    if gold:
        w["G30"].number_format="0%"
    w.freeze_panes="B6"
    return wb

def main():
    HERE.mkdir(parents=True,exist_ok=True)
    for gold,filename in ((False,"input.xlsx"),(True,"gold_output.xlsx")):
        render(gold).save(HERE/filename)
    g=load_workbook(HERE/"gold_output.xlsx",data_only=True).active
    canonical={g.cell(r,c).coordinate:g.cell(r,c).value for r in range(1,33) for c in range(1,8) if g.cell(r,c).value is not None}
    (HERE/"gold_canonical.json").write_text(json.dumps(canonical,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Generated input.xlsx, gold_output.xlsx, gold_canonical.json")

if __name__=="__main__":main()
