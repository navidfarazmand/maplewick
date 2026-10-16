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
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2)
    pg=ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st=D(pg,'state()'); pg.close()
    st['named']=True; st['flags']['tourDone']=True; st['flags']['coachAsked']=True; st['gold']=3000; st['playSec']=1800
    for bb in st['buildings']:
        bb.pop('ruin',None)
        if bb['type']=='townhall': bb['level']=3
        if bb['type'] in ('cottage','cafe','market'): bb['level']=2 if bb['type']!='cottage' else 3
    st['questsDone']=['gift','repair']; st['tray']=[{'id':900,'type':'gnome','origin':'chest'}]
    st['buildings'].append({'id':400,'type':'police','c':3,'r':7,'level':2,'origin':'built'})
    st['staff']['police']=1
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', "+json.dumps(json.dumps(st))+"); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900)
    if pg.is_visible('#intro'): pg.click('#intro'); pg.wait_for_timeout(2500)
    cafe=pg.evaluate("() => window.MaplewickDebug.state().buildings.find(b=>b.type==='cafe').id")
    cot=pg.evaluate("() => window.MaplewickDebug.state().buildings.find(b=>b.type==='cottage').id")
    print(D(pg,f"attach('awning',{cafe})"), D(pg,f"attach('mural',{cafe})"), D(pg,f"attach('solar',400)"), D(pg,f"attach('flowerbox',{cot})"), D(pg,f"attach('solar',{cot})"))
    D(pg,'play()'); pg.wait_for_timeout(1200)
    pg.screenshot(path=SH+'50_taskpop.png')
    pg.wait_for_timeout(2600)
    pg.screenshot(path=SH+'51_taskpill.png')
    D(pg,"weather('rain')"); D(pg,"sky(12)")
    D(pg,f"lookAt(5,6)"); pg.evaluate("() => { }")
    pg.wait_for_timeout(2500)
    pg.screenshot(path=SH+'52_rain_town.png')
    # zoom closer
    pg.evaluate("() => { const ev = new WheelEvent('wheel', {deltaY: -600, clientX: 195, clientY: 420, bubbles: true}); document.querySelector('#map').dispatchEvent(ev); }"); pg.wait_for_timeout(600)
    D(pg,f"lookAt(6,5)"); pg.wait_for_timeout(1500)
    pg.screenshot(path=SH+'53_rain_zoom.png')
    D(pg,"weather(null)")
    print('errors',errs)
    b.close()
