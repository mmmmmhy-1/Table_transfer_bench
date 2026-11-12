#!/usr/bin/env python3
"""Rebuild JTS0402 OP7+OP2 Gold from input.xlsx, without reading a reference Gold.

Requires openpyxl; preserves source data types and writes cached numeric formula values.
"""
from __future__ import annotations
import json, tempfile, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT=Path(__file__).resolve().parent
SRC=load_workbook(ROOT/'input.xlsx',read_only=True,data_only=True)
SW=SRC.active;SW.reset_dimensions()
source=list(SW.iter_rows(values_only=True))
assert len(source)>=368 and source[6][:4]==('Region','LA_Code','LA_Name','PS_pop')
assert len(source[7:368])==361
codes=source[5][:31];fields=source[6][:31]
MODES=['Public transport / walking','Cycling','Car']
METRICS=['Average minimum journey time (min)', 'Origin indicator: accessible schools (mean number)', 'Destination indicator: children with access (%)']
LEAVES=['Nearest primary school']+[f'Within {x} min' for x in (15,30,45,60)]*2
URL='https://www.gov.uk/government/publications/journey-time-statistics-guidance'
W=Workbook();S=W.active;S.title='Primary School Accessibility';S.sheet_view.showGridLines=False
for r,t in [(1,'Primary Schools | Journey Time and Accessibility | England 2014'),(2,'Department for Transport | JTS0402 | Local Authority'),(3,'Origin = reachable schools; Destination = children able to reach >=1 school; source codes in header notes')]:
    S.merge_cells(start_row=r,start_column=1,end_row=r,end_column=32)
    c=S.cell(r,1,t);c.font=Font(name='Aptos',size=13 if r==1 else 10,bold=r==1,color='FFFFFF' if r==1 else '465A6E');c.fill=PatternFill('solid',fgColor='234263' if r==1 else 'EDF3F8');c.alignment=Alignment(vertical='center',indent=1)
    S.row_dimensions[r].height=36 if r==1 else 25
geo=['Region','LA code','Local authority','Primary-school-age population (5–10)']
for col,label in enumerate(geo,1):
    S.merge_cells(start_row=4,start_column=col,end_row=6,end_column=col)
    c=S.cell(4,col,label);c.font=Font(bold=True,color='FFFFFF',size=10);c.fill=PatternFill('solid',fgColor='315575');c.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
    c.comment=Comment(f'Original field: {fields[col-1]}\nOriginal indicator: {codes[col-1]}','Source provenance')
for m,mode in enumerate(MODES):
    base=5+9*m;color=['24608A','187E81','996934'][m]
    S.merge_cells(start_row=4,start_column=base,end_row=4,end_column=base+8)
    c=S.cell(4,base,mode);c.font=Font(bold=True,color='FFFFFF');c.fill=PatternFill('solid',fgColor=color);c.alignment=Alignment(horizontal='center',vertical='center')
    for off,last,metric in [(0,0,METRICS[0]),(1,4,METRICS[1]),(5,8,METRICS[2])]:
        if off!=last:S.merge_cells(start_row=5,start_column=base+off,end_row=5,end_column=base+last)
        c=S.cell(5,base+off,metric);c.font=Font(bold=True,color='FFFFFF',size=10);c.fill=PatternFill('solid',fgColor=color);c.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
    for k,leaf in enumerate(LEAVES):
        col=base+k;c=S.cell(6,col,leaf);c.font=Font(bold=True,color='19314B',size=10);c.fill=PatternFill('solid',fgColor='E7F0F7');c.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
        c.comment=Comment(f'Original indicator: {codes[col-1]}\nOriginal field: {fields[col-1]}\nSource: {URL}','Source provenance')
for r,txt in [(4,'Derived comparison'),(5,'Average minimum journey time gap (min)'),(6,'Public transport / walking - Car')]:
    c=S.cell(r,32,txt);c.font=Font(bold=True,color='FFFFFF' if r<6 else '2B2650',size=10);c.fill=PatternFill('solid',fgColor='4E4678' if r==4 else '6C6198' if r==5 else 'EBE5F7');c.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
S.cell(6,32).comment=Comment('Formula: PSPTt (PS101) - PSCart (PS119); units minutes.','Source provenance')
S.row_dimensions[4].height=32;S.row_dimensions[5].height=48;S.row_dimensions[6].height=39
for col,width in [(1,24),(2,16),(3,34),(4,25),(32,32)]:S.column_dimensions[get_column_letter(col)].width=width
for col in range(5,32):S.column_dimensions[get_column_letter(col)].width=21 if col in (5,14,23) else 16
cached={}
for idx,row in enumerate(source[7:368]):
    out=7+idx
    for col,v in enumerate(row[:31],1):
        c=S.cell(out,col,v);c.font=Font(name='Aptos',size=10,color='17324A');c.alignment=Alignment(horizontal='left' if col<=3 else 'right',vertical='center')
        c.fill=PatternFill('solid',fgColor='F5F9FC' if idx%2==0 else 'FFFFFF')
        c.number_format=('@' if col==2 else '#,##0' if col==4 else '0" min"' if col in (5,14,23) else '0"%"' if col in list(range(10,14))+list(range(19,23))+list(range(28,32)) else '0')
        if col==3 and isinstance(v,str) and v.startswith(' '):c.alignment=Alignment(horizontal='left',vertical='center',indent=1)
    c=S.cell(out,32,f'=E{out}-W{out}');c.font=Font(name='Aptos',size=10);c.fill=PatternFill('solid',fgColor='EEE8F9' if idx%2 else 'F7F3FE');c.number_format='0.##;[Red]-0.##;0'
    cached[out]=row[4]-row[22]
    S.row_dimensions[out].height=19
# Vertical Region merges on contiguous identical runs; keep all distinct data rows.
pos=0;regions=[]
while pos<361:
    j=pos+1
    while j<361 and source[7+j][0]==source[7+pos][0]:j+=1
    first,last=pos+7,j+6
    if first<last:S.merge_cells(start_row=first,start_column=1,end_row=last,end_column=1)
    S.cell(first,1).alignment=Alignment(vertical='top',indent=1)
    regions.append((first,last,source[7+pos][0]));pos=j
S.freeze_panes='E7';S.print_title_rows='1:6';S.sheet_view.zoomScale=75
S.print_area='A1:AF367';S.page_setup.orientation='landscape';S.page_setup.fitToWidth=1
output=ROOT/'gold_output.xlsx';W.save(output)
# Patch formula cache (openpyxl otherwise leaves empty <v> for formulas).
ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
with tempfile.NamedTemporaryFile(suffix='.xlsx',delete=False,dir=ROOT) as tf: tmp=Path(tf.name)
try:
    with zipfile.ZipFile(output) as zsrc, zipfile.ZipFile(tmp,'w') as zdst:
        for item in zsrc.infolist():
            data=zsrc.read(item.filename)
            if item.filename=='xl/worksheets/sheet1.xml':
                root=ET.fromstring(data);written=0
                for cell in root.iter(ns+'c'):
                    a=cell.get('r','')
                    if not a.startswith('AF') or not a[2:].isdigit():continue
                    r=int(a[2:]);v=cached.get(r)
                    if v is None:continue
                    assert cell.find(ns+'f').text==f'E{r}-W{r}'
                    val=cell.find(ns+'v')
                    if val is None:val=ET.SubElement(cell,ns+'v')
                    val.text=repr(v);written+=1
                assert written==361
                data=ET.tostring(root,encoding='utf-8',xml_declaration=True)
            zdst.writestr(item,data)
    tmp.replace(output)
finally:
    tmp.unlink(missing_ok=True)
print(f'Built {output}; rows=361; columns=32; formula caches=361; region groups={len(regions)}')
