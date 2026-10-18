"""11.11: the Android app bridge. Runs the game with a stand-in for the app (window.MaplewickApp) and checks:
the focus start and end messages, the phone-pickup rule (unlocked in another app for 15 s or more), what doesn't count
(screen off, a quick look, coming back in time), picking up the phone after a lap = taking the break, the message on
leaving the app (lock-screen countdown and alarms), and that nothing of this runs in a plain browser."""
import json, time, os, pathlib
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
def D(pg, e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
fails, errs = [], []
def check(ok, what):
    print(('PASS ' if ok else 'FAIL ') + what)
    if not ok: fails.append(what)

STUB = """
window.__posts = [];
window.MaplewickApp = { platform: 'android', post: (m) => window.__posts.push(m), on: (fn) => { window.__h = fn; }, recv: (m) => window.__h && window.__h(m) };
"""
def posts(pg, t): return pg.evaluate(f"() => window.__posts.filter((m) => m.t === '{t}')")
def send(pg, m): pg.evaluate(f"() => window.MaplewickApp.recv({json.dumps(m)})")
def ev(pg, sec_ago, e): send(pg, {'t': 'ev', 'at': int(time.time() * 1000) - int(sec_ago * 1000), 'e': e})

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 390, 'height': 844})
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st = D(pg, 'state()'); pg.close()
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['gold'] = 900; st['alarms'] = True
    seed = "if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + "); sessionStorage.setItem('seeded','1'); }"

    def fresh(app=True):
        pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        if app: pg.add_init_script(STUB)
        pg.add_init_script(seed)
        pg.goto(URL); pg.wait_for_timeout(900)
        return pg

    def start(pg, laps=False):
        pg.evaluate("() => document.querySelector('#btn-focus').click()"); pg.wait_for_timeout(900)
        if laps: pg.evaluate("() => { const t = [...document.querySelectorAll('.startsheet button')].find((x) => /lap/i.test(x.textContent) && !/start/i.test(x.textContent)); if (t) t.click(); }"); pg.wait_for_timeout(200)
        pg.click('.startsheet .btn.primary.full'); pg.wait_for_timeout(300)
        D(pg, 'skipReady()'); pg.wait_for_timeout(300)

    # 1. the hello, and the start message
    pg = fresh()
    check(any(m.get('version') == '11.12' for m in posts(pg, 'hello')), 'the game says hello to the app with its version')
    start(pg)
    s = D(pg, 'state()')['session']
    f = posts(pg, 'focus')
    check(bool(s) and f and f[-1]['on'] and f[-1]['grace'] == 15 and not f[-1]['resume'], 'starting focus tells the app (fresh log, 15 s grace)')

    # 2. a quick look in another app (8 s) doesn't count
    D(pg, 'jumpFocus(3)')
    ev(pg, 30, 'bg'); ev(pg, 22, 'fg'); pg.wait_for_timeout(500)
    check(D(pg, 'state()')['session'] is not None, '8 seconds in another app: still focusing')
    # 3. the screen going off for a long time doesn't count
    ev(pg, 20, 'bg'); ev(pg, 19.9, 'off'); pg.wait_for_timeout(500)
    check(D(pg, 'state()')['session'] is not None, 'screen off with the app in the back: still focusing')
    # 4. unlocked and in another app for 15 s or more: picked up, ends where it started
    ev(pg, 18, 'unlock'); ev(pg, 17.5, 'fg'); ev(pg, 17, 'bg'); pg.wait_for_timeout(600)
    st2 = D(pg, 'state()')
    check(st2['session'] is None, 'unlocked in another app for 17 s: the session ends')
    title = pg.evaluate("() => { const e = document.getElementById('result-title') || document.querySelector('.cele h2, #cele-title'); return e ? e.textContent : ''; }")
    print('   result:', title)
    f = posts(pg, 'focus')
    check(f and f[-1]['on'] is False, 'the end of the session tells the app')
    pg.close()

    # 5. still in another app now (no fg yet)
    pg = fresh(); start(pg)
    D(pg, 'jumpFocus(10)')
    ev(pg, 60, 'unlock'); ev(pg, 59, 'bg'); pg.wait_for_timeout(500)  # 59 s away, still away now
    check(D(pg, 'state()')['session'] is None, 'still away after 59 s (no fg yet): the session ends')
    pg.close()

    # 6. leaving the app: the countdown and the alarms
    pg = fresh(); start(pg)
    D(pg, 'jumpFocus(2)')
    pg.evaluate("""() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
      Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' });
      document.dispatchEvent(new Event('visibilitychange')); }""")
    pg.wait_for_timeout(300)
    a = posts(pg, 'away')
    print('   away:', json.dumps(a[-1] if a else None)[:400])
    check(bool(a) and a[-1]['countdown'] and a[-1]['countdown']['until'] > time.time() * 1000, 'leaving the app sends the lock-screen countdown')
    check(bool(a) and any(n['id'] == 'end' for n in a[-1]['notes']), 'and the "Focus done!" alarm')
    pg.evaluate("""() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
      Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' });
      document.dispatchEvent(new Event('visibilitychange')); }""")
    pg.wait_for_timeout(200)
    check(len(posts(pg, 'log?')) >= 1, 'coming back asks the app for the log')
    send(pg, {'t': 'log', 'events': []}); pg.wait_for_timeout(300)
    check(D(pg, 'state()')['session'] is not None, 'an empty log: focus goes on')
    pg.close()

    # 7. laps: picking up the phone in the safe minutes after a lap is taking the break
    st4 = json.loads(json.dumps(st)); st4['flags']['laps1012'] = True; st4['flags']['laps1013'] = True; st4['gold'] = 3000
    for bb in st4['buildings']:
        bb.pop('ruin', None)
        if bb['type'] == 'townhall': bb['level'] = 3
    st4['buildings'].append({'id': 302, 'type': 'firestation', 'c': 9, 'r': 2, 'level': 1, 'site': True, 'origin': 'built'})
    st4['queue'] = [{'id': 303, 'kind': 'build', 'type': 'firestation', 'bid': 302, 'fromLevel': 0, 'toLevel': 1, 'work': 125, 'done': 0, 'paid': 90, 'mode': 'focus'}]
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); pg.add_init_script(STUB)
    pg.add_init_script("if (!sessionStorage.getItem('seeded4')) { localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st4)) + "); sessionStorage.setItem('seeded4','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.evaluate("() => document.querySelector('#btn-focus').click()"); pg.wait_for_timeout(700)
    pg.click('.lsw-tick:nth-child(2)'); pg.wait_for_timeout(300)
    pg.click('.startsheet .btn.primary.full'); pg.wait_for_timeout(300); D(pg, 'skipReady()'); pg.wait_for_timeout(300)
    s = D(pg, 'state()')['session']
    check(bool(s and s.get('laps')), 'a lap session started')
    D(pg, 'jumpFocus(26)')  # one 25-minute lap done, 1 minute into the safe window
    ev(pg, 40, 'bg'); pg.wait_for_timeout(600)
    st3 = D(pg, 'state()')
    check(st3['session'] is None and st3.get('lapRun') is not None, 'picked up after a lap: the session ends as a break (the lap is kept)')
    pg.close()
    # and in the middle of the next lap: picked up
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); pg.add_init_script(STUB)
    pg.add_init_script("localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st4)) + ");")
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.evaluate("() => document.querySelector('#btn-focus').click()"); pg.wait_for_timeout(700)
    pg.click('.lsw-tick:nth-child(2)'); pg.wait_for_timeout(300)
    pg.click('.startsheet .btn.primary.full'); pg.wait_for_timeout(300); D(pg, 'skipReady()'); pg.wait_for_timeout(300)
    D(pg, 'jumpFocus(40)')  # lap 1 done, 10 minutes into lap 2
    ev(pg, 60, 'bg'); pg.wait_for_timeout(600)
    st5 = D(pg, 'state()')
    check(st5['session'] is None, 'picked up in the middle of lap 2: the session ends')
    print('   last result reason:', pg.evaluate("() => (document.getElementById('result-title') || {}).textContent || document.body.innerText.slice(0, 0)"))
    pg.close()

    # 8. a plain browser: no app, nothing posted, the test button still works
    pg = fresh(app=False); start(pg)
    check(pg.evaluate("() => typeof window.__posts") == 'undefined' and D(pg, 'state()')['session'] is not None, 'in a browser the bridge stays off')
    pg.close()

    check(not errs, f'no page errors {errs}')
    print('FAILS', fails)
    b.close()
