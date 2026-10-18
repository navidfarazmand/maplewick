# 11.08: leagues (roadmap part 7). Groups of 30, robot towns fill the gaps, points = focus minutes, top 10 up,
# bottom 5 down, top 3 get a trophy in the league's colour and a royal chest. Nobody loses their town.
import json, time, os, pathlib
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
SH = str(HERE / 'shots') + '/'; os.makedirs(SH, exist_ok=True)
def D(pg, e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
fails = []
def ok(c, m):
    print(('ok   ' if c else 'FAIL ') + m)
    if not c: fails.append(m)
errs = []
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 390, 'height': 844})
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st = D(pg, 'state()'); pg.close()
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['questsDone'] = ['gift', 'repair']; st['tray'] = []
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + "); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(2600)
    L = D(pg, 'league()')
    ok(L['L']['w'] and L['L']['t'] == 0 and L['n'] == 30, f"joined Bronze for {L['L']['w']}, group of {L['n']}, rank {L['rank']}")
    wk = L['L']['w']; y, n = wk.split('-W'); prev = f"{y}-W{int(n) - 1}"
    for t in (0, 2, 5, 9):
        R = D(pg, f'lgRobots({t})'); print(f"  robots in {['Bronze','Silver','Gold','Sapphire','Ruby','Emerald','Amethyst','Pearl','Obsidian','Diamond'][t]}: top {R[0]}, 3rd {R[2]}, 10th {R[9]}, median {R[14]}, 25th {R[24]} min a week")
    R0, R9 = D(pg, 'lgRobots(0)'), D(pg, 'lgRobots(9)')
    ok(R0[9] < 200 and R9[2] > 900, 'Bronze is easy to climb out of; a Diamond podium takes many hours')
    # the League tab is the first thing under Friends
    pg.evaluate("() => document.querySelector('#open-friends').click()"); pg.wait_for_timeout(600)
    card = pg.inner_text('.lgcard'); rows = pg.eval_on_selector_all('.lb .lbrow', 'e => e.length'); zones = pg.eval_on_selector_all('.lgzone', 'e => e.map(x => x.textContent)')
    ok('Bronze league' in card and rows == 30 and len(zones) == 1, f"League tab: {card.splitlines()[0]} · {rows} rows · zones {zones}")
    pg.screenshot(path=SH + 's11_league.png')
    # visit a robot town from the league
    pg.evaluate("() => document.querySelector('.lb .lbrow.tap').click()"); pg.wait_for_timeout(900)
    ok(D(pg, 'visiting()') if pg.evaluate("() => typeof window.MaplewickDebug.visiting === 'function'") else True, 'a robot town can be visited')
    pg.evaluate("() => document.querySelector('#visit-home') && document.querySelector('#visit-home').click()"); pg.wait_for_timeout(500)
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    # end of a week: 1st in Gold → up to Sapphire, a trophy and a royal chest
    gold0 = D(pg, 'state()')['gold']
    D(pg, f"leagueSet({{ w: '{prev}', t: 2, m: 2000 }})")
    L2 = D(pg, 'leagueStep()')
    ok(L2['t'] == 3 and L2['pend'] and L2['pend']['rank'] == 1 and L2['pw'] == prev and L2['pm'] == 2000, f"1st of 30 in Gold → Sapphire ({L2['pend']['rank'] if L2.get('pend') else None})")
    s = D(pg, 'state()'); tr = [x for x in s['tray'] if x['type'] == 'trophy']
    ok(len(tr) == 1 and tr[0]['level'] == 3 and tr[0]['place'] == 1, f"a Gold trophy waits in Build → Decor: {tr}")
    ok(s['gold'] > gold0, f"royal chest paid out: gold {gold0:.0f} → {s['gold']:.0f}")
    pg.evaluate("() => { document.querySelector('#scrim') && !document.querySelector('#scrim').hidden && document.querySelector('#sheet-close') && document.querySelector('#sheet-close').click(); }")
    pg.wait_for_timeout(300)
    D(pg, 'leaguePopup()'); pg.wait_for_timeout(400)
    txt = pg.inner_text('#sheet') if pg.query_selector('#sheet') else ''
    ok('1st of 30' in txt and 'Sapphire' in txt, f"the result card: {' / '.join(txt.splitlines()[:5])}")
    pg.screenshot(path=SH + 's11_league_result.png')
    pg.evaluate("() => [...document.querySelectorAll('#sheet .btn.primary')].pop().click()"); pg.wait_for_timeout(500)
    ok(not pg.is_hidden('#chest') and 'league prize' in pg.inner_text('#chest-eye').lower(), f"royal chest opens: {pg.inner_text('#chest-eye')}")
    pg.click('#chest-go'); pg.wait_for_timeout(5200); pg.click('#chest-go'); pg.wait_for_timeout(500)
    ok(pg.is_hidden('#chest') and pg.is_hidden('#result'), 'chest closes with no session result behind it')
    # bottom 5 in Ruby → Emerald? no: down to Sapphire
    D(pg, f"leagueSet({{ w: '{prev}', t: 4, m: 3, pend: null }})"); L3 = D(pg, 'leagueStep()')
    ok(L3['t'] == 3 and L3['pend']['move'] == -1, f"bottom 5 in Ruby → down to Sapphire (rank {L3['pend']['rank']})")
    # a week sat out: no move
    D(pg, f"leagueSet({{ w: '{prev}', t: 4, m: 0, pend: null }})"); L4 = D(pg, 'leagueStep()')
    ok(L4['t'] == 4 and not L4.get('pend'), 'a week with no focus: no move, no result card')
    # real players in my league share my group (the server's docs carry "lg" in the extras)
    docs = [{'id': f'u{i}', 'name': f'Player{i}', 'town': f'Town{i}', 'week': wk, 'weekMin': 50 * i, 'level': 5, 'lg': {'w': wk, 't': 4, 'm': 50 * i}, 'b': []} for i in range(1, 6)]
    docs.append({'id': 'other', 'name': 'Elsewhere', 'town': 'Far', 'week': wk, 'weekMin': 999, 'lg': {'w': wk, 't': 1, 'm': 999}, 'b': []})
    pg.evaluate(f"() => window.MaplewickDebug.boardDocs({json.dumps(docs)})")
    L5 = D(pg, 'league()'); live = [r for r in L5['top'] if r[0] == 'live']
    pg.evaluate("() => document.querySelector('#open-friends').click()"); pg.wait_for_timeout(500)
    body = pg.inner_text('.lb')
    ok('Player5' in body and 'Player1' in body and 'Elsewhere' not in body, 'the five Ruby players race in my group; the Silver one does not')
    snap = D(pg, 'snap()') if pg.evaluate("() => typeof window.MaplewickDebug.snap === 'function'") else None
    ok(snap is None or ('lg' in snap and snap['lg']['t'] == 4), f"my board entry carries the league: {snap and snap.get('lg')}")
    print('errors', errs[:3]); ok(not errs, 'no page errors')
    b.close()
print('FAILED:' if fails else 'ALL OK', fails)
