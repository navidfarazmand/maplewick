"""12.06: turn the town a quarter at a time. In every view: tapping a building opens its own card, the tile under a
finger is the right one, the view is kept after a reload, and the drawing has no errors. Also: night lights draw."""
import json, os, pathlib
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
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 430, 'height': 860})
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st = D(pg, 'state()'); pg.close()
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['gold'] = 5000; st['tray'] = []; st['questsDone'] = ['gift', 'repair']
    for bb in st['buildings']:
        bb.pop('ruin', None)
        if bb['type'] == 'townhall': bb['level'] = 4
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if(!sessionStorage.getItem('s')){localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + ");sessionStorage.setItem('s','1')}")
    pg.goto(URL); pg.wait_for_timeout(900)
    for t in ['cottage'] * 6 + ['cafe', 'market', 'park', 'bakery']: D(pg, f"addBuilding('{t}',2)")
    D(pg, 'play()'); pg.wait_for_timeout(900)
    pg.add_style_tag(content='.toast,#tasktip,.taskpop{display:none!important}')
    blds = [x for x in D(pg, 'state()')['buildings'] if x['type'] in ('cottage', 'cafe', 'market', 'bakery')]
    for v in range(4):
        if v: pg.click('#turnbtn'); pg.wait_for_timeout(450)
        check(D(pg, 'state()')['view'] == v, f'view {v} saved')
        # every tile of every building: the tile under its centre on screen is that tile
        bad = pg.evaluate('''() => { const D = window.MaplewickDebug, s = D.state(), out = [];
          for (const b of s.buildings) for (let c = b.c; c < b.c + 2; c++) for (let r = b.r; r < b.r + 2; r++) { if (c >= 18 || r >= 18) continue;
            const p = D.tileToClient(c, r), t = D.tileAt(p.x, p.y); if (!t || t.c !== c || t.r !== r) out.push([c, r, t]); }
          return out.slice(0, 5); }''')
        check(not bad, f'view {v}: the tile under the finger is the right one {bad}')
        # and a real tap on a building with no card open opens its card
        x = [b for b in blds if b['type'] == 'market'][0]
        for _ in range(4):
            if not D(pg, 'panel()'): break
            if pg.is_visible('#mpanel [aria-label="Close"]'): pg.click('#mpanel [aria-label="Close"]')
            else: pg.mouse.click(215, 300)
            pg.wait_for_timeout(250)
        D(pg, f"lookAt({x['c']}, {x['r']})"); pg.wait_for_timeout(200)
        pt = D(pg, f"tileToClient({x['c']}, {x['r']})"); pg.mouse.click(pt['x'], pt['y'] - 4); pg.wait_for_timeout(400)
        pn = D(pg, 'panel()')
        check(bool(pn) and pn.get('bid') == x['id'], f"view {v}: tapping the market opens its card ({pn and pn.get('bid')} vs {x['id']})")
        D(pg, 'sky(22.5)'); pg.wait_for_timeout(300)
        pg.screenshot(path=SH + f't06_view{v}.png')
        D(pg, 'sky()')
    # drag and drop: a new building appears on a free spot; drag it and let go: it lands where the finger points
    for v in (2, 0):
        D(pg, f'view({v})'); pg.wait_for_timeout(200)
        pv0 = D(pg, "place('bakery')") and D(pg, 'preview()')
        check(bool(pv0), f'view {v}: a new building appears on a free spot ({pv0})')
        p0 = D(pg, f"tileToClient({pv0['c']}, {pv0['r']})")
        # a free target tile a few tiles away
        tgt = pg.evaluate("""([c0, r0]) => { const D = window.MaplewickDebug; for (let d = 3; d < 9; d++) for (const [dc, dr] of [[d, 0], [0, d], [-d, 0], [0, -d]]) { const c = c0 + dc, r = r0 + dr; if (c < 1 || r < 1 || c > 16 || r > 16) continue; const p = D.tileToClient(c, r); if (p.y < 140 || p.y > 700 || p.x < 40 || p.x > 390) continue; if (D.fits('bakery', c, r)) return { c, r, p }; } return null; }""", [pv0['c'], pv0['r']])
        if not tgt: print('   no free target on screen'); continue
        pg.mouse.move(p0['x'], p0['y'] - 6); pg.mouse.down()
        pg.mouse.move((p0['x'] + tgt['p']['x']) / 2, (p0['y'] + tgt['p']['y'] + 34) / 2, steps=5)
        pg.mouse.move(tgt['p']['x'], tgt['p']['y'] + 34, steps=5); pg.wait_for_timeout(100)
        pg.screenshot(path=SH + f't06_drag{v}.png')
        pg.mouse.up(); pg.wait_for_timeout(400)
        pv1 = D(pg, 'preview()')
        check(bool(pv1) and pv1['c'] == tgt['c'] and pv1['r'] == tgt['r'], f"view {v}: dropped where the finger was ({pv1} vs {tgt['c']},{tgt['r']})")
        check(D(pg, 'panel()') and D(pg, 'panel()').get('kind') == 'place', f'view {v}: the Build it card is open')
        pg.click('#mpanel button:has-text("Cancel")'); pg.wait_for_timeout(300)
    D(pg, 'view(3)')
    pg.click('#turnbtn'); pg.wait_for_timeout(300)
    check(D(pg, 'state()')['view'] == 0, 'four turns come back round')
    pg.click('#turnbtn'); pg.wait_for_timeout(300); pg.reload(); pg.wait_for_timeout(1200)
    check(D(pg, 'state()')['view'] == 1, 'the view is kept after a reload')
    b.close()
print('no page errors' if not errs else 'ERRORS', errs[:5])
print('FAILS', fails)
