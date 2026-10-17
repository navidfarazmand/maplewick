import json
from playwright.sync_api import sync_playwright
import os, pathlib
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
SH = str(HERE / 'shots') + '/'
os.makedirs(SH, exist_ok=True)
errs=[]
def check(c,m): print(('PASS ' if c else 'FAIL ')+m); (None if c else errs.append(m))
def D(pg,e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
def seeded(ctx, st):
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append('pageerror: '+str(e)))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', "+json.dumps(json.dumps(st))+"); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900)
    if pg.is_visible('#intro'): pg.click('#intro'); pg.wait_for_timeout(2500)
    return pg
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2)
    pg=ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); base=D(pg,'state()'); pg.close()
    base['named']=True; base['flags']['tourDone']=True; base['flags']['coachAsked']=True; base['speed']=60; base['gold']=3000; base['playSec']=600
    for bb in base['buildings']:
        bb.pop('ruin',None)
        if bb['type']=='townhall': bb['level']=2
    base['questsDone']=['gift','repair']; base['tray']=[]
    # a 10.11 save: police upgrade 67 min (rounds: 2 → 50), fire post 24 (single)
    st=json.loads(json.dumps(base)); st['flags'].pop('laps1012',None); st['flags'].pop('laps1013',None)
    st['buildings'].append({'id':300,'type':'police','c':9,'r':9,'level':1,'origin':'built'})
    st['buildings'].append({'id':302,'type':'firestation','c':9,'r':2,'level':1,'site':True,'origin':'built'})
    st['queue']=[{'id':301,'kind':'upgrade','type':'police','bid':300,'fromLevel':1,'toLevel':2,'work':67,'done':0,'paid':100,'mode':'focus'},
                 {'id':303,'kind':'build','type':'firestation','bid':302,'fromLevel':0,'toLevel':1,'work':24,'done':0,'paid':90,'mode':'focus'}]
    pg=seeded(ctx,st)
    q=D(pg,'queue()'); print(q)
    check(q[0]['work']==50 and q[1]['work']==24, 'over 30 min → whole rounds (67 → 2 rounds), 24 stays')
    pg.evaluate("() => document.querySelector('#btn-focus').click()"); pg.wait_for_timeout(500)
    check(pg.is_visible('.lapsw'), 'lap switch shows')
    ticks=pg.eval_on_selector_all('.lsw-tick','els => els.map(e => e.textContent)'); print('ticks',ticks)
    check(ticks==['15m','30m','45m','1h'], 'options for 2 rounds: 15, 30, 45 (37½ + 12½), 1h')
    durs=pg.eval_on_selector_all('.durations button b','els => els.map(e => e.textContent)'); print(durs)
    check(durs==['5m','10m','15m','25m','45m','1h','1h30','2h'], 'the eight fixed lengths')
    chips=pg.inner_text('.lc-plan .lapplan'); print('plan:',chips.replace('\n',' '))
    pg.screenshot(path=SH+'40_start_laps.png', full_page=False)
    # drag the switch to 15
    tr=pg.query_selector('.lsw-track').bounding_box()
    pg.mouse.move(tr['x']+tr['width']*0.5, tr['y']+tr['height']/2); pg.mouse.down(); pg.mouse.move(tr['x']+2, tr['y']+tr['height']/2, steps=5); pg.mouse.up(); pg.wait_for_timeout(400)
    chips=pg.inner_text('.lc-plan .lapplan'); print('plan 15:',chips.replace('\n',' '))
    check('12½' in chips, 'dragged to 15-minute laps: 12½ + 2½')
    pg.screenshot(path=SH+'41_start_15.png')
    sheet=pg.query_selector('#sheet'); sheet.evaluate("e => e.scrollTop = 9999"); pg.wait_for_timeout(200)
    pg.screenshot(path=SH+'42_start_bottom.png')
    pg.click('.startsheet .btn.primary.full'); pg.wait_for_timeout(500)
    s=D(pg,'state()')['session']; check(s and s.get('laps') and s.get('lapLen')==15, 'lap session with 15-min laps')
    pg.screenshot(path=SH+'43_getready.png')
    D(pg,'skipReady()'); pg.wait_for_timeout(300)
    D(pg,'jumpFocus(13)'); pg.wait_for_timeout(600)
    li=D(pg,'lap()'); print(li)
    check(li['win'] and li['k']==1, 'lap 1 of 12½ done → window')
    pg.screenshot(path=SH+'44_lapwin15.png')
    pg.click('#lap-break'); pg.wait_for_timeout(900)
    q=D(pg,'queue()'); print(q)
    check(abs(q[0]['done']-13)<0.3, 'all 13 minutes counted')
    lr=D(pg,'lapRun()'); print('lapRun',lr)
    pg.close()
    # fixed session: single fire post 24 + rounds; end early at 30: fire post done (24), police saved 0? m=30 → bank 25 → work 25 => fire 24 + police 1
    st2=json.loads(json.dumps(st)); st2['flags']['laps1013']=True; st2['flags']['laps1012']=True
    st2['queue'][0]['work']=50
    pg=seeded(ctx,st2)
    pg.evaluate("() => document.querySelector('#btn-focus').click()"); pg.wait_for_timeout(400)
    pg.click('.durations button:nth-child(5)'); pg.wait_for_timeout(300)  # 45m
    lab=pg.inner_text('.startsheet > .label:nth-of-type(2)') if pg.query_selector('.startsheet > .label:nth-of-type(2)') else ''
    print('label:', pg.eval_on_selector_all('.startsheet .label','els=>els.map(e=>e.textContent)'))
    pg.click('.startsheet .btn.primary.full'); pg.wait_for_timeout(300)
    s=D(pg,'state()')['session']; print('plan', s['plan'])
    check(s['plan'][0]==303, 'fixed session: short project first')
    D(pg,'skipReady()'); D(pg,'jumpFocus(40)'); pg.wait_for_timeout(300)
    pg.click('#focus-end'); pg.wait_for_timeout(200); print('confirm:', pg.inner_text('#focus-confirm-text'))
    pg.click('#focus-stop'); pg.wait_for_timeout(800)
    q=D(pg,'queue()'); print('after', q)
    st3=D(pg,'state()')
    fire=[x for x in st3['buildings'] if x['id']==302][0]
    check(not fire.get('site'), 'the short project finished stays built')
    check(len(q)==1 and abs(q[0]['done']-1)<0.5, f"rounds project kept the saved part only ({q[0]['done'] if q else None})")
    pg.close()
    b.close()
print('errors',errs)
