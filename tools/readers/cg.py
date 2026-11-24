"""CG Power LT motors price list (LTM layout).
Pages differ a lot, so rows are read by column position: every price is tied to the frame before it,
and to the pole header printed above that column. Alternators and DC motors are left out.
Usage: python3 cg.py LIST.pdf OUT.json"""
import sys, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

PDF, OUT = sys.argv[1], sys.argv[2]
N = npages(PDF)
alltext = ' '.join(page_text(PDF, p, layout=False) for p in (1, 2, N - 1, N))
m = re.search(r'(LTM\s*\d+)\s*/\s*(\d{2})-(\d{2})-(\d{4})', alltext + ' ' + page_text(PDF, 13))
listno = m.group(1).replace(' ', '') if m else 'CG Power'
date = date_iso(m.group(2), m.group(3), m.group(4)) if m else date_from_name(PDF)

TOK = re.compile(r'\S+')
FRAME = re.compile(r'^(?:[A-Z]{1,3}\d{2,3}[A-Z]{0,3}|\d{3}TS?)[*#]*$')
PRICE = re.compile(r'^\d{4,8}$')
NUMT = re.compile(r'^\d+(?:\.\d+)?\**$')
SKIP = ('ALTERNATOR', 'DC MOTORS', 'CASH EXTRA', 'TESTING CHARGES', 'INDEX')

def section_of(title):
    t = ' '.join(title.split()).replace('–', '-')
    T = t.upper()
    eff = (re.search(r'IE\d\+?', T) or [''])[0]
    nice = {
        'NEXT GENERATION': 'Next generation', 'PROCESS PERFORMANCE': 'Process performance', 'SUPER PREMIUM EFFICIENCY FLAMEPROOF': 'Flameproof',
        'PREMIUM EFFICIENCY FLAMEPROOF': 'Flameproof', 'SUPER PREMIUM EFFICIENCY': 'Super premium', 'PREMIUM EFFICIENCY HIGHER OUTPUT': 'Higher output',
        'PREMIUM EFFICIENCY': 'Premium', 'HIGH EFFICIENCY': 'High efficiency', 'TEFC SLIP RING CRANE DUTY': 'Slip ring crane duty',
        'TEFC SQUIRREL CAGE CRANE DUTY': 'Squirrel cage crane duty', 'TEFC SLIP RING': 'Slip ring TEFC', 'SPDP SLIP RING': 'Slip ring SPDP',
        'NEMA': 'NEMA premium', 'TEXTILE': 'Textile', 'CRUSHER': 'Crusher', 'BRAKE': 'Brake (Kibosh)', 'FIRE FIGHTING': 'Fire fighting',
        'UL LISTED': 'UL listed', 'SMOKE EXTRACTION': 'Smoke extraction'}
    name = next((v for k, v in nice.items() if k in T), t.title())
    if eff and eff not in name: name += ' ' + eff
    if 'ALUMIN' in T: name += ' aluminium'
    elif 'CAST IRON' in T or '(CI)' in T: name += ' cast iron'
    kind = 'FLP' if 'FLAMEPROOF' in T else 'SLIPRING' if 'SLIP RING' in T else 'CRANE' if 'CRANE' in T else 'BRAKE' if 'BRAKE' in T else 'FIRE' if 'FIRE' in T else 'SMOKE' if 'SMOKE' in T else 'SPECIAL' if any(k in T for k in ('NEMA', 'TEXTILE', 'CRUSHER', 'UL LISTED')) else 'STD'
    return name, eff, kind

secs = Sections(); extras_page = None
for p in range(1, N + 1):
    txt = page_text(PDF, p)
    lines = txt.split('\n'); nonempty = [l for l in lines if l.strip()]
    if not nonempty: continue
    title = nonempty[0].strip()
    if extras_page is None and re.search(r'All types of mounting other than B3', txt): extras_page = p
    if any(k in title.upper() for k in SKIP): continue
    name, eff, kind = section_of(title)
    heads = []   # (centre col, pole)
    b5cols = []  # columns of "B5 (Flange)" headers
    for line in lines:
        hs = [((m.start() + m.end()) / 2, int(m.group(1))) for m in re.finditer(r'(\d+)\s*Pole\s*/\s*\d+\s*RPM', line)]
        if hs: heads = hs
        if 'B5 (Flange)' in line or re.search(r'\bFlange\s*$', line): b5cols = [m.start() for m in re.finditer(r'B5 \(Flange\)|Flange\s*$', line)]
        toks = [(m.start(), m.group()) for m in TOK.finditer(line)]
        if not any(PRICE.match(t) for _, t in toks) or not any(FRAME.match(t) for _, t in toks): continue
        # Explicit-pole layout: "IE3  75  2  CG280SM  cat price  cat price  cat price" (TB top, TB right, flange)
        em = re.match(r'\s*(IE\d)\s+(\d+(?:\.\d+)?)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\d{4,8})(?:\s+\S+\s+(?:\d{4,8}|-))?(?:\s+\S+\s+(\d{4,8}))?', line)
        if em:
            kw = float(em.group(2)); row = {'kw': kw, 'hp': hp_of_kw(kw), 'pole': int(em.group(3)), 'frame': em.group(4).rstrip('*'), 'cat': em.group(5),
                                             'price': float(em.group(6)), 'page': p}
            if em.group(7): row['price_b5'] = float(em.group(7))
            secs.add(re.sub(r' IE\d\+?', '', name) + ' ' + em.group(1), em.group(1), kind, 'B3', row); continue
        lead = []; i = 0
        while i < len(toks) and NUMT.match(toks[i][1]) and not PRICE.match(toks[i][1].rstrip('*')): lead.append(float(toks[i][1].rstrip('*'))); i += 1
        last_row = None; block_nums = list(lead); block = []
        for col, t in toks[i:]:
            if t in ('-', '**', '*'): continue
            if PRICE.match(t) and block:
                fr = [(c, x) for c, x in block if FRAME.match(x)]
                if fr:
                    fcol, frame = fr[-1]
                    cat = next((x for c, x in block if c > fcol and not FRAME.match(x)), '')
                    if not cat: cat = next((x for c, x in block if c < fcol and not NUMT.match(x)), '')
                    nums = [float(x.rstrip('*')) for c, x in block if c < fcol and NUMT.match(x)]
                    kwhp = nums if len(nums) >= 2 else lead
                    if len(kwhp) < 1:
                        cm = re.match(r'(\d+(?:\.\d+)?)[A-Z]', cat)          # catalogue refs start with the kW, e.g. 7.5KX6LTOP
                        if not cm: raise SystemExit(f'page {p}: no kW for {frame}')
                        kwhp = [float(cm.group(1))]
                    centre = (fcol + col) / 2
                    pole = min(heads, key=lambda h: abs(h[0] - centre))[1] if heads else None
                    if pole is None:
                        pm = re.search(r'[A-Z]{1,3}(\d{1,2})(?=[A-Z-]|$)', cat)      # e.g. 5.50EN2-FF -> 2 pole
                        if not pm: raise SystemExit(f'page {p}: no pole header')
                        pole = int(pm.group(1))
                    kw = kwhp[0]; hp = kwhp[1] if len(kwhp) > 1 else hp_of_kw(kw)
                    last_row = {'kw': kw, 'hp': hp, 'pole': pole, 'frame': frame.rstrip('*#'), 'cat': cat, 'price': float(t), 'page': p}
                    if re.search(r'[*#]', frame + cat): last_row['note'] = 'See note on the price list page'
                    secs.add(name if eff or 'IE' in name else name, eff, kind, 'B3', last_row)
                elif last_row is not None and b5cols:                      # B5 price beside the B3 one
                    last_row['price_b5'] = float(t)
                block = []
            elif PRICE.match(t):
                continue
            else:
                block.append((col, t))

save(OUT, 'CG Power', listno, date, 'GST extra', os.path.basename(PDF),
     'All mountings other than B3: frame 63-160 3%, frame 180 and above 5%', [[160, 3], [9999, 5]], extras_page, secs.list())
