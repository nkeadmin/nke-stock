"""Bonfiglioli BVN motors list price (Excel), sheet 'Tab.2_BN_BE_BX' (4 pole, 1500 rpm).
Only IE2 (BE) and IE3 (BX). Without brake: B3 and B5/B14 prices (columns I and K).
With brake: B3 and B5/B14 prices (columns M and O). The columns are found by their headings.
HP is the standard rating for the kW (the sheet's own hidden HP column is not used).
Usage: python3 bonfiglioli.py LIST.xlsx OUT.json"""
import sys, re, os, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import openpyxl
warnings.simplefilter('ignore')

SRC, OUT = sys.argv[1], sys.argv[2]
wb = openpyxl.load_workbook(SRC, data_only=True)
name = next((n for n in wb.sheetnames if n.replace(' ', '').upper().startswith('TAB.2_BN_BE_BX')), None)
if not name: raise SystemExit("sheet Tab.2_BN_BE_BX not found")
ws = wb[name]
rows = list(ws.iter_rows(values_only=True))

def txt(v): return ' '.join(str(v or '').split()).upper()
# header rows: one row has W/o brake / With brake groups, one has B3 / B5 B14, one has KW / Hp
r_grp = next(i for i, r in enumerate(rows[:15]) if any('W/O BRAKE' in txt(c) for c in r))
r_mnt = next(i for i, r in enumerate(rows[:15]) if sum(txt(c) == 'B3' for c in r) >= 2)
r_kw = next(i for i, r in enumerate(rows[:15]) if any(txt(c) == 'KW' for c in r))
kwc = [j for j, c in enumerate(rows[r_kw]) if txt(c) == 'KW'][0]
# group starts (merged cells keep their text in the first column)
groups = sorted((j, 'brake' if 'WITH BRAKE' in txt(c) else 'plain') for j, c in enumerate(rows[r_grp]) if 'BRAKE' in txt(c))
def group_of(j): return [g for s, g in groups if s <= j][-1] if any(s <= j for s, g in groups) else None
cols = {}
for j, c in enumerate(rows[r_mnt]):
    t = txt(c); g = group_of(j)
    if g and t in ('B3', 'B5 B14') and (g, t) not in cols: cols[(g, t)] = j
need = [('plain', 'B3'), ('plain', 'B5 B14'), ('brake', 'B3'), ('brake', 'B5 B14')]
missing = [k for k in need if k not in cols]
if missing: raise SystemExit(f'price columns not found: {missing}')

def num(v):
    if isinstance(v, (int, float)): return float(v)
    s = str(v or '').strip().replace(',', '.')
    try: return float(s)
    except ValueError: return None

secs = Sections()
for r in rows[r_kw + 1:]:
    if not r or len(r) <= kwc: continue
    eff = next((str(c).strip() for c in r[:kwc] if isinstance(c, str) and re.fullmatch(r'IE\d', str(c).strip())), None)
    if eff not in ('IE2', 'IE3'): continue                      # IE1 is not used
    texts = [c for c in r[:kwc] if c is not None]
    series = next((str(c) for c in texts if str(c) in ('BN', 'BE', 'BX')), '')
    size = ''.join(str(c) for c in texts if c not in (eff, series))   # 100, 'LB', 4 -> '100LB4'
    m = re.match(r'(\d{2,3})([A-Z]*)(\d{1,2})$', size)
    if not m: raise SystemExit(f'size not understood: {texts}')
    frame, pole = m.group(1) + m.group(2), int(m.group(3))
    kw = num(r[kwc])
    if not kw: continue
    for g, label in (('plain', ''), ('brake', ' with brake')):
        b3, b5 = num(r[cols[(g, 'B3')]]), num(r[cols[(g, 'B5 B14')]])
        if not b3: continue
        row = {'kw': kw, 'hp': hp_of_kw(kw), 'pole': pole, 'frame': frame, 'cat': f'{series} {frame} {pole}', 'price': round(b3, 2), 'page': 1}
        if b5: row['price_b5'] = row['price_b14'] = round(b5, 2)
        secs.add(f'{eff} {series}{label}', eff, 'BRAKE' if g == 'brake' else 'STD', 'B3', row)

save(OUT, 'Bonfiglioli', 'BVN motors', date_from_name(SRC), 'GST extra', os.path.basename(SRC),
     'B5 and B14 prices are taken from the list; B35 is not in this list', None, None, secs.list())
