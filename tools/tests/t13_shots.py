import base64
from playwright.sync_api import sync_playwright
import os, pathlib
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
SH = str(HERE / 'shots') + '/'
os.makedirs(SH, exist_ok=True)
def save(pg, expr, name):
    d=pg.evaluate(f"() => window.MaplewickDebug.{expr}"); open(SH+name,'wb').write(base64.b64decode(d.split(',')[1]))
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); pg.on('pageerror', lambda e: print('PAGEERROR',e))
    pg.goto(URL); pg.wait_for_timeout(1200)
    save(pg,'boatShot(1, 2000)','62_boat_r.png'); save(pg,'boatShot(-1, 15500)','63_boat_l_dolphin.png')
    save(pg,"personShot('hammer')",'64_hammer.png'); save(pg,"personShot('umbrella', true)",'65_umbrella.png')
    b.close()
