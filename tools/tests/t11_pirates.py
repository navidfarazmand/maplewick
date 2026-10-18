# 11.05: the old harbour, pirates (guards, paying them off, landing), the fish market, hotel and theater.
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
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['gold'] = 5000; st['playSec'] = 1200; st['food'] = 400
    for bb in st['buildings']:
        bb.pop('ruin', None)
        if bb['type'] == 'townhall': bb['level'] = 5
    st['land'] = ['base', 'east', 'south', 'hill']; st['questsDone'] = ['gift', 'repair']; st['tray'] = []
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + "); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900); D(pg, 'play()')
    ok(D(pg, 'pirates()') is None, 'no pirates without the harbour')
    hb = D(pg, "addBuilding('harbour', 1)"); ok(hb is not None, 'the old harbour sits on the shore')
    pr = D(pg, 'pirates()'); ok(pr is not None, f"a pirate ship sails for the shore ({pr and pr['name']})")
    D(pg, 'lookAt(9, 9)'); pg.wait_for_timeout(600); pg.screenshot(path=SH + 's11_pirates.png')
    r = D(pg, 'pirateTick(65)'); f = D(pg, 'food()')['food']; g = D(pg, 'state()')['gold']
    ok(r is None and (f < 400 or g < 5000), f'they land and take a little (food {round(f)}, gold {round(g)})')
    ok(D(pg, 'pirates()') is not None, 'a second ship can come')
    r = D(pg, 'pirateTick(65)'); ok(r is None, 'it leaves (at most one landing a day)')
    D(pg, 'setGold(5000)'); pr = D(pg, 'pirates()'); pp = D(pg, 'payPirates()'); ok(not pp['pirate'] and pp['gold'] < 5000, 'paying them off sends them away')
    pr = D(pg, 'pirates()')
    wt = D(pg, f"addAt('watchtower', 3, {pr['c'] if pr['c'] < 17 else 16}, {pr['r'] if pr['r'] < 17 else 16})") if pr else None
    if wt is None and pr:
        for dc in range(-3, 4):
            for dr in range(-3, 4):
                wt = D(pg, f"addAt('watchtower', 3, {pr['c'] + dc}, {pr['r'] + dr})")
                if wt: break
            if wt: break
    q = D(pg, 'pirate()'); print('guard', q and q['guard'])
    r = D(pg, 'pirateTick(30)'); ok(r is None and q and q['guard'] == 'watchtower', 'the watchtower guards drive them off')
    fm = D(pg, "addBuilding('fishmarket', 1)"); f0 = D(pg, 'food()')['flow']['grown']; print('fish', fm, f0)
    ok(fm is not None and f0 > 0, 'the fish market brings food')
    for t in ['hotel', 'theater']: ok(D(pg, f"addBuilding('{t}', 1)") is not None, f'a {t} fits')
    ok(not errs, 'no page errors ' + str(errs[:3]))
    b.close()
print('FAILS', fails)
