# Maplewick

A focus game for people with ADHD: you are the mayor of a small island town, real focus time builds it, and play time is the break.

- **Play it:** https://navidfarazmand.github.io/maplewick/ (add it to the iPhone home screen; it works offline).
- **The live app** is the `gh-pages` branch (what GitHub Pages serves).
- **This branch (`main`)** keeps the source and the tools, at version 12.00:

| | |
|---|---|
| `app/maplewick.html` | The whole game in one file (HTML, CSS, JavaScript). Open it in a browser to run it. |
| `app/github-pages/` | The home-screen copy as it is on `gh-pages`. |
| `tools/build_pages.py` | Builds the home-screen copy from `app/maplewick.html`: `python3 tools/build_pages.py 10.20` |
| `tools/README.md` | How to publish a new version, check the file, and run the browser tests in `tools/tests/`. |
| `mobile/` | The Android app (Expo): the game from GitHub Pages plus the phone-pickup check, lock-screen countdown, alarms with the app closed and Google sign-in. See `mobile/README.md`. |
| `server/` | Version 12's server (Firebase functions and rules): focus minutes timed by the server and the weekly leagues worked out in one place. See `server/README.md`. |
| `tools/fb/` | Builds `app/github-pages/fb.js`, the small Firebase helper the game loads. |
| `design/combo_options_preview.html` | The four looks tried for the combo bonus on the focus time blocks (Stamp is the one in the game since 10.14). |

## A new version, step by step

1. Edit `app/maplewick.html` and set `APP_VERSION` to the new number (10.20, 10.21…).
2. `python3 tools/build_pages.py 10.20`
3. Put `app/github-pages/index.html` and `app/github-pages/sw.js` (and `fb.js` when it changed) on the `gh-pages` branch. Phones pick it up the second time the app is opened.
4. Commit `app/` here too, so `main` stays the source.
