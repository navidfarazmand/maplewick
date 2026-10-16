import json, time
from playwright.sync_api import sync_playwright
import os, pathlib
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
SH = str(HERE / 'shots') + '/'
os.makedirs(SH, exist_ok=True)
def D(pg,e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844})
    pg=ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st=D(pg,'state()'); pg.close()
    st['named']=True; st['flags']['tourDone']=True; st['flags']['coachAsked']=True; st['gold']=300; st['playSec']=1800
    for bb in st['buildings']: bb.pop('ruin',None)
    st['questsDone']=['gift','repair']; st['tray']=[]
    st['combo']={'n':2,'until':int(time.time()*1000)+15*60000}
    pg=ctx.new_page()
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', "+json.dumps(json.dumps(st))+"); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.evaluate("() => document.querySelector('#btn-focus').click()"); pg.wait_for_timeout(500)
    print(pg.eval_on_selector_all('.durations button','els => els.map(e => [e.querySelector("b").textContent, e.querySelector(".gold").textContent, (e.querySelector(".note")||{}).textContent||"", getComputedStyle(e).backgroundColor])'))
    el=pg.query_selector('.durations'); el.screenshot(path=SH+'combo_now.png')
    b.close()
