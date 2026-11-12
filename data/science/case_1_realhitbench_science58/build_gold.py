#!/usr/bin/env python3
"""Deterministic Science58 V2.2 reference builder; no network required."""
from __future__ import annotations
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties

HERE=Path(__file__).resolve().parent
MEASURE=[f'{gene}_Expt{exp}_repli{rep}_Ct' for gene in ('CD40','b-actin') for exp in range(1,4) for rep in (1,2)]
HEADERS=['Set','Treatment','TNF Treatment','siRNA Target']+MEASURE
TARGETS=['None','Control','Runx1','Runx3','Runx1 + Runx3']


def parse_condition(s):
    t=re.sub(r'\s+','',s).lower()
    matched=re.search(r'([+-])tnf$',t)
    if not matched:raise ValueError('Unexpected TNF condition: '+s)
    sign=matched.group(1)
    before=t[:matched.start()]
    if 'runx1+3sirna' in before or 'runx1+runx3sirna' in before:target='Runx1 + Runx3'
    elif 'runx1sirna' in before:target='Runx1'
    elif 'runx3sirna' in before:target='Runx3'
    elif 'ctrlsirna' in before:target='Control'
    elif '-sirna' in before:target='None'
    else:raise ValueError('Unexpected siRNA condition: '+s)
    return ('Yes' if sign=='+' else 'No',target)


def extract():
    inp=load_workbook(HERE/'input.xlsx',read_only=False,data_only=True)
    if len(inp.worksheets)!=1:raise ValueError('Expected one source sheet')
    sheet=inp.active
    assert sheet.max_row==14 and sheet.max_column==14, (sheet.max_row,sheet.max_column)
    # Independently validate source's hierarchy, not only its final positional values.
    assert [sheet.cell(1,c).value for c in (3,9)]==['CD40','b-actin']
    assert [sheet.cell(2,c).value for c in (3,5,7,9,11,13)]==['Expt1','Expt2','Expt3']*2
    assert [sheet.cell(3,c).value for c in range(3,15)]==['repli1','repli2']*6
    assert all(sheet.cell(4,c).value.lower()=='ct' for c in range(3,15))
    rows=[]
    for r in range(5,15):
        sid=sheet.cell(r,1).value
        text=sheet.cell(r,2).value
        assert sid==f'Set{r-4}'
        tn, target=parse_condition(text)
        nums=[]
        for c in range(3,15):
            value=sheet.cell(r,c).value
            if value in (None,''):raise ValueError(f'Missing source Ct at {r},{c}')
            num=float(value)
            assert 0<num<100, (r,c,value)
            nums.append(num)
        rows.append([sid,text,tn,target]+nums)
    assert all(rows[i][2]=='No' and rows[i+1][2]=='Yes' and rows[i][3]==rows[i+1][3] for i in range(0,10,2))
    assert [rows[i][3] for i in range(0,10,2)]==TARGETS
    return rows


def install_caches(path, values):
    namespace='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    ET.register_namespace('',namespace)
    tmp=path.with_suffix('.tmp.xlsx')
    n=0
    with zipfile.ZipFile(path) as zi, zipfile.ZipFile(tmp,'w') as zo:
        for info in zi.infolist():
            content=zi.read(info.filename)
            if info.filename=='xl/worksheets/sheet1.xml':
                xml=ET.fromstring(content)
                for cell in xml.findall('.//{%s}c'%namespace):
                    coord=cell.get('r')
                    if coord not in values:continue
                    assert cell.find('{%s}f'%namespace) is not None
                    target=cell.find('{%s}v'%namespace)
                    if target is None:target=ET.SubElement(cell,'{%s}v'%namespace)
                    target.text=format(values[coord],'.15g')
                    n+=1
                content=ET.tostring(xml,encoding='utf-8',xml_declaration=True)
            zo.writestr(info,content)
    assert n==60,n
    tmp.replace(path)


def main():
    data=extract()
    wb=Workbook(); ws=wb.active;ws.title='TNF Comparison';ws.sheet_view.showGridLines=False
    navy='213B5C';light='EEF4FA';mint='E9F5EF';white='FFFFFF'
    for c,h in enumerate(HEADERS,1):
        x=ws.cell(1,c,h);x.fill=PatternFill('solid',fgColor=navy);x.font=Font(name='Aptos',bold=True,color=white,size=10)
        x.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
        ws.column_dimensions[get_column_letter(c)].width=22 if c>=5 else (18 if c!=2 else 31)
    ws.row_dimensions[1].height=42
    ws.freeze_panes='E2'
    cache={};canonical=[]
    for i in range(0,len(data),2):
        minus,plus=data[i:i+2]
        first=ws.max_row+1
        for rowkind,row in (('negative',minus),('positive',plus)):
            ws.append(row)
            r=ws.max_row
            ws.row_dimensions[r].height=24
            for c in range(1,17):
                x=ws.cell(r,c)
                x.fill=PatternFill('solid',fgColor=light if rowkind=='negative' else white)
                x.font=Font(name='Aptos',color='28765F' if c>=5 else '3B4B60',size=10)
                x.alignment=Alignment(vertical='center',horizontal='right' if c>=5 else 'left')
                if c>=5:x.number_format='0.000000000000'
            canonical.append({'row_type':rowkind,'values':row})
        r=ws.max_row+1
        prefix=[f'Diff {minus[0]} vs {plus[0]}','+TNF minus -TNF','Difference',minus[3]]
        for c,value in enumerate(prefix,1):ws.cell(r,c,value)
        vals=[]
        for c in range(5,17):
            letter=get_column_letter(c)
            x=ws.cell(r,c,f'={letter}{first+1}-{letter}{first}')
            x.number_format='0.000000000000;[Red](0.000000000000);0.000000000000'
            val=plus[c-1]-minus[c-1]
            cache[x.coordinate]=val
            vals.append(val)
        for c in range(1,17):
            x=ws.cell(r,c)
            x.fill=PatternFill('solid',fgColor=mint)
            x.font=Font(name='Aptos',color='113F39',bold=True,size=10)
            x.alignment=Alignment(vertical='center',horizontal='right' if c>=5 else 'left')
            x.border=Border(top=Side(style='thin',color='9ABFB1'))
        ws.row_dimensions[r].height=25
        canonical.append({'row_type':'difference','values':prefix+vals,'comparison':{'minus_set':minus[0],'plus_set':plus[0]},'formula_rule':'plus_tnf_minus_minus_tnf'})
    assert ws.max_row==16 and ws.max_column==16 and len(cache)==60
    wb.calculation=CalcProperties(calcMode='auto',fullCalcOnLoad=True)
    wb.save(HERE/'gold_output.xlsx')
    install_caches(HERE/'gold_output.xlsx',cache)
    obj={'benchmark_version':'2.2','source_family_id':'RealHiTBench_science58','sheet_name':'TNF Comparison','headers':HEADERS,'data_rows':canonical,'comparison_sign':'Ct(+TNF) - Ct(-TNF)','measure_columns':MEASURE,'source_record_count':10,'difference_row_count':5}
    (HERE/'gold_canonical.json').write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Built gold: 15 data rows, 16 columns, 60 formula cells, 120 raw Ct values')

if __name__=='__main__':main()