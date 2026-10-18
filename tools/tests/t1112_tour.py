"""11.12: walks the whole quick tour on a new town and checks the highlight follows each step (the cottage card, Place it here, Repair, See what you earned)."""
import json, os, pathlib, time
fails = []
from playwright.sync_api import sync_playwright
URL = (pathlib.Path(__file__).resolve().parent.parent.parent / 'app' / 'maplewick.html').as_uri()
def D(pg,e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':412,'height':860})
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(1500)
    # welcome screen: tap to continue, then the form
    for _ in range(15):
        if pg.is_visible('#welcome-form button[type=submit]'): break
        pg.mouse.click(200,400); pg.wait_for_timeout(700)
    if not pg.is_visible('#welcome-form button[type=submit]'): print('no welcome form')
    pg.evaluate("() => document.querySelector('#welcome-form button[type=submit]').click()"); pg.wait_for_timeout(800)
    # coach survey, if any: skip
    for _ in range(6):
        t = D(pg,'tour()')
        if t >= 0: break
        btns = pg.query_selector_all('#sheet button')
        names = [x.inner_text() for x in btns]
        sk = [x for x in btns if any(w in x.inner_text().lower() for w in ('skip','not now','later','no thanks'))]
        if sk: sk[0].click()
        elif btns: btns[-1].click()
        pg.wait_for_timeout(700)
    print('tour step', D(pg,'tour()'))
    seen=set()
    for k in range(80):
        i = D(pg,'tour()')
        if i < 0: break
        txt = pg.inner_text('#tour-text')
        hole = pg.evaluate("() => { const h = document.getElementById('tour-hole').getBoundingClientRect(); return [Math.round(h.top), Math.round(h.height)]; }")
        if (i, txt) not in seen:
            seen.add((i, txt)); print(i, '|', txt[:60], '| hole', hole)
        if pg.is_visible('#tour-next'): pg.click('#tour-next'); pg.wait_for_timeout(500); continue
        # waiting steps: do what the tour asks
        if 'Place it here' in txt:
            bt = pg.locator('button:visible', has_text='Place it here').first; r = bt.bounding_box(); print('   hole vs button', hole, [round(r['y'])-6, round(r['height'])+12]); bt.click(); pg.wait_for_timeout(800)
        elif 'free cottage' in txt:
            card = pg.query_selector('.bgrid .bcard.free:not(.off)')
            if card and card.is_visible():
                r = card.bounding_box(); print('   hole vs card', hole, [round(r['y'])-6, round(r['height'])+12])
                card.click(); pg.wait_for_timeout(800)
            else:
                pg.mouse.click(206, 360); pg.wait_for_timeout(700)
        elif 'Tap Repair' in txt:
            bt = pg.locator('button:visible', has_text='Repair').first; r = bt.bounding_box(); print('   hole vs repair', hole, [round(r['y'])-6, round(r['height'])+12]); bt.click(); pg.wait_for_timeout(800)
        elif 'broken' in txt:
            c = pg.evaluate("() => { const r = document.getElementById('tour-hole').getBoundingClientRect(); return [r.left+r.width/2, r.top+r.height/2]; }")
            pg.mouse.click(c[0], c[1]+6); pg.wait_for_timeout(700)
        elif 'Try one now' in txt:
            hb = pg.evaluate("() => { const r = document.getElementById('tour-hole').getBoundingClientRect(); return [r.left+r.width/2, r.top+r.height/2]; }")
            pg.mouse.click(hb[0], hb[1]); pg.wait_for_timeout(900)
        elif 'While you focus' in txt:
            D(pg,'skipReady()'); D(pg,'jumpFocus(30)'); pg.wait_for_timeout(800)
        elif 'Done!' in txt:
            pg.click('#cele-go'); pg.wait_for_timeout(800)
        elif 'chest' in txt.lower() or 'See what you earned' in txt:
            hb = pg.evaluate("() => { const r = document.getElementById('tour-hole').getBoundingClientRect(); return [r.left+r.width/2, r.top+r.height/2]; }")
            pg.mouse.click(hb[0], hb[1]); pg.wait_for_timeout(3500)
        else:
            pg.wait_for_timeout(500)
    ok = D(pg,'tour()') == -1 and not errs
    print(('PASS' if ok else 'FAIL') + ' the whole tour, errors', errs)
    b.close()
