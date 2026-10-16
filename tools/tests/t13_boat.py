import json, math
from playwright.sync_api import sync_playwright
import os, pathlib
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
SH = str(HERE / 'shots') + '/'
os.makedirs(SH, exist_ok=True)
def D(pg,e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2)
    pg=ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st=D(pg,'state()'); pg.close()
    st['named']=True; st['flags']['tourDone']=True; st['flags']['coachAsked']=True; st['gold']=3000; st['playSec']=1800; st['speed']=60
    for bb in st['buildings']: bb.pop('ruin',None)
    st['questsDone']=['gift','repair']; st['tray']=[]
    st['buildings'].append({'id':300,'type':'police','c':9,'r':9,'level':1,'origin':'built'})
    st['queue']=[{'id':301,'kind':'upgrade','type':'police','bid':300,'fromLevel':1,'toLevel':2,'work':50,'done':0,'paid':100,'mode':'focus'}]
    st['flags']['laps1013']=True; st['flags']['laps1012']=True
    pg=ctx.new_page(); pg.on('pageerror', lambda e: print('PAGEERROR',e))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', "+json.dumps(json.dumps(st))+"); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900)
    if pg.is_visible('#intro'): pg.click('#intro'); pg.wait_for_timeout(2500)
    D(pg,'play()'); pg.wait_for_timeout(800)
    D(pg,"sky(12)"); D(pg,"boatAt(0.9)")
    # look at the boat position: south-east of island
    pg.evaluate("() => { const ev = new WheelEvent('wheel', {deltaY: -500, clientX: 195, clientY: 420, bubbles: true}); document.querySelector('#map').dispatchEvent(ev); }"); pg.wait_for_timeout(400)
    D(pg,"lookAt(18,12)"); pg.wait_for_timeout(1500)
    pg.screenshot(path=SH+'60_boat.png')
    D(pg,"sky(1)"); pg.wait_for_timeout(1200); pg.screenshot(path=SH+'61_boat_night.png')
    D(pg,"sky(12)")
    # focus scene: Sam hammering
    D(pg,"boatAt(null)")
    pg.evaluate("() => document.querySelector('#play-focus') && 0")
    pg.evaluate("() => { window.MaplewickDebug; }")
    b.close()
