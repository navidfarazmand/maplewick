"""Makes the Google Play phone screenshots (1080 x 1920) in store/screenshots/ from the game. Needs the game fonts: npm install @fontsource/baloo-2 @fontsource/figtree in /tmp/claude-0/fonts (or change F)."""
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
import json, base64, pathlib, time
from playwright.sync_api import sync_playwright
URL = (ROOT / 'app' / 'maplewick.html').as_uri()
OUT = str(ROOT) + '/store/screenshots/'
F = '/tmp/claude-0/fonts/node_modules/@fontsource/'
def face(fam, pkg, w):
    p = pathlib.Path(F + f'{pkg}/files/{pkg}-latin-{w}-normal.woff2')
    if not p.exists(): return ''
    return "@font-face{font-family:'%s';font-weight:%d;font-style:normal;font-display:block;src:url(data:font/woff2;base64,%s) format('woff2');}" % (fam, w, base64.b64encode(p.read_bytes()).decode())
CSS = ''.join(face('Baloo 2', 'baloo-2', w) for w in (500, 600, 700, 800)) + ''.join(face('Figtree', 'figtree', w) for w in (400, 500, 600, 700, 800))
def D(pg, e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
errs = []
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 360, 'height': 640}, device_scale_factor=3, color_scheme='light')
    ctx.route('https://fonts.googleapis.com/**', lambda r: r.fulfill(status=200, content_type='text/css', body=CSS))
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st = D(pg, 'state()'); pg.close()
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['gold'] = 2400; st['playSec'] = 1500; st['town'] = 'Maplewick'
    st['streak'] = st.get('streak') or {}; 
    for bb in st['buildings']:
        bb.pop('ruin', None)
        if bb['type'] == 'townhall': bb['level'] = 3
    st['questsDone'] = ['gift', 'repair']; st['tray'] = []; st['flags'].update({'news8': True, 'migrated7': True, 'food10': True}); st['food'] = 150
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e) + ' @ ' + (e.stack or '')[:300]))
    pg.add_init_script("if (!sessionStorage.getItem('s')) { localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + "); sessionStorage.setItem('s','1'); }")
    pg.goto(URL); pg.wait_for_timeout(1200)
    for t, lv in [('cottage', 3), ('cottage', 2), ('cottage', 3), ('cottage', 2), ('market', 2), ('cafe', 2), ('bakery', 1), ('park', 2), ('fountain', 1), ('field', 2), ('field', 1), ('firestation', 1), ('policestation', 1), ('clinic', 1), ('school', 1), ('depot', 1), ('shed', 1), ('workshop', 1), ('granary', 1), ('lighthouse', 1)]:
        try: D(pg, f"addBuilding('{t}', {lv})")
        except Exception as e: print('skip', t, str(e)[:80])
    pg.wait_for_timeout(500)
    pg.wait_for_timeout(6000)
    pg.add_style_tag(content='#taskpop,#reqpill,#toast{visibility:hidden!important}')
    D(pg, "weather('clear')"); D(pg, "sky('day')"); pg.wait_for_timeout(800)
    pg.screenshot(path=OUT + '1-home.png')
    D(pg, 'play()'); pg.wait_for_timeout(1500)
    cam = D(pg, 'camera()'); print('cam', cam)
    pg.screenshot(path=OUT + '2-town.png')
    # 3. the start sheet, from Home
    pg.evaluate("() => { const h = [...document.querySelectorAll('button')].find((x) => x.offsetParent && /^\\s*Home/.test(x.textContent)); if (h) h.click(); }"); pg.wait_for_timeout(900)
    pg.evaluate("() => document.querySelector('#btn-focus').click()"); pg.wait_for_timeout(1200)
    pg.screenshot(path=OUT + '3-start.png')
    # 4. focusing
    pg.click('.startsheet .btn.primary.full'); pg.wait_for_timeout(400); D(pg, 'skipReady()'); D(pg, 'jumpFocus(9)'); pg.wait_for_timeout(1500)
    pg.screenshot(path=OUT + '4-focus.png')
    # 5. the chest
    D(pg, 'jumpFocus(30)'); pg.wait_for_timeout(2500)
    pg.screenshot(path=OUT + '5-celebrate.png')
    pg.evaluate("() => { const b = document.getElementById('cele-go'); if (b && b.offsetParent) b.click(); }"); pg.wait_for_timeout(600)
    pg.evaluate("() => { const b = document.getElementById('chest-hit'); if (b && b.offsetParent) b.click(); }"); pg.wait_for_timeout(4200)
    pg.screenshot(path=OUT + '6-chest.png')
    pg.evaluate("() => { const b = document.getElementById('chest-go'); if (b && b.offsetParent) b.click(); }"); pg.wait_for_timeout(1500)
    pg.screenshot(path=OUT + '7-result.png')
    pg.evaluate("() => { const b = document.getElementById('result-home'); if (b && b.offsetParent) b.click(); }"); pg.wait_for_timeout(800)
    # 8. the league
    pg.evaluate("() => document.getElementById('open-friends').click()"); pg.wait_for_timeout(1500)
    pg.screenshot(path=OUT + '8-league.png')
    print('errors', errs)
    b.close()
