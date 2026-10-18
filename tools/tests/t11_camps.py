# 11.06: town hall 6, the Barracks (one soldier per finished lap), soldiers' wages and food, and the bandit camps.
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
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['gold'] = 8000; st['playSec'] = 1200; st['food'] = 400
    for bb in st['buildings']:
        bb.pop('ruin', None)
        if bb['type'] == 'townhall': bb['level'] = 6
    st['land'] = ['base', 'east', 'south', 'hill']; st['questsDone'] = ['gift', 'repair']; st['tray'] = []
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + "); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900); D(pg, 'play()')
    ok(D(pg, 'train(3)') == 0, 'no soldiers without a Barracks')
    br = D(pg, "addBuilding('barracks', 1)"); ok(br is not None, 'the Barracks fits')
    ok(D(pg, 'train(3)') == 3, 'one soldier per finished lap')
    e0 = D(pg, 'econ()'); D(pg, 'train(4)'); e1 = D(pg, 'econ()'); ok(e1['wages'] > e0['wages'], 'soldiers cost wages')
    a = D(pg, 'army()'); ok(a['n'] == 7 and a['chance'] > 0.5, f"7 soldiers against the first camp: {round(a['chance']*100)}%")
    wins = 0
    for i in range(6):
        r = D(pg, 'attack()')
        if r['hurtUntil'] and r['hurtUntil'] > 0: break
        wins = r['cleared']
    a = D(pg, 'army()'); print('army after attacks', a)
    ok(a['cleared'] >= 1 or a['hurtUntil'] > 0, 'a win opens the next camp, a loss sends them home to rest')
    txt = D(pg, 'campPanel(0)'); ok('Bandit camps' in txt, 'the camp panel lists the camps')
    D(pg, 'lookAt(-2, 9)'); pg.wait_for_timeout(700); pg.screenshot(path=SH + 's11_camps.png')
    D(pg, f"choose({br}, 'off')"); ok(D(pg, 'train(2)') == 0, 'a resting Barracks trains no one')
    ok(not errs, 'no page errors ' + str(errs[:3]))
    b.close()
print('FAILS', fails)
