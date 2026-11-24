"""Shared helpers for the price list readers."""
import re, json, subprocess

MONTHS = 'jan feb mar apr may jun jul aug sep oct nov dec'.split()

def npages(pdf):
    out = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout
    return int(re.search(r'Pages:\s+(\d+)', out).group(1))

def page_text(pdf, p, layout=True):
    args = ['pdftotext'] + (['-layout'] if layout else []) + ['-f', str(p), '-l', str(p), pdf, '-']
    return subprocess.run(args, capture_output=True, text=True).stdout

def money(s):
    """'1,10,130' / '16650.00' / '9,520' -> float"""
    return float(s.replace(',', ''))

def date_iso(d, mon, y):
    m = int(mon) if str(mon).isdigit() else MONTHS.index(str(mon)[:3].lower()) + 1
    y = int(y); y = y + 2000 if y < 100 else y
    return f'{y}-{m:02d}-{int(d):02d}'

def hp_of_kw(kw):
    """Standard kW -> HP ratings as printed in Indian price lists."""
    table = {0.06: 0.08, 0.09: 0.12, 0.12: 0.16, 0.18: 0.25, 0.25: 0.33, 0.37: 0.5, 0.55: 0.75, 0.75: 1, 1.1: 1.5, 1.5: 2, 2.2: 3, 3: 4, 3.7: 5,
             4: 5.5, 5.5: 7.5, 7.5: 10, 9.3: 12.5, 11: 15, 15: 20, 18.5: 25, 22: 30, 30: 40, 37: 50, 45: 60, 55: 75, 75: 100, 90: 120,
             110: 150, 125: 170, 132: 180, 150: 200, 160: 215, 180: 240, 200: 270, 220: 300, 225: 300, 250: 335, 275: 370, 280: 375,
             300: 400, 315: 425, 355: 475, 400: 536, 450: 603, 500: 670, 560: 750, 630: 845, 710: 950, 800: 1072}
    return table.get(round(kw, 2), round(kw / 0.746, 1))

def save(out, make, listno, date, tax, source, mounting_text, steps, extras_page, sections):
    data = {'make': make, 'list': listno, 'date': date, 'tax': tax, 'source': source,
            'mounting_extra': {'text': mounting_text, 'steps': steps}, 'extras_page': extras_page,
            'sections': [s for s in sections if s['rows']]}
    json.dump(data, open(out, 'w'), indent=1)
    n = sum(len(s['rows']) for s in data['sections'])
    print(make, listno, date, 'sections', len(data['sections']), 'prices', n)
    for s in data['sections']:
        print(f"  {s['name']:<40} {len(s['rows']):4}  poles {sorted(set(str(r['pole']) for r in s['rows']))}  mount {s['mount']}")
    return data

class Sections:
    def __init__(self): self.d = {}; self.order = []
    def add(self, name, eff, kind, mount, row):
        if name not in self.d:
            self.d[name] = {'name': name, 'eff': eff, 'kind': kind, 'mount': mount, 'rows': []}; self.order.append(name)
        self.d[name]['rows'].append(row)
    def list(self): return [self.d[k] for k in self.order]

def date_from_name(name):
    """Dates in file names: 'w.e.f. 22.05.2026', '08.07.2026', '02.09.2026', '...-011126.pdf'."""
    import os
    b = os.path.basename(name)
    for pat in (r'(\d{1,2})[.\-_](\d{1,2})[.\-_](20\d{2})', r'(\d{2})(\d{2})(2\d)(?=\D*\.\w+$)', r'(\d{1,2})[.\-_](\d{1,2})[.\-_](\d{2})(?!\d)'):
        m = re.search(pat, b)
        if m and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(1)) <= 31: return date_iso(*m.groups())
    return None
