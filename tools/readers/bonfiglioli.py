"""Bonfiglioli branded motors list price (Excel, sheet 'List Price'). Columns are found by their headings.
Usage: python3 bonfiglioli.py LIST.xlsx OUT.json"""
import sys, re, os, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import openpyxl
warnings.simplefilter('ignore')

SRC, OUT = sys.argv[1], sys.argv[2]
wb = openpyxl.load_workbook(SRC, data_only=True, read_only=True)
ws = next((wb[n] for n in wb.sheetnames if n.strip().lower() == 'list price'), wb.worksheets[0])
rows = list(ws.iter_rows(values_only=True))
hi = next(i for i, r in enumerate(rows[:10]) if r and any(str(c or '').strip().lower().startswith('power') for c in r))
H = [str(c or '').strip().lower() for c in rows[hi]]
def col(*names):
    for n in names:
        for i, h in enumerate(H):
            if h.startswith(n): return i
    raise SystemExit(f'column {names} not found in {H}')
C = {'kw': col('power'), 'pole': col('poles'), 'eff': col('efficiency'), 'housing': col('housing'), 'size': col('size'),
     'b3': col('foot b3'), 'b5': col('flange b5'), 'b14': col('flange b14'), 'b35': col('foot/flange b35')}
secs = Sections()
for r in rows[hi + 1:]:
    if not r or not isinstance(r[C['kw']], (int, float)): continue
    b3 = r[C['b3']]
    if not isinstance(b3, (int, float)): continue
    kw = float(r[C['kw']]); eff = str(r[C['eff']] or '').strip(); housing = str(r[C['housing']] or '').strip()
    row = {'kw': kw, 'hp': hp_of_kw(kw), 'pole': int(r[C['pole']]), 'frame': str(r[C['size']]).strip(), 'cat': '', 'price': round(b3, 2), 'page': 1}
    for k in ('b5', 'b14', 'b35'):
        v = r[C[k]]
        if isinstance(v, (int, float)): row['price_' + k] = round(v, 2)
    secs.add(f'{eff} {housing.lower()}'.strip(), eff, 'STD', 'B3', row)

name = os.path.basename(SRC)
date = date_from_name(name)
save(OUT, 'Bonfiglioli', 'Branded motors', date, 'GST extra', name,
     'B5 and B14 same as B3, B35 and B34 +3% (prices per mounting are taken from the list)', [[9999, 0]], None, secs.list())
