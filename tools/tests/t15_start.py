import json, time
from playwright.sync_api import sync_playwright
import os, pathlib
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
SH = str(HERE / 'shots') + '/'
os.makedirs(SH, exist_ok=True)
def D(pg,e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
errs=[]
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':390,'height':844}, color_scheme='dark')
    pg=ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st=D(pg,'state()'); pg.close()
    st['named']=True; st['flags']['tourDone']=True; st['flags']['coachAsked']=True; st['gold']=900; st['playSec']=1800
    for bb in st['buildings']:
        bb.pop('ruin',None)
        if bb['type']=='townhall': bb['level']=3
    st['questsDone']=['gift','repair']; st['tray']=[]
    st['combo']={'n':1,'until':int(time.time()*1000)+15*60000}
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', "+json.dumps(json.dumps(st))+"); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900)
    for t in ('field','market','bakery','cafe'): D(pg,f"addBuilding('{t}',1)")
    D(pg,'play()'); pg.wait_for_timeout(800)
    pg.screenshot(path=SH+'s15_bar_closed.png')
    D(pg,'openBarNow && 0') if False else None
    pg.evaluate("() => document.getElementById('barhandle').click()"); pg.wait_for_timeout(500)
    pg.screenshot(path=SH+'s15_bar.png')
    bb=pg.query_selector('#playbar').bounding_box()
    pg.mouse.move(bb['x']+30, bb['y']+20); pg.mouse.down(); pg.mouse.move(bb['x']+30, bb['y']-20, steps=4); pg.wait_for_timeout(100)
    pg.screenshot(path=SH+'s15_bar_drag.png')
    pg.mouse.move(bb['x']+30, bb['y']-90, steps=4); pg.mouse.up(); pg.wait_for_timeout(1200)
    print('sheet open', pg.is_visible('#sheet'), pg.evaluate("() => document.getElementById('sheet').className"), pg.inner_text('#sheet-title'))
    pg.wait_for_timeout(2500)
    pg.screenshot(path=SH+'s15_start.png')
    (pg.click('.set-tog.card') if pg.is_visible('.set-tog.card') else None); pg.wait_for_timeout(300)
    jr=pg.query_selector('.jobs'); jr.evaluate("e => e.scrollLeft = 9999"); pg.wait_for_timeout(200)
    sl=jr.evaluate("e => e.scrollLeft"); btns=pg.query_selector_all('.jobs .jobchip'); btns[-1].click(); pg.wait_for_timeout(300)
    print('scroll before', sl, 'after', pg.query_selector('.jobs').evaluate("e => e.scrollLeft"))
    pg.query_selector('#sheet').evaluate("e => e.scrollTop = 9999"); pg.wait_for_timeout(200)
    pg.screenshot(path=SH+'s15_start_bottom.png')
    pg.click('.pextras-tog'); pg.wait_for_timeout(200); pg.screenshot(path=SH+'s15_start_extras.png')
    print('ERRORS', errs)
    b.close()
