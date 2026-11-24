"""Marathon (WEG group) LV motor price list (LVMP layout). Prices are listed by kW; HP is the standard equivalent.
Usage: python3 marathon.py LIST.pdf OUT.json"""
import sys, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

PDF, OUT = sys.argv[1], sys.argv[2]
N = npages(PDF)
GROUP = re.compile(r'(?:(?P<code>\b[A-Z]{2}\d{2}[A-Z0-9]{8,})\s+)?(?P<frame>\b[A-Z]{0,2}\d{2,3}[A-Z]{0,3}\d?\b)\s+(?P<kw>\d+(?:\.\d+)?)\s+(?:(?P<brake>\d+\s*\(\d+\s*Nm\))\s+)?(?P<price>\d{4,8})\b')
HEAD = re.compile(r'(\d+)\s*POLE,\s*\d+\s*RPM', re.I)

# table of contents: title ... page or page range
toc = {}
for line in page_text(PDF, 2).split('\n'):
    m = re.match(r'\s{3,}([A-Z][A-Z®\'’ ,()\-0-9]+?)\s{2,}(\d+)(?:-(\d+))?\s*$', line)
    if m and 'CASH EXTRAS' not in m.group(1):
        for p in range(int(m.group(2)), int(m.group(3) or m.group(2)) + 1): toc[p] = ' '.join(m.group(1).replace('®', '').split())

lp = ''
for p in range(1, min(N, 8) + 1):
    m = re.search(r'LVMP\s*\d+\s*:\s*(\d{2})-(\d{2})-(\d{4})', page_text(PDF, p))
    if m: lp = m.group(0); date = date_iso(*m.group(1, 2, 3)); break
else:
    date = None
m = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', page_text(PDF, 1))
listno = (m.group(1) + ' ' + m.group(2)) if m else 'Marathon'
if not date and m: date = date_iso(1, m.group(1), m.group(2))

def section(title):
    t = title.upper()
    eff = (re.search(r'IE\d', t) or [''])[0]
    temp = re.search(r'IE\d\s*-\s*(\d{3})0*\s*C', t)
    if 'SMOKE' in t: return f'Smoke spill {eff}' + (f' ({temp.group(1)[:3]}°C)' if temp else ''), eff, 'SMOKE'
    if 'FLAME PROOF' in t: return f'Flameproof {eff}' + (' gas group IIC' if 'IIC' in t else ''), eff, 'FLP'
    if 'SLIPRING' in t: return 'Crane duty slip ring (KS)', '', 'SLIPRING'
    if 'SCV BRAKE' in t: return 'Crane duty SCV brake', 'IE2', 'BRAKE'
    if 'TCV BRAKE' in t: return 'Crane duty TCV brake', 'IE3', 'BRAKE'
    if 'BRAKE' in t: return 'Standard brake', '', 'BRAKE'
    if 'CRANE' in t: return f'Crane duty {eff}', eff, 'CRANE'
    if 'FIREFIGHTING' in t: return f'Fire fighting {eff}', eff, 'FIRE'
    if 'DUST' in t: return "Dust proof Ex'tb' IIIC", '', 'FLP'
    if 'NON SPARKING' in t: return "Non sparking Ex'ec'", '', 'FLP'
    if 'TCA' in t: return f'Terramax TCA {eff}' + (' UL' if ' UL' in t else ''), eff, 'SPECIAL' if ' UL' in t else 'STD'
    if 'SCA' in t: return f'Terramax SCA {eff}', eff, 'STD'
    return title.title(), eff, 'STD'

secs = Sections(); extras_page = None; cur = None
for p in range(3, N + 1):
    txt = page_text(PDF, p)
    if re.search(r'TERMS AND\s*CONDITIONS', txt, re.I): break
    if extras_page is None and 'CASH EXTRAS' in txt: extras_page = p
    head = []
    for line in txt.split('\n'):
        if 'SPECIFICATIONS' in line.upper(): break
        head.append(line)
    title = ' '.join(re.sub(r'WEG Group|LVMP.*|®|CONTENTS', ' ', ' '.join(head)).split())
    title = re.sub(r'(?<=- )(\d{3})\s*0?\s*C', r'\1 C', re.sub(r'\s0\s', ' ', ' ' + title + ' ')).strip()
    if re.search(r'SERIES|DUTY|FLAME|SMOKE|BRAKE|MOTOR', title.upper()): cur = section(title)
    elif p in toc: cur = section(toc[p])
    if not cur: continue
    heads = []
    for line in txt.split('\n'):
        hs = [((m.start() + m.end()) / 2, int(m.group(1))) for m in HEAD.finditer(line)]
        if hs: heads = hs; continue
        for m in GROUP.finditer(line):
            if not heads: continue
            centre = (m.start() + m.end()) / 2
            pole = min(heads, key=lambda h: abs(h[0] - centre))[1]
            kw = float(m.group('kw'))
            row = {'kw': kw, 'hp': hp_of_kw(kw), 'pole': pole, 'frame': m.group('frame'), 'cat': m.group('code') or '', 'price': float(m.group('price')), 'page': p}
            if m.group('brake'): row['brake'] = ' '.join(m.group('brake').split())
            name, eff, kind = cur
            secs.add(name, eff, kind, 'B3', row)

save(OUT, 'Marathon', listno, date, 'GST extra', os.path.basename(PDF),
     'Standard flange and face mounting: up to frame 160 3%, frame 180 and above 5%', [[160, 3], [9999, 5]], extras_page, secs.list())
