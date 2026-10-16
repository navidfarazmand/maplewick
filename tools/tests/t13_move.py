import json, sys, os
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
    st['named']=True; st['flags']['tourDone']=True; st['flags']['coachAsked']=True; st['flags']['fireSeen']=True; st['gold']=3000; st['playSec']=1800
    for bb in st['buildings']:
        bb.pop('ruin',None)
        if bb['type']=='townhall': bb['level']=2
    st['questsDone']=['gift','repair']; st['tray']=[]
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', "+json.dumps(json.dumps(st))+"); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900)
    D(pg,'play()'); pg.wait_for_timeout(500)
    fs=D(pg,"addBuilding('firestation', 1)")
    home=[x for x in D(pg,'state()')['buildings'] if x['type']=='cottage' or x.get('resident')][0]
    print('firestation', fs, 'home', home['id'], home['type'])
    for bid in (fs, home['id']):
        print('moveInfo', bid, D(pg,f'moveInfo({bid})'))
    g0=D(pg,'state()')['gold']
    mi=D(pg,f'moveInfo({fs})')
    spot=D(pg,f"freeSpot({mi['c']+3},{mi['r']+2})")
    print('spot', spot)
    res=D(pg,f"moveTo({fs},{spot['c']},{spot['r']},0)")
    print('moveTo', res)
    g1=D(pg,'state()')['gold']; print('gold', g0, '->', g1, 'paid', g0-g1)
    print('after start', D(pg,f'moveInfo({fs})'))
    pg.wait_for_timeout(5000)
    print('vehicles', [(v['kind'],v['state'],v['target']) for v in D(pg,'vehicles()')])
    D(pg,f"lookAt({mi['c']},{mi['r']})"); pg.wait_for_timeout(2500)
    pg.screenshot(path=SH+'move1_down.png')
    print('after 7s', D(pg,f'moveInfo({fs})'))
    secs=mi['secs']
    print('crewAhead down*0.6', D(pg,f"crewAhead({secs['down']*0.6})"))
    print(D(pg,f'moveInfo({fs})'))
    pg.wait_for_timeout(1500); pg.screenshot(path=SH+'move2_down.png')
    print('crewAhead down*0.45', D(pg,f"crewAhead({secs['down']*0.45})"))
    info=D(pg,f'moveInfo({fs})'); print(info)
    pg.wait_for_timeout(1200)
    print('vehicles', [(v['kind'],v['state'],v['target'],round(v['c'],1),round(v['r'],1)) for v in D(pg,'vehicles()')])
    pg.screenshot(path=SH+'move3_drive.png')
    pg.wait_for_timeout(5000)
    D(pg,f"lookAt({spot['c']},{spot['r']})"); pg.wait_for_timeout(2000)
    pg.screenshot(path=SH+'move4_up.png')
    print(D(pg,f'moveInfo({fs})'))
    print('crewAhead up', D(pg,f"crewAhead({secs['up']*1.05})"))
    info=D(pg,f'moveInfo({fs})'); print('final', info)
    pg.wait_for_timeout(1500); pg.screenshot(path=SH+'move5_done.png')
    # a cottage move: cost a quarter of its price, quick move for a decor
    D(pg,f"openCard({home['id']})"); pg.wait_for_timeout(500)
    print('card', pg.inner_text('#mpanel')[:400])
    print('ERRORS', errs)
    b.close()
