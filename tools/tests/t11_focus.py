# 11.01: name the project, a step per lap, the if-then, check-ins, the plaque and the Monument.
import json, os, pathlib
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
SH = str(HERE / 'shots') + '/'; os.makedirs(SH, exist_ok=True)
def D(pg, e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
errs = []; fails = []
def ok(c, m): print(('PASS ' if c else 'FAIL ') + m); (None if c else fails.append(m))
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 390, 'height': 844})
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st = D(pg, 'state()'); pg.close()
    st['named'] = True; st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['gold'] = 3000; st['playSec'] = 1200; st['speed'] = 1
    for bb in st['buildings']:
        bb.pop('ruin', None)
        if bb['type'] == 'townhall': bb['level'] = 2
    st['questsDone'] = ['gift', 'repair']; st['tray'] = []
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + "); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900)
    D(pg, 'play()')
    for i in range(4): D(pg, "addBuilding('townhouse', 1)")
    hall = [x for x in D(pg, 'state()')['buildings'] if x['type'] == 'townhall'][0]['id']
    up = D(pg, f'planUp({hall})'); ok(up['ok'], 'town hall 3 in the plan ' + up['why'])
    t = D(pg, 'tasks()'); ok(t and t[0]['work'] >= 50, f"a 2-lap project ({t[0]['work'] if t else None})")
    pg.evaluate("() => { document.querySelector('#play-focus') ? document.querySelector('#play-focus').click() : document.querySelector('#btn-focus').click(); }"); pg.wait_for_timeout(700)
    ok(pg.locator('.taskcard').count() == 1, 'the start sheet asks what you will work on')
    pg.fill('.tk-name', 'Thesis chapter 2'); pg.click('.taskcard .btn.primary'); pg.wait_for_timeout(400)
    steps = pg.eval_on_selector_all('.tk-step input', 'els => els.map(e => e.value)')
    ok(len(steps) == 2 and steps[0] == 'Outline and notes', f'a step for each lap {steps}')
    pg.screenshot(path=SH + 's11_task.png')
    pg.click('.taskcard .btn.primary'); pg.wait_for_timeout(300)
    ok('next: Outline and notes' in pg.inner_text('.taskcard'), 'folded card shows the next step')
    pg.evaluate("() => [...document.querySelectorAll('#sheet .btn.primary.full')].pop().click()"); pg.wait_for_timeout(500)
    ok('When the countdown ends' in pg.inner_text('#focus-task'), 'the if-then shows while getting ready: ' + pg.inner_text('#focus-task'))
    D(pg, 'skipReady()'); pg.wait_for_timeout(400)
    ok('Outline and notes' in pg.inner_text('#focus-list'), 'the lap shows its step')
    D(pg, 'jumpFocus(25.3)'); pg.wait_for_timeout(500)
    ok(pg.is_visible('#lapdone-check'), 'the check-in shows after the lap')
    pg.screenshot(path=SH + 's11_check.png')
    pg.click('#lapdone-check .ck-yes'); pg.wait_for_timeout(300)
    ok(not pg.is_visible('#lapdone-check'), 'answered')
    pg.click('#lap-skip'); pg.wait_for_timeout(300)
    D(pg, 'jumpFocus(25.3)'); pg.wait_for_timeout(500)
    pg.click('#lap-break'); pg.wait_for_timeout(900)
    ok(pg.is_visible('#cele-check'), 'the celebration asks about the second lap')
    pg.screenshot(path=SH + 's11_cele.png')
    pg.click('#cele-check .ck-yes'); pg.wait_for_timeout(400)
    txt = pg.inner_text('#cele-check'); print('cele:', txt)
    m = D(pg, 'monument()'); print(m)
    ok(m['m'] and len(m['m']['stones']) == 1 and m['m']['stones'][0]['laps'] == 2, 'a stone for the Monument, 2 laps')
    ok('monument' in m['tray'], 'the Monument waits in the tray')
    ok(any(l[1] == 'Thesis chapter 2' and l[2] for l in m['labels']), 'the town hall carries the name and a plaque')
    sn = D(pg, 'snapMonu()'); ok(sn and sn['show'] == 'names' and sn['s'][0][0] == 'Thesis chapter 2', 'visitors see the names by default')
    ok(not errs, 'no page errors ' + str(errs[:3]))
    b.close()
print('FAILS', fails)
