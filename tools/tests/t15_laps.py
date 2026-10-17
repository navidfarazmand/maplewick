import json
from playwright.sync_api import sync_playwright
import os, pathlib
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
SH = str(HERE / 'shots') + '/'
os.makedirs(SH, exist_ok=True)
errs=[]
def D(pg,e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844})
    pg=ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st=D(pg,'state()'); pg.close()
    st['named']=True; st['flags']['tourDone']=True; st['flags']['coachAsked']=True; st['speed']=60; st['gold']=3000; st['playSec']=600
    for bb in st['buildings']:
        bb.pop('ruin',None)
        if bb['type']=='townhall': bb['level']=3
    st['questsDone']=['gift','repair']; st['tray']=[]; st['flags']['laps1012']=True; st['flags']['laps1013']=True
    st['buildings'].append({'id':302,'type':'firestation','c':9,'r':2,'level':1,'site':True,'origin':'built'})
    st['queue']=[{'id':303,'kind':'build','type':'firestation','bid':302,'fromLevel':0,'toLevel':1,'work':125,'done':0,'paid':90,'mode':'focus'}]
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', "+json.dumps(json.dumps(st))+"); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.evaluate("() => document.querySelector('#btn-focus').click()"); pg.wait_for_timeout(600)
    print('ticks', pg.eval_on_selector_all('.lsw-tick','els => els.map(e => e.textContent)'))
    pg.click('.lsw-tick:nth-child(3)'); pg.wait_for_timeout(300)
    print('plan 45:', pg.inner_text('.lc-plan .lapplan').replace('\n',' '))
    pg.screenshot(path=SH+'s15_laps45.png')
    pg.click('.startsheet .btn.primary.full'); pg.wait_for_timeout(300)
    s=D(pg,'state()')['session']; print('lapLen', s.get('lapLen'), 'lapP', s.get('lapP'))
    D(pg,'skipReady()'); D(pg,'jumpFocus(36)'); pg.wait_for_timeout(300); print('lap', {k:v for k,v in D(pg,'lap()').items() if k in ('k','lf','into','left','lap','of','win')})
    D(pg,'jumpFocus(2)'); pg.wait_for_timeout(300); print('lap', {k:v for k,v in D(pg,'lap()').items() if k in ('k','lf','into','left','lap','of','win')})
    print('ERRORS', errs)
    b.close()
