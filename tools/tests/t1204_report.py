"""12.04: problem reports. Menu → Report a problem (and a shake in the Android app) opens the form; Send posts the
report to the server's bugReport function (stubbed here) with the note, version, what was on screen, recent errors and
a picture, and shows the report id. Also: a tap wakes up a page that still thinks the app is hidden."""
import json, pathlib, threading, http.server, functools
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
STUB = """window.__posts = []; window.MaplewickApp = { platform: 'android', appVersion: '1.0.0', _fake: null, post: (m) => window.__posts.push(m), on: (fn) => { window.__h = fn; }, recv: (m) => window.__h && window.__h(m),
  setHidden: (h) => { window.MaplewickApp._fake = h; Object.defineProperty(document, 'hidden', { configurable: true, get: () => window.MaplewickApp._fake }); document.dispatchEvent(new Event('visibilitychange')); } };
window.MAPLEWICK_FIREBASE = { apiKey: 'test', projectId: 'test' };"""
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 390, 'height': 844})
    sent = []
    def handle(route):
        sent.append(json.loads(route.request.post_data)); route.fulfill(status=200, content_type='application/json', body=json.dumps({'result': {'id': 'R-TEST'}}))
    ctx.route('https://us-central1-test.cloudfunctions.net/bugReport', handle)
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st = D(pg, 'state()'); pg.close()
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script(STUB); pg.add_init_script("localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + ");")
    pg.goto(URL); pg.wait_for_timeout(1500)
    # a shake opens the form
    pg.evaluate("() => window.MaplewickApp.recv({ t: 'shake' })"); pg.wait_for_timeout(500)
    check(pg.is_visible('textarea.reptext'), 'a shake opens the report form')
    pg.evaluate("() => console.error('test error for the report')")
    pg.fill('textarea.reptext', 'The town froze after I came back.')
    pg.click('#sheet button:has-text("Send report")'); pg.wait_for_timeout(1200)
    check(len(sent) == 1, 'Send posts the report to the server')
    d = sent[0]['data'] if sent else {}
    print('   keys:', sorted(d.keys()))
    check(d.get('note') == 'The town froze after I came back.' and d.get('ver') == '12.04' and d.get('app') == '1.0.0', 'with the note, the game and app versions')
    check(any('test error for the report' in e['msg'] for e in d.get('errors', [])), 'and recent errors')
    check(isinstance(d.get('state'), dict) and 'screen' in d['state'] and len(d.get('atPoints', [])) == 5, 'and what was on screen')
    check((d.get('shot') or '').startswith('data:image/jpeg;base64,'), 'and a picture of the town')
    check('R-TEST' in pg.inner_text('#sheet'), 'the report id is shown to the player')
    pg.click('#sheet button:has-text("Close")'); pg.wait_for_timeout(400)
    # the menu entry
    pg.evaluate("() => document.getElementById('open-menu').click()"); pg.wait_for_timeout(500)
    check(pg.is_visible('.mtile.k-report'), 'Menu has Report a problem')
    pg.evaluate("() => document.querySelector('.mtile.k-report').click()"); pg.wait_for_timeout(400)
    check(pg.is_visible('textarea.reptext'), 'which opens the form')
    pg.evaluate("() => { const b = document.getElementById('sheet-close'); if (b) b.click(); }"); pg.wait_for_timeout(400)
    # a page stuck "hidden" wakes up on a tap
    pg.evaluate("() => window.MaplewickApp.setHidden(true)"); pg.wait_for_timeout(200)
    check(pg.evaluate('() => document.hidden') is True, '(the page is told it is hidden)')
    pg.mouse.click(200, 400); pg.wait_for_timeout(300)
    check(pg.evaluate('() => document.hidden') is False, 'a tap wakes it up')
    check(not errs, f'no page errors {errs}')
    print('FAILS', fails)
    b.close()
srv.shutdown()
