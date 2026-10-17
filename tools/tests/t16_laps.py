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
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844}, color_scheme='dark')
    pg=ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st=D(pg,'state()'); pg.close()
    st['named']=True; st['flags']['tourDone']=True; st['flags']['coachAsked']=True; st['speed']=60; st['gold']=900; st['playSec']=600
    for bb in st['buildings']:
        bb.pop('ruin',None)
        if bb['type']=='townhall': bb['level']=3
    st['questsDone']=['gift','repair']; st['tray']=[]
    st['combo']={'n':1,'until':int(time.time()*1000)+15*60000}
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', "+json.dumps(json.dumps(st))+"); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900)
    print('top chip:', pg.inner_text('#chip-res').replace('\n',' '))
    pg.evaluate("() => document.querySelector('#btn-focus').click()"); pg.wait_for_timeout(1200)
    pg.screenshot(path=SH+'s16_t1.png')
    pg.wait_for_timeout(1800); pg.screenshot(path=SH+'s16_t3.png')
    pg.wait_for_timeout(2000); pg.screenshot(path=SH+'s16_t5.png')
    ticks=pg.eval_on_selector_all('.lsw-tick','els => els.map(e => [e.textContent, e.style.left])'); print('ticks', ticks)
    print('thumb at', pg.eval_on_selector('.lsw-thumb','e => e.style.left'))
    pg.click('.lsw-tick:nth-child(3)'); pg.wait_for_timeout(300)
    print('card:', pg.inner_text('.lapcard').replace('\n',' | '))
    pg.click('.startsheet .btn.primary.full'); pg.wait_for_timeout(300)
    s=D(pg,'state()')['session']; print('session laps', s.get('laps'), s.get('lapLen'), s.get('lapP'))
    D(pg,'skipReady()'); pg.wait_for_timeout(300); print('eyebrow', pg.inner_text('#focus-eyebrow'))
    D(pg,'jumpFocus(38)'); pg.wait_for_timeout(500); L=D(pg,'lap()'); print('lap', L['k'], L['win'], L['lap'])
    pg.click('#lap-break'); pg.wait_for_timeout(1200)
    print('lapRun', D(pg,'lapRun()'))
    print('ERRORS', errs)
    b.close()
