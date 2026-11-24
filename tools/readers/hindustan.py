"""Hindustan (HEM) LT motor price list, 'Price list No. 48/2026' layout.
Usage: python3 hindustan.py LIST.pdf OUT.json"""
import sys, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

PDF, OUT = sys.argv[1], sys.argv[2]
N = npages(PDF)
# Each row: kW HP [torque] Frame Designation Price; the designation's last digits give the pole (0203 = 2 pole, 4203 = 4/2 pole)
ROW = re.compile(r'(?P<frame>\b\d{2,3}[A-Z]{0,2}(?:\s+FLP)?)\s+(?:[-*#]\s+)?(?:\d{1,2}/\d{1,2}\s+)?(?P<des>\d[A-Z]{2}\d\s\d{3}-(?P<pole>\d{2})\d{0,2}(?:-[A-Z])?)(?:\s*\*)?\s+(?P<price>\d{1,3}(?:,\d{2})*,\d{3}|On\b)')
NUM = re.compile(r'(?<![\w./])(\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?)(?![\w.])')

def pole_of(code):
    a, b = int(code[0]), int(code[1])
    if a == 0: return b
    if code in ('10', '12', '16'): return int(code)
    return f'{a}/{b}'

def section_name(desc):
    d = re.sub(r'^HINDUSTAN\s+', '', desc)
    d = re.split(r'\s+(?:induction motors|Squirrel Cage|motors suitable)', d, flags=re.I)[0]
    d = d.replace("Ex'd' ", '').replace('motors for ', '').replace(' application', '').replace(' with IE2 efficiency class', ' IE2')
    d = d.replace('DUPLEX COOLING type', 'Duplex cooling').replace(' IE Cooling', ' Cooling')
    d = re.sub(r'\s+', ' ', d).strip()
    return d[0].upper() + d[1:]

first = ''.join(page_text(PDF, p) for p in (1, 2))
m = re.search(r'Price list No\.\s*(\d+)/(\d{4})', first)
listno = f'Price list {m.group(1)}/{m.group(2)}' if m else 'Hindustan'
m = re.search(r'(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})', os.path.basename(PDF).replace('011126', '01.11.26'))
date = None
for p in range(1, N + 1):
    t = page_text(PDF, p, layout=False)
    m = re.search(r'(?:w\.e\.f\.?|effective from)\s*:?\s*(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})', t, re.I)
    if m: date = date_iso(*m.groups()); break
if not date: date = date_from_name(PDF)

secs = Sections(); extras_page = None
for p in range(1, N + 1):
    txt = page_text(PDF, p)
    if 'Non-standard' in txt and 'Mounting' in txt and extras_page is None and not ROW.search(txt): extras_page = p
    flat = ' '.join(page_text(PDF, p, layout=False).split())
    dm = re.search(r'HINDUSTAN\s+.*?(?:suitable|application|class)', flat)
    if not dm: continue
    base = section_name(dm.group(0))
    mount = 'B5' if 'B5 construction' in flat else 'B3'
    flp = 'Flameproof' in base
    heads = []        # (col, eff) from headers like "4 Pole, 1500 rpm, IE3"
    lines = txt.split('\n')
    for i, line in enumerate(lines):
        hh = [(m.start(), m.group(1) or '') for m in re.finditer(r'\d+\s*Pole,\s*\d+\s*rpm(?:,\s*(IE\d))?', line)]
        if hh: heads = hh                      # a heading without IE (10 and 12 pole) resets the class
        prev = 0
        for m in ROW.finditer(line):
            seg = line[prev:m.start()]; segstart = prev; prev = m.end()
            if m.group('price') == 'On': continue                     # "On request"
            nums = [x.group(1) for x in NUM.finditer(seg)]
            if len(nums) < 2:                                          # kW/HP printed on the line above or below
                for j in (i - 1, i + 1):
                    if 0 <= j < len(lines) and not ROW.search(lines[j]):
                        part = lines[j][segstart:m.start()] if len(lines[j]) > segstart else ''
                        cand = [x.group(1) for x in NUM.finditer(part)]
                        if len(cand) >= 2: nums = cand; break
            if len(nums) < 2: raise SystemExit(f'page {p}: no kW/HP before {m.group("des")}')
            # take the numbers just before the frame: text further left can be a footnote or a pole heading
            if 'Torque' in base and len(nums) >= 3: kw, hp, tq = nums[-3], nums[-2], nums[-1]; nums = [kw, hp, tq]
            else: kw, hp = nums[-2], nums[-1]
            two = '/' in kw
            if two or 'two speed' in base.lower(): continue      # dual speed motors are left out of the app
            row = {'kw': kw if two else float(kw), 'hp': hp if two else float(hp), 'pole': pole_of(m.group('pole')),
                   'frame': m.group('frame').replace(' FLP', ''), 'cat': m.group('des'), 'price': money(m.group('price')), 'page': p}
            if len(nums) >= 3 and 'Torque' in base: row['torque_kgm'] = float(nums[2])
            eff = ''
            h = [x for x in heads if x[0] <= m.start()]
            if h: eff = max(h)[1]
            name = base
            if eff and eff not in name: name = f'{name} {eff}'
            if not re.search(r'IE\d', name) and not flp and 'Two speed' not in name and 'Torque' not in name and 'Duplex' not in name:
                pass
            em = re.search(r'IE\d', name)
            low = name.lower()
            kind = 'FLP' if flp else 'CRANE' if 'crane' in low else 'FIRE' if 'fire' in low else 'COOLING' if 'cooling tower' in low else 'SPECIAL' if any(k in low for k in ('two speed', 'torque')) else 'STD'
            secs.add(name + (' (B5)' if mount == 'B5' else ''), em.group(0) if em else '', kind, mount, row)

save(OUT, 'Hindustan', listno, date, 'GST extra', os.path.basename(PDF),
     'B5, B14, V1, V3, V18, V19, B35, B34: up to frame 132 3%, frame 160 and above 5%', [[132, 3], [9999, 5]], extras_page, secs.list())
