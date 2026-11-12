#!/usr/bin/env python3
"""Rebuild Gold deterministically from the released long-format input.xlsx."""
from __future__ import annotations
from collections import OrderedDict
from pathlib import Path
from statistics import mean,stdev
from math import sqrt
import os,zipfile
from xml.etree import ElementTree as ET
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.comments import Comment
from openpyxl.utils import get_column_letter

ROOT=Path(__file__).resolve().parent
input_wb=load_workbook(ROOT/'input.xlsx',data_only=True)
records=list(input_wb.active.iter_rows(min_row=2,max_col=5,values_only=True))
assert len(records)==67
by=OrderedDict()
for animal,genotype,group,treat,value in records:
    by.setdefault((genotype,group),OrderedDict()).setdefault(treat,[]).append((str(animal),value))
assert tuple(by)==(('WT','Control'),('WT','Stress'),('FGF2KO','Stress'))

wb=Workbook();s=wb.active;s.title='Wide Treatment Groups';s.sheet_view.showGridLines=False
fill=lambda x:PatternFill('solid',fgColor=x)
navy='1D3557';teal='137C83';purple='6D56A4';gray='64748B';ink='1F2937'
center=Alignment(horizontal='center',vertical='center',wrap_text=True)
s.merge_cells('A1:G1');s['A1']='EMOTIONALITY INDEX  |  TREATMENT-BASED WIDE FORMAT';s['A1'].fill=fill(navy);s['A1'].font=Font(name='Aptos Display',size=16,bold=True,color='FFFFFF');s['A1'].alignment=Alignment(horizontal='left',vertical='center',indent=1);s.row_dimensions[1].height=40
s.merge_cells('A2:G2');s['A2']='Individual animals preserved  •  independently sampled treatment groups  •  Mean / sample SD / SEM regenerated';s['A2'].font=Font(name='Aptos',size=10,italic=True,color=gray);s['A2'].alignment=Alignment(horizontal='left',vertical='center',indent=1);s.row_dimensions[2].height=27
for col,txt in zip('ABC',['Genotype','Experimental Group','Record / Statistic']):
    s.merge_cells(f'{col}3:{col}4');c=s[f'{col}3'];c.value=txt;c.fill=fill(navy);c.font=Font(name='Aptos',bold=True,color='FFFFFF');c.alignment=center
for a,b,label,color in [('D','E','Vehicle',teal),('F','G','Fluoxetine',purple)]:
    s.merge_cells(f'{a}3:{b}3');c=s[f'{a}3'];c.value=label;c.fill=fill(color);c.font=Font(name='Aptos',bold=True,color='FFFFFF');c.alignment=center
for col,txt,color in [('D','Animal ID','D7EEF0'),('E','Emotionality Index','D7EEF0'),('F','Animal ID','EEE9F8'),('G','Emotionality Index','EEE9F8')]:
    c=s[f'{col}4'];c.value=txt;c.fill=fill(color);c.font=Font(name='Aptos',bold=True,color=ink,size=10);c.alignment=center
for col,width in {'A':16,'B':22,'C':22,'D':20,'E':22,'F':20,'G':22}.items():s.column_dimensions[col].width=width
s.row_dimensions[3].height=28;s.row_dimensions[4].height=33
caches={}
for idx,((genotype,group),cohorts) in enumerate(by.items()):
    v=cohorts['Vehicle'];f=cohorts['Fluoxetine'];n=max(len(v),len(f));start=s.max_row+1
    for i in range(n):
        r=s.max_row+1;s.cell(r,3,i+1)
        for c,rows in [(4,v),(6,f)]:
            if i<len(rows):
                animal,value=rows[i];s.cell(r,c,animal).number_format='@';s.cell(r,c+1,value).number_format='0.00;[Red](0.00);0.00'
        for cell in s[r][:7]:
            cell.font=Font(name='Aptos',size=10,color=ink);cell.alignment=center
            if i%2==0:cell.fill=fill('F5FAFA' if idx%2==0 else 'F7F6FB')
        s.row_dimensions[r].height=24
    end=s.max_row
    for label in ('Mean','Sample SD','SEM'):
        r=s.max_row+1;s.cell(r,3,label)
        for col,rows in [(5,v),(7,f)]:
            vals=[x[1] for x in rows];rng=f'{get_column_letter(col)}{start}:{get_column_letter(col)}{end}'
            formula={'Mean':f'=AVERAGE({rng})','Sample SD':f'=STDEV.S({rng})','SEM':f'=STDEV.S({rng})/SQRT(COUNT({rng}))'}[label]
            value={'Mean':lambda:mean(vals),'Sample SD':lambda:stdev(vals),'SEM':lambda:stdev(vals)/sqrt(len(vals))}[label]()
            s.cell(r,col,formula).number_format='0.000000';caches[f'{get_column_letter(col)}{r}']=value
        for cell in s[r][:7]:cell.fill=fill('E8F5EE' if label=='Mean' else 'FCF1DD');cell.font=Font(name='Aptos',bold=True,size=10,color=navy);cell.alignment=center
        s.row_dimensions[r].height=27
    for col,val in [(1,genotype),(2,group)]:
        s.merge_cells(start_row=start,start_column=col,end_row=s.max_row,end_column=col)
        cell=s.cell(start,col,val);cell.fill=fill('E9F2F7');cell.font=Font(name='Aptos',size=11,bold=True,color=navy);cell.alignment=center
    for col in range(1,8):s.cell(s.max_row,col).border=Border(bottom=Side(style='medium',color='AAC5D4'))
assert s.max_row==48 and len(caches)==18
s.freeze_panes='D5';s.print_area='A1:G48';s.sheet_view.zoomScale=85
s['D3'].comment=Comment('Rows align independent animals by treatment-local ordinal, NOT paired biological observations.','Benchmark')
path=ROOT/'gold_output.xlsx';wb.save(path)
ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
tmp=path.with_suffix('.tmp.xlsx')
with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp,'w') as zout:
    for item in zin.infolist():
        body=zin.read(item.filename)
        if item.filename=='xl/worksheets/sheet1.xml':
            tree=ET.fromstring(body);seen=set()
            for c in tree.iter(ns+'c'):
                addr=c.attrib.get('r')
                if addr in caches:
                    assert c.find(ns+'f') is not None
                    v=c.find(ns+'v')
                    if v is None:v=ET.SubElement(c,ns+'v')
                    v.text=repr(caches[addr]);seen.add(addr)
            assert len(seen)==18
            body=ET.tostring(tree,encoding='utf-8',xml_declaration=True)
        zout.writestr(item,body)
os.replace(tmp,path)
print(path)
