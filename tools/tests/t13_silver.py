import json
from playwright.sync_api import sync_playwright
import os, pathlib
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
SH = str(HERE / 'shots') + '/'
os.makedirs(SH, exist_ok=True)
def D(pg,e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844})
    pg=ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st=D(pg,'state()'); pg.close()
    st['named']=True; st['flags']['tourDone']=True; st['flags']['coachAsked']=True; st['gold']=300; st['playSec']=1800
    for bb in st['buildings']: bb.pop('ruin',None)
    st['questsDone']=['gift','repair']; st['tray']=[]
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', "+json.dumps(json.dumps(st))+"); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.evaluate("() => document.querySelector('#btn-focus').click()"); pg.wait_for_timeout(400)
    (pg.click('.set-tog.card') if pg.is_visible('.set-tog.card') else None); pg.wait_for_timeout(250)
    pg.click('.durations button:nth-child(3)'); pg.wait_for_timeout(200)  # 15m
    pg.click('.startsheet .btn.primary.full'); pg.wait_for_timeout(300)
    print('sess', bool(D(pg,'state()')['session']))
    D(pg,'skipReady()'); D(pg,'jumpFocus(16)'); pg.wait_for_timeout(900)
    print('after', bool(D(pg,'state()')['session']), D(pg,'state()')['streak'])
    pg.reload(); pg.wait_for_timeout(900); D(pg,'endShield()'); pg.wait_for_timeout(600)
    print('home chip:', pg.inner_text('#silver-home'), pg.is_visible('#silver-home'))
    pg.screenshot(path=SH+'silver1_progress.png')
    pg.evaluate("() => document.querySelector('#btn-focus').click()"); pg.wait_for_timeout(400)
    (pg.click('.set-tog.card') if pg.is_visible('.set-tog.card') else None); pg.wait_for_timeout(250)
    pg.click('.durations button:nth-child(3)'); pg.wait_for_timeout(200)
    pg.click('.startsheet .btn.primary.full'); pg.wait_for_timeout(300)
    D(pg,'skipReady()'); D(pg,'jumpFocus(16)'); pg.wait_for_timeout(1200)
    print('silver', D(pg,'silver()'))
    print('cele', pg.inner_text('#cele-lines') if pg.is_visible('#cele-lines') else '-')
    pg.screenshot(path=SH+'silver2_cele.png')
    pg.reload(); pg.wait_for_timeout(900); D(pg,'endShield()'); pg.wait_for_timeout(600)
    print('home chip:', pg.inner_text('#silver-home'), pg.is_visible('#silver-home'))
    pg.screenshot(path=SH+'silver3_on.png')
    print('ERRORS', errs)
    b.close()
