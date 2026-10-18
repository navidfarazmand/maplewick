"""12.00: the game and the server. Runs the game over http with a stand-in Firebase helper (tools/tests/fake_fb.js)
and checks: each focus session is reported to the server (focusStart with an id, focusEnd with the minutes), the
tour's 10x session isn't, nothing breaks when the server isn't there, and the server's weekly league result is used
(league, rank, trophy) instead of the game's own."""
import json, time, os, pathlib, threading, http.server, functools
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_address[1]}/app/maplewick.html'
def D(pg, e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
fails, errs = [], []
def check(ok, what):
    print(('PASS ' if ok else 'FAIL ') + what)
    if not ok: fails.append(what)
FBINIT = "window.MAPLEWICK_FIREBASE = { apiKey: 'test', projectId: 'test' }; window.MAPLEWICK_FB_URL = '/tools/tests/fake_fb.js';"
WEEKKEY = "(t) => { const d = new Date(t); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() + 3 - ((d.getDay() + 6) % 7)); const w1 = new Date(d.getFullYear(), 0, 4); return `${d.getFullYear()}-W${1 + Math.round(((d - w1) / 86400000 - 3 + ((w1.getDay() + 6) % 7)) / 7)}`; }"

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 390, 'height': 844})
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st = D(pg, 'state()'); pg.close()
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['gold'] = 900
    st['board'] = { 'joined': True, 'fb': True, 'name': 'Navid' }

    def page(state, extra=''):
        pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.add_init_script(FBINIT + extra)
        pg.add_init_script("localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(state)) + ");")
        pg.goto(URL); pg.wait_for_timeout(1500)
        return pg
    def start(pg):
        pg.evaluate("() => document.querySelector('#btn-focus').click()"); pg.wait_for_timeout(900)
        pg.click('.startsheet .btn.primary.full'); pg.wait_for_timeout(300); D(pg, 'skipReady()'); pg.wait_for_timeout(400)

    # 1. a session is reported, start and end
    pg = page(st)
    check(D(pg, 'board()')['me'] == 'u1', 'signed in with the stand-in helper')
    start(pg)
    calls = pg.evaluate('() => window.__calls')
    sid = D(pg, 'state()')['session'].get('sid')
    check(bool(calls) and calls[-1]['name'] == 'focusStart' and calls[-1]['data']['sid'] == sid and calls[-1]['data']['app'] is False, 'starting focus calls focusStart with the session id')
    D(pg, 'jumpFocus(30)'); pg.wait_for_timeout(800)
    calls = pg.evaluate('() => window.__calls')
    end = [c for c in calls if c['name'] == 'focusEnd']
    print('   end call:', end[-1] if end else None)
    check(bool(end) and end[-1]['data']['sid'] == sid and end[-1]['data']['minutes'] > 0, 'finishing calls focusEnd with the minutes')
    check(D(pg, 'state()').get('srvAt', 0) > 0, 'the server answered: the game knows it is on')
    pg.close()

    # 2. the server isn't there (not deployed): sessions work as before, nothing marked
    pg = page(st, 'window.__srvDown = true;')
    start(pg); D(pg, 'jumpFocus(30)'); pg.wait_for_timeout(800)
    s2 = D(pg, 'state()')
    check(s2['session'] is None and not s2.get('srvAt'), 'no server: the session finishes normally')
    pg.close()

    # 3. the server's league result is used
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(300)
    prevW = pg.evaluate(f"() => ({WEEKKEY})(Date.now() - 7 * 86400000)"); pg.close()
    st3 = json.loads(json.dumps(st)); st3['league'] = { 'w': prevW, 't': 0, 'm': 120, 'hist': [] }; st3['srvAt'] = int(time.time() * 1000)
    res = { 'last': { 'w': prevW, 't': 0, 'g': 0, 'rank': 2, 'n': 30, 'move': 1, 'to': 1, 'min': 118, 'trophy': True }, 't': 1 }
    pg = page(st3, "window.__docs = { 'leagueResults/u1': " + json.dumps(res) + " };")
    pg.wait_for_timeout(1500); D(pg, 'leagueStep()'); pg.wait_for_timeout(1200)
    L = D(pg, 'state()')['league']
    print('   league:', json.dumps({k: L.get(k) for k in ('w', 't', 'pw', 'pt', 'pm')}), 'hist', L.get('hist'))
    check(L['t'] == 1 and L.get('pw') == prevW and L['hist'] and L['hist'][-1]['rank'] == 2, "the server's result moves you up (2nd of 30)")
    tray = D(pg, 'state()')['tray']
    check(any(x.get('type') == 'trophy' and x.get('wk') == prevW for x in tray), 'and the trophy is waiting')
    pg.close()

    # 4. the server is on but hasn't finished the week yet: the game waits instead of guessing
    st4 = json.loads(json.dumps(st3))
    pg = page(st4)
    D(pg, 'leagueStep()'); pg.wait_for_timeout(800)
    L4 = D(pg, 'state()')['league']
    hrs = pg.evaluate("() => { const d = new Date(); d.setHours(0,0,0,0); d.setDate(d.getDate() - ((d.getDay() + 6) % 7)); return (Date.now() - d) / 3600000; }")
    if hrs < 12: check(L4['w'] == prevW, 'no result yet, early in the week: the game waits for the server')
    else: check(L4['w'] != prevW, 'no result 12 hours into the week: the game works it out itself')
    pg.close()

    # 5. the league tab shows the minutes the server counted this week
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(300)
    W = pg.evaluate(f"() => ({WEEKKEY})(Date.now())"); pg.close()
    st5 = json.loads(json.dumps(st)); st5['srvAt'] = int(time.time() * 1000); st5['league'] = { 'w': W, 't': 0, 'm': 0, 'hist': [] }
    pg = page(st5, "window.__docs = { 'focus/u1': { weeks: { '" + W + "': { min: 42, app: 0, n: 2 } } } };")
    pg.evaluate("() => document.getElementById('open-friends').click()"); pg.wait_for_timeout(2500)
    txt = pg.inner_text('#sheet')
    check('Checked by the server: 42 min' in txt, 'the league tab shows the server-checked minutes')
    pg.close()

    check(not errs, f'no page errors {errs}')
    print('FAILS', fails)
    b.close()
srv.shutdown()
