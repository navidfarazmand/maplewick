import json, sys
from playwright.sync_api import sync_playwright
import os, pathlib
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
SH = str(HERE / 'shots') + '/'
os.makedirs(SH, exist_ok=True)
hour=float(sys.argv[1]) if len(sys.argv)>1 else 12
def D(pg,e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844})
    pg=ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(700); st=D(pg,'state()'); pg.close()
    st['named']=True; st['flags']['tourDone']=True; st['flags']['coachAsked']=True; st['gold']=3000; st['playSec']=1800
    for bb in st['buildings']:
        bb.pop('ruin',None)
        if bb['type']=='townhall': bb['level']=2
    st['questsDone']=['gift','repair']; st['tray']=[]
    st['buildings'].append({'id':400,'type':'shed','c':3,'r':7,'level':1,'origin':'built'})
    st['staff']['gardener']=2
    pg=ctx.new_page(); pg.on('pageerror', lambda e: print('PAGEERROR',e))
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', "+json.dumps(json.dumps(st))+"); sessionStorage.setItem('seeded','1'); }")
    pg.goto(URL); pg.wait_for_timeout(900)
    D(pg,'play()'); pg.wait_for_timeout(500)
    D(pg,f'sky({hour})'); pg.wait_for_timeout(300)
    print('staff', D(pg,'staffWorking("gardener")'))
    f=D(pg,'fallen()'); print('fallen', f)
    for i in range(12):
        pg.wait_for_timeout(2500)
        w=[x for x in D(pg,'walkers()') if x['role']=='gardener']
        still=pg.evaluate(f"() => !!window.MaplewickDebug.state().buildings.find(b => b.id === {f['id']})")
        print(i, still, [(x['state'],x['act'],round(x['c'],1),round(x['r'],1),x['asleep'],x['indoors']) for x in w])
        if not still: break
    b.close()
