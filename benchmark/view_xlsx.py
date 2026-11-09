"""Expose workbook evidence without inferring headers, groups, or relationships."""
import argparse
import datetime
import json
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils.cell import range_boundaries


def inspect_workbook(path, sheet=None, cell_range=None):
    path = Path(path).resolve()
    if path.suffix.lower() != '.xlsx':
        raise ValueError('Expected an .xlsx workbook')
    wb = load_workbook(path, data_only=False)
    cached = load_workbook(path, data_only=True)
    try:
        overview = [dict(name=w.title, state=w.sheet_state, rows=w.max_row,
                         columns=w.max_column, merged_ranges=[str(m) for m in w.merged_cells.ranges])
                    for w in wb.worksheets]
        if sheet is None:
            return {'path': str(path), 'sheets': overview,
                    'hint': 'Specify a sheet and optional A1 range to inspect cells.'}
        ws = wb[sheet]
        x1, y1, x2, y2 = range_boundaries(cell_range or f'A1:{ws.cell(min(ws.max_row, 50), min(ws.max_column, 30)).coordinate}')
        if None in (x1, y1, x2, y2) or min(x1, y1) < 1 or x2 < x1 or y2 < y1:
            raise ValueError('Invalid rectangular A1 range')
        if (x2 - x1 + 1) * (y2 - y1 + 1) > 2000:
            raise ValueError('At most 2000 cells per call; request a smaller range')
        cells = []
        for row in ws.iter_rows(min_row=y1, max_row=y2, min_col=x1, max_col=x2):
            for c in row:
                if c.value is None:
                    continue
                item = {'coordinate': c.coordinate, 'value': c.value,
                        'type': c.data_type, 'number_format': c.number_format}
                if c.data_type == 'f':
                    item['cached_value'] = cached[sheet][c.coordinate].value
                    item['cache_note'] = 'A missing cache is not a recalculated formula value.'
                cells.append(item)
        return {'sheet': sheet, 'requested_range': cell_range,
                'rows': ws.max_row, 'columns': ws.max_column,
                'merged_ranges': [str(m) for m in ws.merged_cells.ranges],
                'cells': cells, 'blank_cells': 'Omitted; merged children are also blank.'}
    finally:
        wb.close()
        cached.close()


def encode(value):
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--path', default='/input/input.xlsx')
    p.add_argument('--sheet')
    p.add_argument('--range', dest='cell_range')
    args = p.parse_args()
    try:
        result = inspect_workbook(args.path, args.sheet, args.cell_range)
        print(json.dumps(result, ensure_ascii=False, default=encode))
    except Exception as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
