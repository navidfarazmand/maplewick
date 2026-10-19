# 12.09: lamp light on the ground, lights before speech bubbles, late days at the town hall and bank, windows on
# workshops and daycares, the gang in town (hideout, red zone, vandals, casing) and weather outfits.
import json, os, sys
from playwright.sync_api import sync_playwright

URL = os.environ.get('MW', 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'maplewick.html')))
ok = True
def check(name, cond, extra=''):
    global ok
    print(('PASS ' if cond else 'FAIL ') + name + (' ' + str(extra) if extra else ''))
    ok = ok and bool(cond)
def D(pg, e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")

with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 430, 'height': 900})
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st = D(pg, 'state()'); pg.close()
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['gold'] = 5000; st['tray'] = []; st['questsDone'] = ['gift', 'repair']
    for bb in st['buildings']:
        bb.pop('ruin', None)
        if bb['type'] == 'townhall': bb['level'] = 4
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if(!sessionStorage.getItem('s')){localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + ");sessionStorage.setItem('s','1')}")
    pg.goto(URL); pg.wait_for_timeout(900)
    ids = {}
    for t in ['cottage'] * 12 + ['bank', 'police', 'cafe', 'workshop', 'daycare']: ids.setdefault(t, []).append(D(pg, f"addBuilding('{t}',2)"))
    D(pg, "setStaff('police', 0)")
    D(pg, 'play()'); pg.wait_for_timeout(700)
    for _ in range(6): pg.mouse.move(215, 450); pg.mouse.wheel(0, 400); pg.wait_for_timeout(60)

    # windows of the workshop and the daycare are noted at night (they had none before)
    D(pg, 'sky(22)'); pg.wait_for_timeout(500)
    w = D(pg, 'nlWins()')
    check('workshop has night windows', w.get('workshop', 0) > 0, w)
    check('daycare has night windows', w.get('daycare', 0) > 0)
    check('a dark home notes no windows', w.get('cottage', 0) == 0)

    # someone in a dark home switches a light on, then talks
    hid = ids['cottage'][0]
    pg.evaluate(f"() => MaplewickDebug.bubble({hid}, null, 'Who is there?')")
    pg.wait_for_timeout(1100)
    check('a light comes on in the home that talks', D(pg, 'nlWins()').get('cottage', 0) > 0)

    # the town hall and the bank work late on some days
    hall = [x for x in D(pg, 'state()')['buildings'] if x['type'] == 'townhall'][0]
    late = D(pg, f"lateDays({hall['id']}, 60)")
    n = sum(1 for x in late if x)
    check('town hall works late on some days', 8 <= n <= 35, n)
    check('late until 8–11 pm', all(20 <= x <= 23 for x in late if x))
    check('a cottage never works late', not any(D(pg, f"lateDays({hid}, 20)")))

    # the gang: hideout, red zone, vandals
    g = D(pg, 'gangNow()')
    check('gang hideout on a free tile', g['hide'] is not None, g['hide'])
    check('gang has a red zone', g['zone'] is not None and len(g['tiles']) >= 3, len(g['tiles']))
    zb = [x['id'] for x in D(pg, 'state()')['buildings'] if D(pg, f"inZone({x['id']})")]
    check('some buildings are in the zone', len(zb) > 0, len(zb))
    check('vandals strike in the zone', D(pg, 'vandal()'))
    s2 = D(pg, 'state()')
    hit = [x for x in s2['buildings'] if x.get('vandal')]
    check('a window is smashed in the zone', len(hit) == 1 and hit[0]['id'] in zb)
    # a lamp in the zone lights it back
    z = g['tiles'][len(g['tiles']) // 2]
    lid = D(pg, f"lamp({z[0] + 0.5},{z[1] + 0.5},2)")
    tiles2 = D(pg, 'gangNow()')['tiles']
    check('a street lamp takes streets back', lid is not None and len(tiles2) < len(g['tiles']), (len(g['tiles']), len(tiles2)))
    pw0 = D(pg, 'power()'); D(pg, f'breakLamp({lid})')
    check('a broken lamp uses no electricity and gives no light', D(pg, 'power()') < pw0 and len(D(pg, 'gangNow()')['tiles']) >= len(tiles2), (pw0, D(pg, 'power()')))
    D(pg, 'setGold(500)') if pg.evaluate("() => !!MaplewickDebug.setGold") else None
    check('the broken lamp can be repaired', D(pg, f'repairLamp({lid})') is True)
    # graffiti after a town day in the zone
    pg.evaluate("() => { const s = MaplewickDebug.state(); }")
    for bid in zb: D(pg, f"bset({bid}, {{zoneSince: 1}})")
    tg = D(pg, 'gangTown(1)')
    check('a building a day in the zone gets tagged', any(x['tag'] for x in tg), tg[:3])

    # casing: the crew walks round the bank, then robs it (no police station)
    c0 = D(pg, 'casing(5)')
    check('the crew cases the bank first', c0 and c0['left'] == 5)
    before = D(pg, 'state()').get('lastHeist') or 0
    D(pg, 'casingStep(10)')
    after = D(pg, 'state()')
    bank = [x for x in after['buildings'] if x['id'] == ids['bank'][0]][0]
    check('then the bank is robbed', (after.get('lastHeist') or 0) > before and bank.get('robbed'))

    # drawn without errors by day and at night, in the rain and in winter
    for hr in (14, 22):
        D(pg, f'sky({hr})'); pg.wait_for_timeout(400)
    o = D(pg, 'outfitShot()')
    check('outfits draw', o.startswith('data:image/png'))
    check('no page errors', not errs, errs[:3])
    b.close()
print('ALL PASS' if ok else 'SOME FAILED')
sys.exit(0 if ok else 1)
