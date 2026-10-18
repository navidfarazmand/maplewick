# 11.03: shop prices, layoffs, the tax rate, choices and the new businesses.
import json, os, pathlib
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
SH = str(HERE / 'shots') + '/'; os.makedirs(SH, exist_ok=True)
def D(pg, e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
errs = []; fails = []
def ok(c, m): print(('PASS ' if c else 'FAIL ') + m); (None if c else fails.append(m))
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 390, 'height': 844})
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st = D(pg, 'state()'); pg.close()
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['gold'] = 6000; st['playSec'] = 1200
    for bb in st['buildings']:
        bb.pop('ruin', None)
        if bb['type'] == 'townhall': bb['level'] = 3
    st['land'] = ['base', 'east', 'south', 'hill']; st['questsDone'] = ['gift', 'repair']; st['tray'] = []
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + "); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900); D(pg, 'play()')
    cf = [x for x in D(pg, 'state()')['buildings'] if x['type'] == 'cafe'][0]; cafe = cf['id']
    homes = []
    for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (2, 0), (-2, 0)]:
        h = D(pg, f"addAt('cottage', 2, {cf['c'] + dc}, {cf['r'] + dr})")
        if h: homes.append(h)
    print('homes near the café', len(homes))
    i0 = D(pg, f'shopInfo({cafe})')['income']
    D(pg, f"choose({cafe}, 'dear')"); i1 = D(pg, f'shopInfo({cafe})')['income']
    ok(abs(i1 / i0 - 1.25) < 0.02, f'dear: +25% at once ({round(i0,2)} → {round(i1,2)})')
    D(pg, 'shopStep(48)'); i2 = D(pg, f'shopInfo({cafe})')['income']
    ok(i2 < i1, f'then some customers stay away ({round(i2,2)})')
    D(pg, f"choose({cafe}, 'cheap')"); D(pg, 'shopStep(60)'); i3 = D(pg, f'shopInfo({cafe})')['income']
    print('cheap after two days', round(i3, 2))
    tx = D(pg, "tax('high')"); tn = D(pg, "tax('normal')"); tl = D(pg, "tax('low')")
    ok(tx['taxes'] > tn['taxes'] > tl['taxes'], 'high taxes pay more, low less')
    ok(tl['policyMood'] == 5 and tx['policyMood'] == -8, 'and change the mood')
    print('crime targets', tx['target'], tn['target'], tl['target']); ok(tx['target'] > tn['target'] or tx['target'] >= 100, 'high taxes raise crime')
    D(pg, "tax('normal')")
    # layoffs: a shop that earns less than its upkeep for a town day
    bk = D(pg, "addBuilding('arcade', 1)"); D(pg, f"choose({bk}, 'cheap')")
    s = D(pg, 'shopStep(25)'); bs = [x for x in s if x['id'] == bk][0]
    print('arcade', bs, D(pg, f'shopInfo({bk})')); ok(bs['layoff'] >= 1, 'a shop that loses money for a town day lets a worker go')
    D(pg, 'shopStep(25)'); D(pg, 'shopStep(25)'); s = D(pg, 'shopStep(25)'); bs = [x for x in s if x['id'] == bk][0]
    print('arcade later', bs); ok(bs['layoff'] <= 1, 'with fewer staff to pay it can hire again')
    ph = D(pg, "addBuilding('pharmacy', 1)"); r0 = D(pg, f'sickRisk({homes[0]})')
    for t in ['hardware', 'pub', 'gym', 'icecream', 'rink']:
        ok(D(pg, f"addBuilding('{t}', 1)") is not None, f'a {t} fits')
    D(pg, f'openCard({cafe})'); pg.wait_for_timeout(300)
    ok(pg.locator('#mpanel .choicebox').count() == 1, 'the café card has a price choice')
    pg.screenshot(path=SH + 's11_choice.png')
    txt = pg.evaluate("() => { window.MaplewickDebug.policies(); return document.querySelector('#sheet').innerText; }")
    ok('Tax rate' in txt, 'Policies has the tax rate')
    ok(not errs, 'no page errors ' + str(errs[:3]))
    b.close()
print('FAILS', fails)
