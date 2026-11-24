"""Read a Havells LT motor price list PDF (HM-xx layout) into prices JSON.
Usage: python3 read_havells.py LIST.pdf OUT.json"""
import sys, re, json, subprocess, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import date_from_name

PDF, OUT = sys.argv[1], sys.argv[2]
def page_text(p):
    return subprocess.run(['pdftotext', '-layout', '-f', str(p), '-l', str(p), PDF, '-'], capture_output=True, text=True).stdout
npages = int(re.search(r'Pages:\s+(\d+)', subprocess.run(['pdfinfo', PDF], capture_output=True, text=True).stdout).group(1))
first = page_text(1)
m = re.search(r'(HM-\d+)', first); listno = m.group(1) if m else 'Havells'
m = re.search(r'w\.e\.f\.\s*(\d+)\w*\s+([A-Za-z]+)\.?,?\s*(\d{4})', first)
MONTHS = 'jan feb mar apr may jun jul aug sep oct nov dec'.split()
date = f'{m.group(3)}-{MONTHS.index(m.group(2)[:3].lower()) + 1:02d}-{int(m.group(1)):02d}' if m else date_from_name(PDF)

ROW = re.compile(r'(MH[A-Z0-9]{6,})\s+(\d{4,8}\.\d\d)')       # catalogue ref + list price ends every row
NUM = re.compile(r'(?<![\w.])(\d+(?:\.\d+)?)(?![\w.])')
POLE = re.compile(r'(\d)\s*Pole\s*-?\s*[\d ]*(?:revolutions per minute|RPM)?\s*(\((?:Foot|Flange)\))?', re.I)
APPS = ['IE2 Gear Box', 'Atta Chakki', 'Cane Unloader', 'IE2 Loom', 'IE3 Ginning', 'IE2 Treadmill']

def frame_of(code):
    code = code.strip()
    m = re.match(r'^MH[A-Z]{2}(\d{2,3})([SML]?)', code)
    if m: return m.group(1) + m.group(2)
    m = re.match(r'^(\d{2,3}[SML]?(?:/[SML])?)\s*(FLP)?$', code)
    if m: return m.group(1)
    return code

def section_of(lines):
    head = ' '.join(l.strip() for l in lines[:3]).lower()
    eff = 'IE4' if 'ie4' in head else 'IE3' if 'ie3' in head else 'IE2' if 'ie2' in head or 'high efficiency' in head else ''
    if 'flame' in head: return eff + ' Flameproof', eff, 'FLP'
    if 'crane duty brake' in head: return 'Crane duty brake (S4)', 'IE2', 'CRANE BRAKE'
    if 'crane duty' in head: return 'Crane duty (S4)', 'IE2', 'CRANE'
    if 'brake' in head: return eff + ' Brake', eff, 'BRAKE'
    if 'fire fighting' in head: return eff + ' Fire fighting', eff, 'FIRE'
    if 'special applications' in head: return 'Special applications', '', 'SPECIAL'
    if 'aluminium' in head: return eff + ' Aluminium', eff, 'STD'
    if 'cast iron' in head: return eff + ' Cast iron', eff, 'STD'
    return None

sections = {}; order = []; extras_page = None
for p in range(1, npages + 1):
    txt = page_text(p); lines = txt.split('\n')
    nonempty = [l for l in lines if l.strip()]
    if not nonempty: continue
    if 'Cash Extra for Non standard' in txt and extras_page is None: extras_page = p
    sec = section_of(nonempty)
    if not sec or not ROW.search(txt): continue
    name, eff, kind = sec
    heads = []            # (col, pole, mount)
    app = ''
    for line in lines:
        hs = [(m.start(), int(m.group(1)), 'B5' if m.group(2) and 'Flange' in m.group(2) else 'B3') for m in POLE.finditer(line) if 'Pole' in m.group(0)]
        if hs and not ROW.search(line): heads = hs; continue
        if kind == 'SPECIAL':
            for a in APPS:
                if re.search(r'\b' + re.escape(a).replace(r'\ ', r'\s+'), line): app = a.replace('IE2 ', '').replace('IE3 ', '')
        prev = 0
        for m in ROW.finditer(line):
            seg = line[prev:m.start()]; prev = m.end()
            # frame: an MH.. code or "80 FLP"/"112M" just before the cat ref
            fm = re.search(r'(MH[A-Z0-9]{6,}|\d{2,3}[SML]?(?:/[SML])?\s*FLP|\b\d{2,3}[SML]\b)\s*$', seg)
            if not fm: raise SystemExit(f'page {p}: no frame in "{seg.strip()}"')
            nums = [(n.start(), float(n.group(1))) for n in NUM.finditer(seg[:fm.start()])]
            if len(nums) < 2: raise SystemExit(f'page {p}: no kW/HP in "{seg.strip()}"')
            col = nums[0][0] + (line.find(seg) if seg else 0)
            h = [x for x in heads if x[0] <= col + 12]
            h = max(h, key=lambda x: x[0]) if h else (heads[0] if heads else None)
            if not h: raise SystemExit(f'page {p}: no pole header')
            v = [x[1] for x in nums]
            if kind == 'SPECIAL': v = v[-2:]                 # bullet text such as 'Bearing: 6306' sits left of the kW
            row = {'kw': v[0], 'hp': v[1], 'pole': h[1], 'frame': frame_of(fm.group(1)), 'code': fm.group(1).strip(), 'cat': m.group(1), 'price': float(m.group(2)), 'page': p}
            if kind in ('CRANE', 'CRANE BRAKE') and len(v) >= 4: row['s1kw'], row['s1hp'] = v[2], v[3]
            if kind in ('BRAKE', 'CRANE BRAKE'):
                rest = v[4:] if kind == 'CRANE BRAKE' else v[2:]
                if len(rest) >= 2: row['torque'], row['sf'] = rest[0], rest[1]
            sname = name
            if kind == 'SPECIAL':
                sname = 'Special: ' + (app or 'other') + (' (flange B5)' if h[2] == 'B5' else '')
            key = sname
            if key not in sections:
                sections[key] = {'name': sname, 'eff': eff, 'kind': kind, 'mount': h[2] if kind == 'SPECIAL' else 'B3', 'rows': []}; order.append(key)
            sections[key]['rows'].append(row)

data = {
    'make': 'Havells', 'list': listno, 'date': date, 'tax': 'GST 18% extra', 'source': os.path.basename(PDF),
    'mounting_extra': {'text': 'B5, B14, V1, B35, B34: up to frame 80 nil, frame 90-160 3%, frame 180 and above 5%', 'steps': [[80, 0], [160, 3], [9999, 5]]},
    'extras_page': extras_page,
    'sections': [sections[k] for k in order],
}
n = sum(len(s['rows']) for s in data['sections'])
json.dump(data, open(OUT, 'w'), indent=1)
print(listno, date, 'sections', len(order), 'prices', n)
for s in data['sections']: print(f"  {s['name']:<34} {len(s['rows']):4}  poles {sorted(set(r['pole'] for r in s['rows']))}")
