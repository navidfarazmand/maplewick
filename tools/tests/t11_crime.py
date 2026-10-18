# 11.02: bigger buildings and crime: custody, the police post letting thieves go, gangs, heists, apartment fires,
# the market hall's competition and the factory's goods.
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
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['gold'] = 6000; st['playSec'] = 1200
    for bb in st['buildings']:
        bb.pop('ruin', None)
        if bb['type'] == 'townhall': bb['level'] = 4
    st['land'] = ['base', 'east', 'south', 'hill']; st['questsDone'] = ['gift', 'repair']; st['tray'] = []
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + "); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900); D(pg, 'play()')
    homes = [D(pg, "addBuilding('cottage', 2)") for i in range(6)]
    post = D(pg, "addBuilding('police', 1)"); D(pg, "setStaff('police', 1)")
    D(pg, f"rob({homes[0]})"); inc = D(pg, f"endRob({homes[0]}, true, false, {post})")
    ok('let go' in inc['outcome'], 'a police post lets the thief go: ' + inc['outcome'])
    g = D(pg, 'gang()'); ok(len(g['jail']) == 0, 'nobody in custody')
    r = D(pg, 'getaways(3)'); ok(r['gang'], f"3 getaways start a gang ({r})")
    g = D(pg, 'gang()'); ok(g['free'] and g['target'] >= 15, f"a free gang raises crime (target {round(g['target'])})")
    bank = D(pg, "addBuilding('bank', 1)"); D(pg, 'setGold(6000)')
    h = D(pg, f'heist({bank})'); ok(h and h['kind'] == 'heist' and 850 <= h['stolen'] <= 900, f"a heist takes 15% of the treasury ({h})")
    D(pg, f"endRob({bank}, false)"); ok(D(pg, 'state()')['gold'] < 5300, 'the heist cost gold')
    lead = g['gang']['leader']; held = D(pg, f'hold({lead})'); ok(not held, 'holding the leader stops the gang for the day')
    stn = D(pg, "addBuilding('policestation', 1)"); D(pg, "setStaff('police', 2)")
    D(pg, f"rob({homes[1]})"); inc = D(pg, f"endRob({homes[1]}, true, false, {stn})")
    ok('Held for a day' in inc['outcome'], 'a police station holds the thief: ' + inc['outcome'])
    apt = D(pg, "addBuilding('apartment', 1)"); fp = D(pg, "addBuilding('firestation', 1)"); D(pg, "setStaff('fire', 1)")
    ok(D(pg, f"responder('fire', {apt})") is None, 'a fire post cannot save an apartment block')
    D(pg, "addBuilding('firehall', 1)"); D(pg, "setStaff('fire', 2)")
    ok(D(pg, f"responder('fire', {apt})") == 'firehall', 'a fire station can')
    mk = D(pg, "addBuilding('market', 2)"); mh = D(pg, "addBuilding('markethall', 1)")
    si = D(pg, f'shopInfo({mk})'); print('market', si)
    fac = D(pg, "addBuilding('factory', 1)"); si2 = D(pg, f'shopInfo({mk})'); ok(si2['goods'], 'the factory gives shops +10%')
    food = D(pg, 'food()'); print('food cap', food['cap'])
    farm = D(pg, "addBuilding('farm', 1)"); food2 = D(pg, 'food()'); ok(food2['cap'] == food['cap'] + 200, 'the farm barn stores 200')
    D(pg, f'openCard({bank})'); pg.wait_for_timeout(300); pg.evaluate("() => { const t=[...document.querySelectorAll('#mpanel .ctabs button')].find(x=>x.textContent==='Details'); t && t.click(); }"); pg.wait_for_timeout(200)
    ok('police station' in pg.inner_text('#mpanel').lower(), 'the bank card says whether a police station reaches it')
    txt = D(pg, 'openIncidents()'); ok('gang' in txt.lower(), 'the incident report names the gang')
    ok(not errs, 'no page errors ' + str(errs[:3]))
    b.close()
print('FAILS', fails)
