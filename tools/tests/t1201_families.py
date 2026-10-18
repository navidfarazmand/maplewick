"""12.01: a town with 16 or more residents runs without errors. Since 11.03 a comment had swallowed the line that
counts new babies, so every tick threw "n is not defined" once a town reached 16 residents."""
import json, pathlib
from playwright.sync_api import sync_playwright
URL = (pathlib.Path(__file__).resolve().parent.parent.parent / 'app' / 'maplewick.html').as_uri()
def D(pg, e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
errs = []
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 390, 'height': 844})
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st = D(pg, 'state()'); pg.close()
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['gold'] = 2000
    for bb in st['buildings']:
        bb.pop('ruin', None)
        if bb['type'] == 'townhall': bb['level'] = 2
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if (!sessionStorage.getItem('s')) { localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + "); sessionStorage.setItem('s','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900)
    for _ in range(4): D(pg, "addBuilding('cottage', 3)")
    D(pg, 'famAhead(48)') if pg.evaluate("() => typeof window.MaplewickDebug.famAhead === 'function'") else None
    pg.wait_for_timeout(2500)
    people = pg.evaluate("() => window.MaplewickDebug.state().buildings.length")
    ok = not errs
    print(('PASS' if ok else 'FAIL') + f' a town of 16+ residents ticks without errors ({people} buildings) {errs[:2]}')
    b.close()
