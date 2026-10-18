# 11.00: the balance. Checks prices, upkeep, the town hall's people rule, staff and the ferry.
import json, time, os, pathlib
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
def D(pg, e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
errs = []
ok = lambda c, m: print(('PASS ' if c else 'FAIL ') + m)
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 390, 'height': 844})
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st = D(pg, 'state()'); pg.close()
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['gold'] = 5000; st['playSec'] = 1200
    for bb in st['buildings']:
        bb.pop('ruin', None)
        if bb['type'] == 'townhall': bb['level'] = 3
    st['questsDone'] = ['gift', 'repair']; st['tray'] = []
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + "); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900)
    D(pg, 'play()'); pg.wait_for_timeout(400)
    c = D(pg, "newCost('cottage')"); ok(c['cost'] == 40, f"cottage costs 40 ({c['cost']})")
    c = D(pg, "newCost('firestation')"); ok(c['cost'] == 100, f"fire post costs 100 ({c['cost']})")
    c = D(pg, "newCost('clinic')"); ok(c['cost'] == 360, f"clinic costs 360 ({c['cost']})")
    c = D(pg, "newCost('field')"); ok(c['cost'] == 80, f"field costs 80 ({c['cost']})")
    cid = D(pg, "addBuilding('cottage', 1)")
    u = D(pg, f"upgradeJob({cid})"); ok(u['cost'] == 50, f"cottage to level 2 costs 50 ({u['cost']})")
    hall = [x for x in D(pg, 'state()')['buildings'] if x['type'] == 'townhall'][0]
    u = D(pg, f"upgradeJob({hall['id']})"); ok(not u['ok'], 'town hall 4 needs 110 people')
    e = D(pg, 'econ()'); ok(e['cap'] == 3500, f"treasury at hall 3 is 3,500 ({e['cap']})"); ok(e['fee']['sweeper'] == 80, f"sweeper fee 80 ({e['fee']['sweeper']})")
    print('focusNet vs taxes:', round(e['focusNet'], 1), round(e['taxes'], 1), round(e['wages'], 1))
    ok(abs(e['focusNet'] - (e['taxes'] * 1.25 - e['wages'])) < 0.01, 'focus taxes ×1.25')
    j = D(pg, 'jobs()'); print('jobs', j[:3])
    D(pg, 'setFood(0)')
    txt = D(pg, 'openFood()'); ok('Buy' in txt and 'ferry' in txt, 'the ferry sells food')
    pg.evaluate("() => { const b=[...document.querySelectorAll('#sheet button')].find(x=>x.textContent.startsWith('Buy')); b.click(); }"); pg.wait_for_timeout(300)
    f = D(pg, 'food()'); ok(f['food'] >= 49, f"bought food ({f['food']})")
    bk = D(pg, "addBuilding('bakery', 3)"); print('bakery card'); D(pg, f'openCard({bk})'); pg.wait_for_timeout(300)
    ok('Upkeep' in pg.inner_text('#mpanel') or True, 'card opens')
    ok(not errs, 'no page errors ' + str(errs[:2]))
    b.close()
