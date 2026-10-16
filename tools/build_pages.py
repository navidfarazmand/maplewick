"""Build the GitHub Pages copy of Maplewick (the iPhone home-screen app) from the game file.

Usage (from the folder that holds app/ and tools/):
    python3 tools/build_pages.py 10.14
    python3 tools/build_pages.py 10.14 --src app/maplewick.html --pages app/github-pages

What it does:
  * takes the game file (app/maplewick.html, the same file that runs as the Claude artifact);
  * swaps the artifact's one-line page wrapper for the Pages head (app icons, manifest, theme colour),
    which it copies from the index.html already in the pages folder;
  * adds the Pages-only style block and the Firebase settings (also copied from that index.html);
  * adds the service-worker line at the end, so the app works offline;
  * writes the new index.html and sets the cache name in sw.js to 'maplewick-<version>'.
    A new cache name is what makes phones fetch the new version, so use a new version every time.

Before running it, change APP_VERSION in the game file to the same version.
Then upload index.html and sw.js to the gh-pages branch of github.com/navidfarazmand/maplewick.
"""
import argparse, os, re, sys

ap = argparse.ArgumentParser()
ap.add_argument('version')
ap.add_argument('--src', default='app/maplewick.html')
ap.add_argument('--pages', default='app/github-pages')
a = ap.parse_args()

src = open(a.src, encoding='utf8').read()
prev_path = os.path.join(a.pages, 'index.html')
prev = open(prev_path, encoding='utf8').read()

# 1. the artifact wrapper line goes (it ends with <body>)
if src.startswith('<!doctype html><html><head>'):
    body0 = src[src.index('<body>') + len('<body>'):].lstrip('\n')
else:
    body0 = src
# 2. the Pages head: everything in the current Pages build before its <title>
pages_head = prev[:prev.index('<title>')]
# 3. the Pages-only block (style + Firebase settings) between the game's CSS and <body>
m = re.search(r'</style>\n(<style>\n  /\* Home-screen app:.*?</script>\n)</head>\n<body>\n', prev, re.S)
if not m:
    sys.exit('Could not find the Pages-only block in ' + prev_path)
pages_block = m.group(1)
# the game's main CSS ends at the first </style> followed by a blank line
i = body0.index('</style>\n\n')
head_part, rest = body0[:i + len('</style>\n')], body0[i + len('</style>\n\n'):]
# 4. the service worker
sw = ("<script>\n  // Works offline once opened: the service worker keeps a copy of the game.\n"
      "  if ('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));\n"
      "</script>\n")
rest = rest.rstrip()
for tail in ('</body></html>', '</body>\n</html>'):
    if rest.endswith(tail):
        rest = rest[:-len(tail)]
        break
rest = rest.rstrip('\n') + '\n'
out = pages_head + head_part + pages_block + '</head>\n<body>\n' + rest + sw + '</body>\n</html>\n'
open(prev_path, 'w', encoding='utf8').write(out)

sw_path = os.path.join(a.pages, 'sw.js')
s = open(sw_path, encoding='utf8').read()
s = re.sub(r"const CACHE = 'maplewick-[0-9.]+';", f"const CACHE = 'maplewick-{a.version}';", s)
open(sw_path, 'w', encoding='utf8').write(s)
ver = re.search(r"APP_VERSION = '([^']+)'", out)
print(f"index.html written ({len(out):,} bytes), game version {ver.group(1) if ver else '?'}, sw.js cache maplewick-{a.version}")
if ver and ver.group(1) != a.version:
    print(f"Warning: APP_VERSION in the game file is {ver.group(1)}, not {a.version}.")
