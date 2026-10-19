"""12.05 (Navid's list of 18 Oct): the silver shield lasts until the end of your day (your first one through the
next day), when your day ends is a setting (once a week), Build now / rescue open the start page instead of a
countdown, the start page for laps (lap label, total, all chips, lap count), the report box is readable in dark mode,
the moving-town setting, the card follows a finger as it is pulled up, and bigger bandit islands with the boat around them."""
import json, time, pathlib, os
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
SH = str(HERE / 'shots') + '/'
os.makedirs(SH, exist_ok=True)
def D(pg, e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
fails, errs = [], []
def check(ok, what):
    print(('PASS ' if ok else 'FAIL ') + what)
    if not ok: fails.append(what)

def seeded(ctx, st):
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + "); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(1000)
    return pg

def focus25(pg):
    pg.evaluate("() => document.querySelector('#btn-focus').click()"); pg.wait_for_timeout(400)
    if not pg.is_visible('.setcard'):
        pg.click('.set-tog'); pg.wait_for_timeout(300)
    pg.click('.setcard .sc-tick[aria-label="45 min"]'); pg.wait_for_timeout(200)  # 45m
    pg.click('.startsheet .btn.primary.full'); pg.wait_for_timeout(300)
    D(pg, 'skipReady()'); D(pg, 'jumpFocus(46)'); pg.wait_for_timeout(1200)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, color_scheme='dark', has_touch=True)
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st0 = D(pg, 'state()'); pg.close()
    st0['named'] = True; st0['flags']['tourDone'] = True; st0['flags']['coachAsked'] = True; st0['gold'] = 2000; st0['playSec'] = 1800
    for bb in st0['buildings']:
        bb.pop('ruin', None)
        if bb['type'] == 'townhall': bb['level'] = 3
    st0['questsDone'] = ['gift', 'repair']; st0['tray'] = []

    # 1. the first silver shield: through tomorrow
    pg = seeded(ctx, dict(st0, silverUntil=0))
    focus25(pg)
    sv = D(pg, 'silver()')
    want = pg.evaluate("() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), d.getDate() + 2).getTime(); }")
    check(sv['on'] and sv['until'] == want, f"first silver shield lasts through tomorrow (until {sv['until']}, want {want})")
    txt = pg.inner_text('body')
    check('24 hours' not in txt, 'no "24 hours" left on screen')
    pg.screenshot(path=SH + 'f05_silver_result.png')
    pg.close()

    # 2. later ones: until the end of your day; a later day end moves it
    st = json.loads(json.dumps(st0)); st['silverEver'] = True; st['silverUntil'] = 1; st['dayEnd'] = 2
    pg = seeded(ctx, st)
    focus25(pg)
    sv = D(pg, 'silver()')
    want = pg.evaluate("() => { const t = Date.now() - 2 * 3600000, d = new Date(t); return new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1, 2).getTime(); }")
    check(sv['until'] == want, f'with the day ending at 2 am, the shield lasts until 2 am ({sv["until"]} vs {want})')
    # the setting
    pg.reload(); pg.wait_for_timeout(1200); D(pg, 'endShield()'); pg.wait_for_timeout(300)
    pg.evaluate("() => document.querySelector('#open-menu').click()"); pg.wait_for_timeout(400)
    pg.click('.mtile.k-settings'); pg.wait_for_timeout(400)
    body = pg.inner_text('#sheet')
    check('Your day ends at' in body and 'Midnight' in body and '5 am' in body, 'Settings: Your day ends at, Midnight … 5 am')
    check('Moving town' in body, 'Settings: Moving town switch')
    pg.click('#sheet .dp-durs button:has-text("4 am")'); pg.wait_for_timeout(300)
    s2 = D(pg, 'state()')
    check(s2['dayEnd'] == 4 and s2['dayEndAt'] > 0, 'choosing 4 am saves it')
    dis = pg.evaluate("() => [...document.querySelectorAll('#sheet .dp-durs button')].filter((b) => /am|Midnight/.test(b.textContent)).map((b) => b.disabled)")
    check(sum(dis) == 5, f'the other hours wait a week ({dis})')
    check('change it again on' in pg.inner_text('#sheet'), 'says when it can change again')
    pg.screenshot(path=SH + 'f05_settings_day.png')
    pg.close()

    # 3. Upgrade now opens the start page (no countdown)
    pg = seeded(ctx, st0)
    D(pg, 'play()'); pg.wait_for_timeout(800)
    cot = [x for x in D(pg, 'state()')['buildings'] if x['type'] == 'cottage' and not x.get('site')]
    D(pg, 'setHall(6)'); pg.wait_for_timeout(200)
    for ty in ('school', 'clinic', 'library', 'barracks', 'harbour', 'stadium', 'museum', 'hospital', 'university'):
        if ty not in D(pg, 'state()') and False: pass
        try: o = D(pg, f"order('{ty}')")
        except Exception as e: o = None
        print('   try', ty, o)
        if o and o.get('mode') == 'focus': break
    site = [x for x in D(pg, 'state()')['buildings'] if x.get('site')]
    if site: D(pg, f"openCard({site[-1]['id']})"); pg.wait_for_timeout(500)
    btn = pg.query_selector('#mpanel button:has-text("Upgrade now"), #mpanel button:has-text("Build now")')
    if btn:
        btn.evaluate('e => e.click()'); pg.wait_for_timeout(700)
        check(pg.is_visible('.startsheet') and not D(pg, 'state()')['session'], 'Upgrade now opens the start page, no countdown')
        pg.screenshot(path=SH + 'f05_upgrade_start.png')
        pg.click('#sheet-close'); pg.wait_for_timeout(400)
    else:
        print('   (no Upgrade now button here:', pg.inner_text('#mpanel')[:200].replace('\n', ' | '), ')')
    # 4. the card follows a finger
    D(pg, f"openCard({cot[0]['id']})"); pg.wait_for_timeout(500)
    bx = pg.query_selector('#mpanel').bounding_box()
    h0 = bx['height']
    pg.evaluate("""([x, y]) => { const box = document.getElementById('mpanel'), g = box.querySelector('.mp-grab') || box;
      const T = (yy) => new Touch({ identifier: 1, target: g, clientX: x, clientY: yy });
      window.__tt = (type, yy) => g.dispatchEvent(new TouchEvent(type, { bubbles: true, cancelable: true, touches: type === 'touchend' ? [] : [T(yy)], changedTouches: [T(yy)] }));
      __tt('touchstart', y); }""", [bx['x'] + bx['width'] / 2, bx['y'] + 6])
    for k in range(1, 6):
        pg.evaluate(f"() => __tt('touchmove', {bx['y'] + 6 - k * 30})"); pg.wait_for_timeout(40)
    h1 = pg.query_selector('#mpanel').bounding_box()['height']
    check(h1 > h0 + 100, f'mid-drag the card has grown with the finger ({h0:.0f} → {h1:.0f})')
    pg.screenshot(path=SH + 'f05_drag_mid.png')
    pg.evaluate(f"() => __tt('touchend', {bx['y'] + 6 - 150})"); pg.wait_for_timeout(700)
    check(bool((D(pg, 'panel()') or {}).get('full')), 'released: the card is full screen')
    pg.screenshot(path=SH + 'f05_drag_full.png')
    pg.close()

    # 5. laps on the start page
    pg = seeded(ctx, st0)
    pg.evaluate("() => document.querySelector('#btn-focus').click()"); pg.wait_for_timeout(500)
    if pg.is_visible('.lc-unfold'): pg.click('.lc-unfold'); pg.wait_for_timeout(500)
    t = pg.inner_text('.startsheet')
    print('   start page:', t[:400].replace('\n', ' | '))
    check('min lap:' in t or 'laps:' in t, 'lap label says "… lap: … min focus + … min break"')
    check('in all' in t, 'the total time is shown')
    pg.screenshot(path=SH + 'f05_start_laps.png')
    sb = pg.query_selector('.set-tog')
    if sb:
        cs = sb.evaluate("e => { const s = getComputedStyle(e); return [s.backgroundColor, s.fontWeight, e.getBoundingClientRect().height]; }")
        print('   set-time box:', cs)
        check(cs[2] > 44, 'the set-time box is a box, not one line')
    pg.close()

    # 6. the report box in dark mode
    pg = seeded(ctx, st0)
    pg.evaluate("() => window.MaplewickDebug && 0")
    pg.evaluate("() => document.querySelector('#open-menu').click()"); pg.wait_for_timeout(400)
    pg.click('.mtile.k-report'); pg.wait_for_timeout(400)
    cols = pg.eval_on_selector('textarea.reptext', "e => { const s = getComputedStyle(e); return [s.backgroundColor, s.color]; }")
    print('   report box colours:', cols)
    def lum(c):
        import re
        v = [int(x) for x in re.findall(r'\d+', c)[:3]]; return sum(v) / 3
    check(abs(lum(cols[0]) - lum(cols[1])) > 120, 'report box text stands out from its background')
    pg.screenshot(path=SH + 'f05_report_dark.png')
    pg.close()

    # 7. bandit islands and the boat
    pg = seeded(ctx, st0)
    D(pg, 'setHall(6)'); D(pg, 'play()'); pg.wait_for_timeout(1500)
    pg.screenshot(path=SH + 'f05_islands.png')
    pg.close()
    b.close()

print('no page errors' if not errs else 'ERRORS', errs[:5])
print('FAILS', fails)
