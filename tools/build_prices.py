"""Build prices.json from the price list files in the pricelists folder.

Each file is matched to a make by what is printed inside it, read by that make's reader, and checked
before it replaces the make's old prices. A make whose new file fails a check keeps its old prices,
and the run ends with an error that says why.

Usage: python3 tools/build_prices.py pricelists prices.json"""
import sys, os, re, json, subprocess, tempfile, datetime, statistics, warnings
warnings.simplefilter('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
READERS = os.path.join(HERE, 'readers')
FOLDER, OUT = sys.argv[1], sys.argv[2]
FORCE = '--accept' in sys.argv[3:]     # accept new lists even if they differ a lot from the old ones

def first_text(path):
    if path.lower().endswith('.pdf'):
        return subprocess.run(['pdftotext', '-l', '3', path, '-'], capture_output=True, text=True).stdout
    if path.lower().endswith(('.xlsx', '.xlsm')):
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        out = ' '.join(wb.sheetnames)
        ws = wb.worksheets[0]
        for r in ws.iter_rows(max_row=6, values_only=True): out += ' ' + ' '.join(str(c) for c in r if c is not None)
        return out
    return ''

def which_make(path, text):
    t = text.upper(); n = os.path.basename(path).upper()
    if path.lower().endswith(('.xlsx', '.xlsm')):
        return 'bonfiglioli' if 'TAB.2_BN_BE_BX' in t.replace(' ', '') else None   # BVN motor list; gearbox and other lists are not read
    if 'HAVELLS' in t: return 'havells'
    if 'HINDMOTORS' in t or 'HINDUSTAN' in t: return 'hindustan'
    if 'FRSM' in t.replace(' ', '') or ('ABB' in t and 'IEC LV MOTORS' in t): return 'abb'
    if re.search(r'LTM\s*\d+', t) or 'CG POWER' in t or 'CROMPTON' in t: return 'cg'
    if 'MARATHON' in t or 'LVMP' in t or 'WEG' in t: return 'marathon'
    return None

MAKE_NAME = {'havells': 'Havells', 'hindustan': 'Hindustan', 'abb': 'ABB', 'cg': 'CG Power', 'marathon': 'Marathon', 'bonfiglioli': 'Bonfiglioli'}
MIN_PRICES = {'bonfiglioli': 20}     # the BVN sheet is short: 4 pole only
ORDER = ['abb', 'cg', 'havells', 'hindustan', 'marathon', 'bonfiglioli']

# Ranges left out of the app: one phrase per line in pricelists/leave-out.txt (a section whose name contains it is dropped)
LEAVE = []
lo = os.path.join(FOLDER, 'leave-out.txt')
if os.path.exists(lo):
    for line in open(lo, encoding='utf-8', errors='replace'):
        line = line.split('#')[0].strip()
        if not line: continue
        parts = re.split(r'\s+except\s+', line, maxsplit=1, flags=re.I)      # "Brake except Bonfiglioli"
        phrase, keep = parts[0], parts[1] if len(parts) > 1 else ''
        LEAVE.append((re.compile(r'(?<![A-Za-z])' + re.escape(phrase.strip()) + r'(?![A-Za-z])', re.I), [k.strip().lower() for k in keep.split(',') if k.strip()]))
def left_out(sec, make):
    return any(p.search(sec['name']) and make.lower() not in keep for p, keep in LEAVE)

old = {}
if os.path.exists(OUT):
    try:
        for mk in json.load(open(OUT)).get('makes', []): old[mk['make']] = mk
    except Exception as e:
        print('::warning::old prices.json could not be read:', e)

found = {}; notes = []; errors = []
for name in sorted(os.listdir(FOLDER)):
    path = os.path.join(FOLDER, name)
    if not os.path.isfile(path) or not name.lower().endswith(('.pdf', '.xlsx', '.xlsm')): continue
    key = which_make(path, first_text(path))
    if not key:
        notes.append(f'{name}: not a motor price list this app reads (left as it is)'); continue
    found.setdefault(key, []).append(path)

def odd_rating(r):
    try: kw, hp = float(r['kw']), float(r['hp'])
    except (TypeError, ValueError): return False          # two-speed ratings like 0.37/0.55
    return kw <= 0 or abs(hp * 0.746 / kw - 1) > 0.3

def key_of(r, sec): return (sec['name'], str(r['pole']), str(r['kw']), str(r['frame']))

makes = []
for key in ORDER:
    paths = found.get(key)
    label = MAKE_NAME[key]
    if not paths:
        if label in old:
            errors.append(f'{label}: its price list file is no longer in the pricelists folder; the old prices are kept')
            makes.append(old[label])
        continue
    best = None
    for path in paths:
        tmp = tempfile.mktemp(suffix='.json')
        r = subprocess.run([sys.executable, os.path.join(READERS, key + '.py'), path, tmp], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(tmp):
            errors.append(f'{label}: could not read {os.path.basename(path)}: {(r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout).strip() else "unknown error"}')
            continue
        data = json.load(open(tmp)); data['pdf'] = 'pricelists/' + os.path.basename(path)
        if best is None or (data.get('date') or '') > (best.get('date') or ''): best = data
    if len(paths) > 1:
        notes.append(f'{label}: {len(paths)} files found; using the newest ({best["source"] if best else "none readable"}). Delete the old file to avoid confusion.')
    if best is None:
        if label in old: makes.append(old[label])
        continue
    best['all_count'] = sum(len(s['rows']) for s in best['sections'])
    dropped = [s['name'] for s in best['sections'] if left_out(s, label)]
    best['sections'] = [s for s in best['sections'] if not left_out(s, label)]
    if dropped: notes.append(f'{label}: left out ' + ', '.join(dropped))
    rows = [(s, r) for s in best['sections'] for r in s['rows']]
    problem = None
    if best['all_count'] < MIN_PRICES.get(key, 50): problem = f'only {best["all_count"]} prices were found'
    elif any(not (r['price'] > 0) for s, r in rows): problem = 'some prices are zero or missing'
    elif sum(1 for s, r in rows if odd_rating(r)) > 0.02 * len(rows): problem = 'many kW and HP values do not fit together; the layout of the file may have changed'
    elif label in old and not FORCE:
        prev = old[label]
        prev_rows = {key_of(r, s): r['price'] for s in prev['sections'] for r in s['rows']}
        n_old = prev.get('all_count', len(prev_rows))
        if best['all_count'] < 0.7 * n_old: problem = f'{best["all_count"]} prices found, the old list had {n_old}; the layout of the new file may have changed'
        else:
            ratios = [r['price'] / prev_rows[key_of(r, s)] for s, r in rows if key_of(r, s) in prev_rows]
            if len(ratios) >= 20:
                med = statistics.median(ratios)
                if not 0.7 <= med <= 1.5: problem = f'prices changed by {round((med - 1) * 100)}% on average, which looks wrong'
                else: notes.append(f'{label}: {len(rows)} prices, average change {round((med - 1) * 100, 1)}% against {prev.get("list")}')
            elif best.get('list') == prev.get('list'): pass
    if problem:
        errors.append(f'{label} ({best["source"]}): {problem}. The old prices are kept.')
        if label in old: makes.append(old[label])
        continue
    makes.append(best)
    if label not in old: notes.append(f'{label}: added, {len(rows)} prices')
    if not rows: makes.pop(); notes.append(f'{label}: every range of this make is in leave-out.txt, so it is not shown')

out = {'generated': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).isoformat(timespec='minutes'),
       'makes': makes, 'errors': errors}
json.dump(out, open(OUT, 'w'), separators=(',', ':'))
for n in notes: print(n)
for e in errors: print('::error::' + e)
print('prices.json:', ', '.join(f'{m["make"]} {m["list"]} ({sum(len(s["rows"]) for s in m["sections"])})' for m in makes))
sys.exit(1 if errors else 0)
