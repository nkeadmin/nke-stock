"""ABB IEC LV motors India price list (FRSM layout).
Usage: python3 abb.py LIST.pdf OUT.json"""
import sys, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

PDF, OUT = sys.argv[1], sys.argv[2]
N = npages(PDF)
CODE = r'(?P<code>(?P<series>[A-Z]*M\d[A-Z]{2,3}|S\d[A-Z]{3})(?P<fno>\d{2,3})(?P<flet>[SMLK]{0,2})[A-Z]{1,2}(?P<pn>\d{1,2}))'
ROW = re.compile(r'^(?P<pre>.*?)\b' + CODE + r'(?:\s+(?P<ie>IE\d))?(?P<mid>.*?)\s(?P<price>\d{1,3}(?:,\d{3})+|\d{4,})\s*$')
NUM = re.compile(r'(?<![\w./])(\d+(?:\.\d+)?)(?![\w.])')
POLES = {'TWO': 2, 'FOUR': 4, 'SIX': 6, 'EIGHT': 8, 'TEN': 10, 'TWELVE': 12}

t1 = ' '.join(page_text(PDF, 1, layout=False).split() + page_text(PDF, 4, layout=False).split())
m = re.search(r'FRSM\s*-?\s*(\d+)', re.sub(r'(?<=[A-Z]) (?=[A-Z])', '', t1))
listno = f'FRSM {m.group(1)}' if m else 'ABB'
m = re.search(r'EFFECTIVE FROM\s*(\d{1,2})\.(\d{1,2})\.(\d{4})', re.sub(r'\s+', '', t1).replace('EFFECTIVEFROM', 'EFFECTIVE FROM '))
date = date_iso(*m.groups()) if m else date_from_name(PDF)

def section(title, flat):
    P = re.search(r'\(([^()]*)\)\s*$', title.strip())
    P = P.group(1) if P else title
    eff = (re.search(r'IE\d', P) or re.search(r'IE\d', title) or [''])[0]
    if 'Smoke' in title:
        t = re.search(r'(\d{3})\s*Deg\.?\s*C\s*for\s*(\d+(?:\.\d+)?)\s*Hr', flat)
        return f'Smoke venting {eff}' + (f' ({t.group(1)}°C {t.group(2)} h)' if t else ''), eff, 'SMOKE'
    if 'Crane' in P: return f'Crane duty {eff or "IE2"} ({"VFD" if "VFD" in P else "DOL"})', eff or 'IE2', 'CRANE'
    if 'FLP' in P: return f'M2JAP Flameproof{" high output" if "HO" in P else ""} {eff}', eff, 'FLP'
    if 'HIOPT' in P: return f'M3BP High output {eff}', eff, 'HO'
    if 'M3BP' in P: return f'M3BP {eff}', eff, 'STD'
    if 'Aluminum-' in P: return f'M2AA {eff} (aluminium)', eff, 'STD'
    if 'Aluminum Winding' in title: return f'M2BAN {eff} (aluminium winding)', eff, 'STD'
    return f'M2BAX {eff}', eff, 'STD'

secs = Sections(); cur = None; extras_page = None
for p in range(3, N + 1):
    txt = page_text(PDF, p)
    if extras_page is None and re.search(r'Additional charges for specific', txt, re.I): extras_page = p
    notes = {m.group(1): m.group(2).strip() for m in re.finditer(r'^\s*([*#])\s*(The rating.*)$', txt, re.M)}
    flat = ' '.join(txt.split())
    tl = [l for l in txt.split('\n') if 'Squirrel Cage' in l and re.search(r'\([^()]*\)\s*$', l)]
    if tl: cur = section(tl[0], flat)
    if not cur: continue
    pole = None
    for line in txt.split('\n'):
        hm = re.match(r'\s*(TWO|FOUR|SIX|EIGHT|TEN|TWELVE)\s+POLE', line, re.I)
        if hm: pole = POLES[hm.group(1).upper()]; continue
        m = ROW.match(line)
        if not m: continue
        nums = [float(x) for x in NUM.findall(m.group('pre'))]
        if len(nums) < 2: raise SystemExit(f'page {p}: no kW/HP: {line.strip()}')
        name, eff, kind = cur
        row = {'kw': nums[0], 'hp': nums[1], 'pole': pole or int(m.group('pn')), 'frame': m.group('fno') + m.group('flet'),
               'cat': m.group('code'), 'price': money(m.group('price')), 'page': p}
        if kind == 'CRANE' and len(nums) >= 4: row['kw'], row['hp'], row['s1kw'], row['s1hp'] = nums[2], nums[3], nums[0], nums[1]
        amb = re.findall(r'\d{2}/[A-Z]', m.group('mid'))
        if amb: row['note'] = 'Ambient/temp rise ' + ', '.join(amb)
        marks = set(re.findall(r'[*#]', line))
        fn = [notes[k] for k in sorted(marks) if k in notes]
        if fn: row['note'] = (row.get('note', '') + ' ' + ' '.join(fn)).strip()
        secs.add(name, eff or m.group('ie') or '', kind, 'B3', row)

save(OUT, 'ABB', listno, date, 'GST extra', os.path.basename(PDF),
     'B5, B14, V1, V18, V19, B35, B34, V14, V36: up to frame 160 3%, frame 180 and above 5%', [[160, 3], [9999, 5]], extras_page, secs.list())
