"""Makes store/feature-graphic.png (1024 x 500) from the first screenshot and the app icon."""
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
import base64, pathlib
from playwright.sync_api import sync_playwright
F = '/tmp/claude-0/fonts/node_modules/@fontsource/'
b64 = lambda p: base64.b64encode(pathlib.Path(p).read_bytes()).decode()
town = b64(str(ROOT) + '/store/screenshots/01-town.png'); icon = b64(str(ROOT) + '/store/icon-512.png')
html = f"""<!doctype html><html><head><style>
@font-face{{font-family:B;font-weight:800;src:url(data:font/woff2;base64,{b64(F+'baloo-2/files/baloo-2-latin-800-normal.woff2')})}}
@font-face{{font-family:Fig;font-weight:600;src:url(data:font/woff2;base64,{b64(F+'figtree/files/figtree-latin-600-normal.woff2')})}}
html,body{{margin:0;width:1024px;height:500px;overflow:hidden}}
body{{background:linear-gradient(135deg,#6B3FD6 0%,#4A23A8 55%,#2E1670 100%);position:relative;font-family:Fig}}
.txt{{position:absolute;left:64px;top:92px;width:520px;color:#fff}}
.ic{{width:92px;height:92px;border-radius:22px;box-shadow:0 8px 24px rgba(0,0,0,.25)}}
h1{{font-family:B;font-weight:800;font-size:66px;line-height:1.0;margin:22px 0 14px;letter-spacing:-.5px}}
h1 em{{font-style:normal;color:#FFD15C}}
p{{font-size:26px;margin:0;color:#E6DCFF}}
.ph{{position:absolute;right:70px;top:38px;width:300px;height:533px;border-radius:34px;overflow:hidden;transform:rotate(6deg);box-shadow:0 18px 50px rgba(0,0,0,.4);border:8px solid #1b1430}}
.ph img{{width:100%;display:block}}
</style></head><body>
<div class="txt"><img class="ic" src="data:image/png;base64,{icon}"><h1>Your <em>focus</em><br>builds a town.</h1><p>A cozy focus game for ADHD minds.</p></div>
<div class="ph"><img src="data:image/png;base64,{town}"></div>
</body></html>"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1024, 'height': 500})
    pg.set_content(html); pg.wait_for_timeout(500); pg.screenshot(path=str(ROOT) + '/store/feature-graphic.png'); b.close()
