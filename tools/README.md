# Tools

## build_pages.py: make the home-screen (GitHub Pages) copy

```
python3 tools/build_pages.py 10.17
```

Run it from the top folder (the one with `app/` and `tools/`). It turns `app/maplewick.html` into `app/github-pages/index.html` and sets the cache name in `app/github-pages/sw.js` to `maplewick-10.17`. Change `APP_VERSION` in `app/maplewick.html` to the same number first (the script warns if they differ). Use a new version number every time: the new cache name is what makes phones download the update.

Then put `index.html` and `sw.js` on the `gh-pages` branch of github.com/navidfarazmand/maplewick, either with git:

```
git clone --branch gh-pages https://github.com/navidfarazmand/maplewick.git
cp app/github-pages/index.html app/github-pages/sw.js maplewick/
cd maplewick && git add index.html sw.js && git commit -m "Maplewick 10.17" && git push
```

or on github.com: open the repo, switch to the `gh-pages` branch, Add file → Upload files, drop the two files, Commit. GitHub rebuilds the site in a minute or two. On the phone, open the app, close it and open it again.

## Checking the file for mistakes

The game is one big script, so one typo stops the whole game. A quick check with Node.js:

```
node -e "const fs=require('fs');const h=fs.readFileSync('app/maplewick.html','utf8');let m,o='';const re=/<script(?![^>]*src)[^>]*>([\s\S]*?)<\/script>/g;while((m=re.exec(h)))o+=m[1]+'\n;\n';fs.writeFileSync('/tmp/chk.js',o)" && node --check /tmp/chk.js && echo OK
```

## tests/: automatic checks in a real browser

These open the game in Chromium with Playwright, set up a town, and check things (moves, time away, the silver shield, laps, gardeners…). Screenshots go to `tools/tests/shots/`.

```
pip install playwright
python3 -m playwright install chromium
python3 tools/tests/t13_move.py
```

When the browser is automated, the game turns on `window.MaplewickDebug`: helpers such as `play()`, `addBuilding(type, level)`, `moveTo(id, c, r)`, `crewAhead(seconds)`, `away(minutes, {silver})`, `fire(id)`, `rescue(id)`, `skipReady()`, `jumpFocus(minutes)`, `queue()`, `state()`. Search for `MaplewickDebug` in the game file to see them all. Each test seeds a town by writing a save into localStorage (key `maplewick-town-v7`) before the page loads.

`t13_laps.py` reports two "FAIL" lines that are expected: the test measures time at test speed, where a few extra minutes pass before the click. The game behaves correctly there.

Set `MAPLEWICK_URL` to test another copy, for example the live site:

```
MAPLEWICK_URL=https://navidfarazmand.github.io/maplewick/ python3 tools/tests/t13_err.py
```
