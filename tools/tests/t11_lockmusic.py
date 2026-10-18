# 11.08: music with the phone locked. Fake songs stand in for the Internet Archive; the page is made "hidden" by hand.
# Checks: the next song starts on the second player before the first ends, a station that has played every song moves
# on to the next one, a pause (headphones out) shows as paused on the lock screen, and Play (the lock-screen button's
# own handler) starts it again; back in the app the music player carries on from the same song.
import json, struct, math, os, pathlib
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
def D(pg, e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
def wav(secs, f):
    sr = 8000; n = int(sr * secs); data = b''.join(struct.pack('<h', int(8000 * math.sin(2 * math.pi * f * i / sr))) for i in range(n))
    return b'RIFF' + struct.pack('<I', 36 + len(data)) + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 1, 1, sr, sr * 2, 2, 16) + b'data' + struct.pack('<I', len(data)) + data
SONG = wav(24, 440)
fails = []
def ok(c, m):
    print(('ok   ' if c else 'FAIL ') + m)
    if not c: fails.append(m)
HIDE = "() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => true }); Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' }); document.dispatchEvent(new Event('visibilitychange')); }"
SHOW = "() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => false }); Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' }); document.dispatchEvent(new Event('visibilitychange')); }"
errs = []
with sync_playwright() as p:
    b = p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844})
    def serve(r):  # with byte ranges, so the player can seek
        rg = r.request.headers.get('range'); H = {'Content-Type': 'audio/wav', 'Access-Control-Allow-Origin': '*', 'Accept-Ranges': 'bytes'}
        if rg and rg.startswith('bytes='):
            a, _, z = rg[6:].partition('-'); a = int(a or 0); z = int(z) if z else len(SONG) - 1
            H['Content-Range'] = f'bytes {a}-{z}/{len(SONG)}'; return r.fulfill(status=206, body=SONG[a:z + 1], headers=H)
        r.fulfill(status=200, body=SONG, headers=H)
    ctx.route('**/archive.org/**', serve)
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st = D(pg, 'state()'); pg.close()
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['questsDone'] = ['gift', 'repair']; st['tray'] = []
    st['music'] = True; st['src'] = 'rec'; st['track'] = 1; st['lockKind'] = 'music'  # Bossa nova: two songs
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("""
      if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', %s); sessionStorage.setItem('seeded','1'); }
      if (navigator.mediaSession) { const ms = navigator.mediaSession, set = ms.setActionHandler.bind(ms); ms.__h = {}; ms.setActionHandler = (a, f) => { ms.__h[a] = f; try { set(a, f); } catch (e) {} }; }
    """ % json.dumps(json.dumps(st)))
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.mouse.click(200, 400); pg.wait_for_timeout(1500)
    m = D(pg, 'music()'); ok(m['on'] and m['station'] == 'Bossa nova', f"music plays in the app: {m['track']} ({m['station']})")
    first = m['track']
    pg.evaluate(HIDE); pg.wait_for_timeout(1200)
    L = D(pg, 'lock()'); ok(L['on'] and not L['paused'] and L['song'] == first, f"locked: the lock-screen player carries on with {L['song']}")
    ok(D(pg, 'radio()')['playing'] is False, 'the in-app player stopped')
    o0 = L['other']
    D(pg, 'lockSeek(3)'); pg.wait_for_timeout(2600)
    L = D(pg, 'lock()'); S = D(pg, 'lockState()')
    ok(L['other'] != o0 and not L['paused'] and L['song'] != first, f"song ended: the second player took the next song ({L['song']}) {S['els']}")
    second = L['song']
    D(pg, 'lockSeek(3)'); pg.wait_for_timeout(2600)
    L = D(pg, 'lock()'); S = D(pg, 'lockState()')
    ok(S['track'] == 2 and not L['paused'], f"Bossa nova finished: the next station plays ({L['song']}, station {S['track']})")
    third = L['song']
    ps = D(pg, 'lockPause()'); pg.wait_for_timeout(300)
    S = D(pg, 'lockState()'); ok(S['ps'] == 'paused' and D(pg, 'lock()')['paused'], f"headphones out: paused, the lock screen shows paused ({S['ps']})")
    D(pg, 'lockPlay()'); pg.wait_for_timeout(800)
    S = D(pg, 'lockState()'); L = D(pg, 'lock()')
    ok(not L['paused'] and S['ps'] == 'playing' and L['song'] == third, f"Play on the lock screen: plays again ({L['song']}, {S['ps']})")
    # ⏭ on the lock screen
    pg.evaluate("() => navigator.mediaSession.__h.nexttrack()"); pg.wait_for_timeout(800)
    L2 = D(pg, 'lock()'); S = D(pg, 'lockState()')
    ok(L2['song'] != third and not L2['paused'] and sum(1 for e in S['els'] if not e['paused']) == 1, f"⏭ on the lock screen: {L2['song']}, only one player on")
    pg.evaluate(SHOW); pg.wait_for_timeout(1500)
    m = D(pg, 'music()'); L = D(pg, 'lock()')
    ok(not L['on'] and m['on'] and m['track'] == L2['song'] and m['station'] == 'Calm piano', f"back in the app: {m['track']} ({m['station']}) carries on")
    # in the app too: the last song of a station moves on to the next station
    seen = []
    for i in range(6):
        pg.evaluate("() => navigator.mediaSession.__h.nexttrack()"); pg.wait_for_timeout(500)
        m = D(pg, 'music()'); seen.append(m['station'])
        if m['station'] != 'Calm piano': break
    ok(seen[-1] == 'Soft ambient' and m['on'], f"in the app, ⏭ past the last Calm piano song plays Soft ambient: {m['track']}")
    # focus with the lock-screen music: the same two players, started by the tap on the lock button
    pg.evaluate("() => document.querySelector('#btn-focus').click()"); pg.wait_for_timeout(700)
    pg.evaluate("() => { const b = [...document.querySelectorAll('.startsheet .btn.primary.full')].pop(); if (b) b.click(); }"); pg.wait_for_timeout(500)
    D(pg, 'skipReady()'); pg.wait_for_timeout(300)
    pg.evaluate("() => document.querySelector('#focus-lock') && document.querySelector('#focus-lock').click()"); pg.wait_for_timeout(1200)
    L = D(pg, 'lock()')
    if L['on'] and L['song']:
        f1 = L['song']; D(pg, 'lockSeek(3)'); pg.wait_for_timeout(2600); L = D(pg, 'lock()')
        ok(L['on'] and not L['paused'] and L['song'] != f1, f"focus, phone locked: {f1} → {L['song']}")
    else: print('note: the focus lock sound is', L)
    print('errors', errs[:3])
    ok(not errs, 'no page errors')
    b.close()
print('FAILED:' if fails else 'ALL OK', fails)
