# 11.04: town halls 5 and 6, inflation, savings, strikes, recessions, public works, the daycare and the new buildings.
import json, os, pathlib
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
def D(pg, e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
errs = []; fails = []
def ok(c, m): print(('PASS ' if c else 'FAIL ') + m); (None if c else fails.append(m))
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 390, 'height': 844})
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st = D(pg, 'state()'); pg.close()
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['gold'] = 6000; st['playSec'] = 1200; st['food'] = 600
    for bb in st['buildings']:
        bb.pop('ruin', None)
        if bb['type'] == 'townhall': bb['level'] = 4
    st['land'] = ['base', 'east', 'south', 'hill']; st['questsDone'] = ['gift', 'repair']; st['tray'] = []
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + "); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900); D(pg, 'play()')
    hall = [x for x in D(pg, 'state()')['buildings'] if x['type'] == 'townhall'][0]['id']
    u = D(pg, f'upgradeJob({hall})'); ok(u['cost'] == 12000, f"town hall 5 costs 12,000 (12.07) ({u['cost']})")
    for t in ['restaurant', 'library', 'cinema', 'townsquare']:
        ok(D(pg, f"addBuilding('{t}', 1)") is not None, f'a {t} fits')
    D(pg, 'setHall(5)'); D(pg, 'setGold(31000)')  # 12.07: the treasury at hall 5 holds 32,000
    i = D(pg, 'infl()'); ok(i['rate'] > 0, f"a nearly full treasury raises prices ({i['rate']*100:.2f}% a day)")
    k = D(pg, 'inflDays(7)'); ok(k > 1.02, f'after a week prices are up {round((k-1)*100,1)}%')
    i2 = D(pg, 'infl()'); ok(i2['fee'] > i['fee'], f"hiring costs more ({i['fee']} → {i2['fee']})")
    D(pg, "addBuilding('citybank', 1)")
    sv = D(pg, 'savings(500)'); ok(sv['savings'] >= 499, f'savings at the bank ({sv})')
    D(pg, 'infl(1.2)')
    sv2 = D(pg, 'savings(0)'); ok(sv2['savings'] >= sv['savings'] * 1.0, 'savings keep their value')
    D(pg, "addBuilding('depot', 1)"); D(pg, "setStaff('sweeper', 1)")
    e = D(pg, 'evStep()'); ok(e and e['kind'] == 'strike' and e['stage'] == 'warn', f'staff warn a day before a strike ({e})')
    ok('ev-strike' in D(pg, 'alerts()'), 'the warning is an alert with a fix')
    e = D(pg, 'evAhead(25)'); ok(e and e['stage'] == 'on', 'then they strike')
    ok(D(pg, "staffWorking('sweeper')") == 0, 'nobody sweeps during the strike')
    e = D(pg, "raise('sweeper')"); ok(e is None, 'a raise ends the strike')
    # recession: most shops losing money
    for i in range(3): D(pg, "addBuilding('cafe', 1)")
    D(pg, 'shopsRed()'); D(pg, 'setGold(2000)'); D(pg, "evAhead(0)")
    e = D(pg, 'ev()'); ok(e and e['kind'] == 'recession' and e['stage'] == 'warn', f'shops are worried ({e})')
    D(pg, 'shopsRed()'); e = D(pg, 'evAhead(49)'); ok(e and e['stage'] == 'on', 'then a recession')
    j0 = D(pg, 'jobsNow()')['jobs']; n = D(pg, 'publicWorks()'); j1 = D(pg, 'jobsNow()')['jobs']
    ok(n == 1 and j1 - j0 == 20, f'public works give 20 jobs ({j0} → {j1})')
    t = D(pg, 'tasks()'); print('plan', [(x['type'], x['work']) for x in t])
    ok(not errs, 'no page errors ' + str(errs[:3]))
    b.close()
print('FAILS', fails)
