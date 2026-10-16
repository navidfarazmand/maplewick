from playwright.sync_api import sync_playwright
import os, pathlib
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
SH = str(HERE / 'shots') + '/'
os.makedirs(SH, exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page()
    pg.on('pageerror', lambda e: print('PAGEERROR', e.message, (e.stack or '')[:500]))
    pg.goto(URL); pg.wait_for_timeout(1500)
    print(pg.evaluate("() => !!window.MaplewickDebug"))
    b.close()
