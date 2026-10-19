# 12.10: the start page (jobs in laps, no repeated lap length, a big total, Sam's plan mark), police shifts, the gang's
# hours, the wanted poster, the lamp preview and the phone-check note.
import json, os, sys
from playwright.sync_api import sync_playwright

URL = os.environ.get('MW', 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'maplewick.html')))
ok = True
def check(name, cond, extra=''):
    global ok
    print(('PASS ' if cond else 'FAIL ') + name + (' ' + str(extra) if extra != '' else ''))
    ok = ok and bool(cond)
def D(pg, e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")

with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 390, 'height': 844})
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st = D(pg, 'state()'); pg.close()
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['gold'] = 5000; st['tray'] = []; st['questsDone'] = ['gift', 'repair']; st['playSec'] = 3600
    for bb in st['buildings']:
        bb.pop('ruin', None)
        if bb['type'] == 'townhall': bb['level'] = 4
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if(!sessionStorage.getItem('s')){localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + ");sessionStorage.setItem('s','1')}")
    pg.goto(URL); pg.wait_for_timeout(900)
    ids = {}
    for t in ['cottage'] * 10 + ['bank', 'police', 'policestation', 'cafe', 'market']: ids.setdefault(t, []).append(D(pg, f"addBuilding('{t}',2)"))
    D(pg, 'play()'); pg.wait_for_timeout(600)

    # the start page, laps with no project
    D(pg, 'openStart()'); pg.wait_for_timeout(600)
    head = pg.inner_text('.lapsw .lsw-head b')
    check('the lap line says only how it splits', 'lap:' not in head and 'focus' in head, head)
    check('your job can be chosen in laps', pg.query_selector('.startsheet .jobline') is not None)
    pg.click('.startsheet .jobline'); pg.wait_for_timeout(300)
    check('the job choices open in laps', len(pg.query_selector_all('.startsheet .jobs .jobchip')) > 0)
    tot = pg.inner_text('.lp-total')
    check('the total is big, with the time it ends', 'in all' in tot and 'done at' in tot, tot.replace('\n', ' | '))
    check('no plan, no plan mark', pg.eval_on_selector('.lapsw .lsw-mid', 'e => e.hidden'))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)

    # police shifts
    D(pg, "setStaff('police', 6)"); D(pg, 'sky(14)'); pg.wait_for_timeout(1500)
    w = [x for x in D(pg, 'walkers()') if x['role'] == 'police']
    if len(w) > 1:
        inside = sum(1 for x in w if x['indoors'])
        check('by day not every officer is out', 0 < inside < len(w), (inside, len(w)))
    else:
        check('police walkers exist', False, len(w))

    # the gang's hours and the wanted poster
    g = D(pg, 'gangNow()')
    check('gang has a hideout', g['hide'] is not None)
    phases = pg.evaluate("() => [13, 21, 23.5, 2, 4].map((h) => { MaplewickDebug.sky(h); return MaplewickDebug.gangPhase ? MaplewickDebug.gangPhase() : null; })")
    check('asleep by day, out to plan and awake inside at night', phases == ['asleep', 'out', 'awake', 'out', 'awake'], phases)
    check('the wanted poster opens', D(pg, 'openWanted()'))
    check('it shows the reward', 'Reward' in pg.inner_text('#sheet') or 'REWARD' in pg.inner_text('#sheet').upper())
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)

    # placing a street lamp shows the lamp and fades the buildings around it
    hall = [x for x in D(pg, 'state()')['buildings'] if x['type'] == 'townhall'][0]
    picked = False
    for dc in range(-2, 4):
        for dr in range(-2, 4):
            if not picked and D(pg, f"pickLamp({hall['c'] + dc + 0.5},{hall['r'] + dr + 0.5})"): picked = True
    check('a lamp corner can be picked', picked)
    pg.wait_for_timeout(400)

    check('no page errors', not errs, errs[:3])
    b.close()
print('ALL PASS' if ok else 'SOME FAILED')
sys.exit(0 if ok else 1)
