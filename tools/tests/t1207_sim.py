"""12.07: the balance check Navid asked for ("too easy to have full gold and full food"). Runs the game's own economy
day by day for a few players: they focus, play the time they earned, are away the rest of the day, and spend their gold
on what pays back fastest (upgrades of homes, shops and fields first, then new ones), keeping the staff the town needs.
Prints, for each player, the day the town hall reaches each level and how often the treasury and the food store are full.

    python3 tools/tests/t1207_sim.py [days] [player ...]     players: strong2h, strong1h, strong30, lazy2h
"""
import json, os, sys, time, pathlib
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
DAYS = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 90
PLAYERS = {  # sessions of 30 minutes a day; does the player spend their gold?
    'strong2h': {'sessions': 4, 'invest': True},
    'strong1h': {'sessions': 2, 'invest': True},
    'strong30': {'sessions': 1, 'invest': True},
    'lazy2h': {'sessions': 4, 'invest': False},
}
pick = [a for a in sys.argv[1:] if a in PLAYERS] or list(PLAYERS)
def D(pg, e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
def run(p, name, P):
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 390, 'height': 844})
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st = D(pg, 'state()'); pg.close()
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['questsDone'] = ['gift', 'repair']; st['tray'] = []
    st['coach'] = {'off': True}
    for bb in st['buildings']: bb.pop('ruin', None)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if(!sessionStorage.getItem('s')){localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + ");sessionStorage.setItem('s','1')}")
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.add_style_tag(content='*{animation:none!important;transition:none!important}')
    if os.environ.get('BAL'): print('   settings', D(pg, f"bal({os.environ['BAL']})"))
    hall_day, full_g, full_f, rows = {}, 0, 0, []
    src = {'focus': 0, 'play': 0, 'away': 0, 'spent': 0}
    t0 = time.time()
    for d in range(DAYS):
        D(pg, f"season('{'autumn' if d < 64 else 'winter'}')"); D(pg, 'simDay()')
        g = lambda: D(pg, 'simStat()')['gold']
        for _ in range(P['sessions']): r = D(pg, 'simFocus(30)'); src['focus'] += (r or {}).get('gold', 0)
        play = P['sessions'] * 5  # 1 min of play for every 6 of focus
        g0 = g(); D(pg, f"simTime({play}, 'play')"); src['play'] += g() - g0
        if P['invest']: g0 = g(); D(pg, f"simInvest({{reserve: {P.get('reserve', 0)}}})"); src['spent'] += g0 - g()
        g0 = g(); D(pg, f"simTime({24 * 60 - P['sessions'] * 30 - play}, 'home')"); src['away'] += g() - g0
        s = D(pg, 'simStat()')
        if d % 15 == 14: s['src'] = {k: round(v / 15) for k, v in src.items()}; src = {k: 0 for k in src}
        for L in range(2, 7):
            if s['hall'] >= L and L not in hall_day: hall_day[L] = d + 1
        if s['gold'] >= 0.95 * s['cap']: full_g += 1
        if s['foodCap'] and s['food'] >= 0.95 * s['foodCap']: full_f += 1
        if d % 15 == 14 or d == DAYS - 1: rows.append((d + 1, s))
    b.close()
    print(f"\n== {name}: {P['sessions'] * 30} min of focus a day, {'spends' if P['invest'] else 'saves'} its gold ({time.time() - t0:.0f} s)")
    print('   town hall 2/3/4/5/6 on day', [hall_day.get(L, "-") for L in (2, 3, 4, 5, 6)], f"· treasury full {full_g}/{DAYS} days · food store full {full_f}/{DAYS} days")
    for d, s in rows: print(f"   day {d:3}: gold {s['gold']:6}/{s['cap']:<6} food {s['food']:5}/{s['foodCap']:<5} hall {s['hall']} people {s['res']:3} net {s['net']:4}/h (focus {s['focusNet']:4}/h) food {s['grown']}-{s['eaten']}/h mood {s['mood']}% staff {s['staff']} levels {sum(s['lv'])}/{len(s['lv'])}" + (f"\n             a day: focus +{s['src']['focus']}, play +{s['src']['play']}, away +{s['src']['away']}, spent {s['src']['spent']}" if 'src' in s else ''))
    if errs: print('   ERRORS', errs[:3])
with sync_playwright() as p:
    for n in pick: run(p, n, PLAYERS[n])
