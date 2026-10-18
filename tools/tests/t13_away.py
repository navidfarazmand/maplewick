import json, sys
from playwright.sync_api import sync_playwright
import os, pathlib
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
SH = str(HERE / 'shots') + '/'
os.makedirs(SH, exist_ok=True)
def D(pg,e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
errs=[]; fails=[]
def check(c, m):
    print(('ok   ' if c else 'FAIL ')+m)
    if not c: fails.append(m)
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844})
    pg=ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st=D(pg,'state()'); pg.close()
    st['named']=True; st['flags']['tourDone']=True; st['flags']['coachAsked']=True; st['flags']['fireSeen']=True; st['gold']=3000; st['playSec']=1800
    for bb in st['buildings']:
        bb.pop('ruin',None)
        if bb['type']=='townhall': bb['level']=3
    st['questsDone']=['gift','repair']; st['tray']=[]
    def seeded(s):
        pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', "+json.dumps(json.dumps(s))+"); sessionStorage.setItem('seeded','1'); }")
        pg.goto(URL); pg.wait_for_timeout(900); return pg
    pg=seeded(st)
    for i in range(4): D(pg,"addBuilding('cottage',1)")
    # 1. crew catch-up: order a cottage, then 10 minutes away
    o=D(pg,"order('cottage')"); print('order', o)
    q0=D(pg,'queue()'); print(q0)
    n=D(pg,'away(10,{crew:true,silver:false})'); print('news', n)
    check(n and len(n['done'])>=1, 'a crew job finished while away is in the news')
    check(not [x for x in D(pg,'queue()') if not x['big']], 'crew queue empty after 10 min away')
    pg.wait_for_timeout(900)
    check(pg.is_visible('#sheet') and 'While you were away' in pg.inner_text('#sheet-title'), 'the While-you-were-away card shows')
    pg.screenshot(path=SH+'away1_crew.png')
    pg.evaluate("() => document.querySelector('#sheet-close').click()"); pg.wait_for_timeout(300)
    # 2. silver shield blocks trouble
    n=D(pg,'away(900,{silver:true})'); print('silver news', n)
    check(n and n['blocked']>=1 and not n['inc'], 'silver shield: trouble blocked, none happened')
    pg.wait_for_timeout(900); pg.screenshot(path=SH+'away2_silver.png')
    pg.evaluate("() => document.querySelector('#sheet-close').click()"); pg.wait_for_timeout(300)
    # 3. no shield: incidents happen (12 h away: 3)
    got=[]
    for k in range(4):
        n=D(pg,'away(720,{silver:false})');
        if n: got+=n['inc']
        pg.wait_for_timeout(700)
        pg.evaluate("() => { const x = document.querySelector('#sheet-close'); if (!document.querySelector('#scrim').hidden) x.click(); }"); pg.wait_for_timeout(200)
        fires=D(pg,'fires()')
        if fires: break
    print('incidents', [(i['kind'], i.get('rescue'), i['text'][:70]) for i in got])
    check(len(got)>=1, 'incidents happen while away without a shield')
    fires=D(pg,'fires()'); print('fires', fires)
    if fires:
        fid=fires[0]['id']
        D(pg,'play()'); pg.wait_for_timeout(600)
        D(pg,f'openCard({fid})'); pg.wait_for_timeout(500)
        txt=pg.inner_text('#mpanel'); print(txt[:500])
        check('Rescue it' in txt, 'card offers the rescue')
        pg.screenshot(path=SH+'away3_rescuecard.png')
        D(pg,f'rescue({fid})'); pg.wait_for_timeout(600)
        check(pg.is_visible('.startsheet') and not D(pg,'state()')['session'], '12.05: the rescue opens the start page, no countdown yet')
        print('   start page:', pg.inner_text('.startsheet')[:200].replace('\n',' | '))
        pg.screenshot(path=SH+'away3b_rescuestart.png')
        pg.click('.startsheet .btn.primary.full'); pg.wait_for_timeout(600)
        s=D(pg,'state()')['session']; check(s and s.get('rescue')==fid and s['duration']==10, 'a 10-minute rescue session')
        D(pg,'skipReady()'); D(pg,'jumpFocus(10.2)'); pg.wait_for_timeout(1200)
        check(not D(pg,'fires()'), 'the fire is out after the rescue')
        inc=[x for x in D(pg,'incidents()') if x['kind']=='fire' and x['bid']==fid]; print(inc[-1])
        check('Saved by your focus' in inc[-1]['outcome'], 'incident says saved by your focus')
        pg.screenshot(path=SH+'away4_rescued.png')
    # 4. silver shield from 30 min of focus
    pg2=seeded(st)
    pg2.evaluate("() => document.querySelector('#btn-focus').click()"); pg2.wait_for_timeout(400)
    (pg2.click('.set-tog.card') if pg2.is_visible('.set-tog.card') else None); pg2.wait_for_timeout(250)
    pg2.click('.durations button:nth-child(4)'); pg2.wait_for_timeout(200)  # 25m
    pg2.click('.startsheet .btn.primary.full'); pg2.wait_for_timeout(300)
    D(pg2,'skipReady()'); D(pg2,'jumpFocus(26)'); pg2.wait_for_timeout(900)
    print('silver after 25', D(pg2,'silver()'))
    check(not D(pg2,'silver()')['on'], 'no silver shield after 25 minutes')
    pg2.evaluate("() => { for (const id of ['cele-go','result-ok','cele-close']) { const x = document.getElementById(id); if (x) x.click(); } }"); pg2.wait_for_timeout(600)
    print('overlay', D(pg2,'overlay()'))
    pg2.screenshot(path=SH+'away5_home_progress.png')
    print(pg2.inner_text('#homebar')[:200])
    errs and print('ERRS', errs)
    print('FAILS', fails, 'ERRORS', errs)
    b.close()
