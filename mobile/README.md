# Maplewick for Android

The phone app. It shows the game from GitHub Pages (https://navidfarazmand.github.io/maplewick/), so every new version of the game reaches the app the same way it reaches the home-screen app: no new app build needed. The app adds what a web page can't do.

| What | How |
|---|---|
| **Phone-pickup check** | During focus the app notes when the screen goes off or on, when the phone is unlocked, and when Maplewick goes to the back or comes to the front (`modules/focus-guard`). The game decides: unlocked with Maplewick in the back for **15 seconds** or more counts as picking up the phone, and the session ends where you left. The screen going off, a quick look, or coming back in time doesn't count. In the safe minutes after a lap it counts as taking your break. |
| **"Your focus is still running"** | Unlock the phone with Maplewick in the back and a notification says so, so a reflex unlock can be undone in time. |
| **Lock-screen countdown** | While Maplewick is in the back during focus, a quiet notification counts down to the end of the lap or session. |
| **Alarms with the app closed** | Lap done, break over, "Focus done!", Today's focus plan blocks, and set times with friends (10 minutes before) are scheduled when you leave the app, and cleared when you come back. |
| **Friends' notifications** | With the server live (`server/`), invitations to focus together, gifts, trades and loans from friends arrive as notifications, even with Maplewick closed. Uses Firebase Cloud Messaging (`google-services.json`, registered in Firebase as "Maplewick Android"). |
| **Google sign-in** | Google doesn't allow its sign-in page inside apps, so the app signs in natively and hands the token to the game, which gives it to Firebase as before. |
| **Back button** | Closes the open sheet; on Home it sends Maplewick to the back (it keeps running). |

The game side is the "11.11: the Android app" section of `app/maplewick.html`. In a browser it stays off. The test is `tools/tests/t1111_app.py`.

## Files

| | |
|---|---|
| `App.tsx` | The app: the game in a WebView, messages both ways, notifications, Google sign-in |
| `src/bridge.ts` | The script put into the page before it loads: `window.MaplewickApp`, a stand-in for the browser's Notification API, and `document.hidden` when the app goes to the back |
| `modules/focus-guard/` | The Android code (Kotlin): the pickup log, the nudge and the lock-screen countdown |
| `app.config.js` | Adds `google-services.json` (Firebase messaging) to the build when the file is there |
| `google-services.json` | The Firebase config for Android (not secret: the same public key the web game uses) |
| `app.json` | Name, package `com.khoreh.maplewick`, icons, permissions, the game's address (`extra.gameUrl`) |
| `eas.json` | Build profiles: `preview` makes an APK to install on your phone, `production` an app bundle for Google Play |

## Getting the app on your phone (free, no accounts)

GitHub builds the app on its own computers whenever `mobile/` changes (`.github/workflows/android.yml`), or by hand: Actions → Android test build → Run workflow. It takes about 15 minutes and costs nothing.

On the Samsung, open **https://github.com/navidfarazmand/maplewick/releases/tag/android-test**, tap `maplewick-test.apk`, and install it. Android asks once to allow installs from your browser. Newer test builds install over the old one and keep your town.

The test build is signed with React Native's standard test key, so it's for your own phones only. Google Play needs a real key: when the time comes, build with EAS (`npm run build:android:store`, free Expo account) or a key of your own.

The game itself comes from the website, so a new game version doesn't need a new app build, only changes in `mobile/` do.

## Google sign-in: one setup step

Google only gives the app a sign-in if it knows the app's package and signing key. In the Google Cloud console, project **maplewick-eb4df** → APIs & Services → Credentials → Create credentials → OAuth client ID → **Android**:

- Package name: `com.khoreh.maplewick`
- SHA-1 (the test key): `5E:8F:16:06:2E:A3:CD:2C:4A:0D:54:78:76:BA:A6:F3:8C:AB:F6:25`

Nothing else changes: the game keeps using its web client ID. For Google Play later, add Google Play's own SHA-1 (Play Console → App integrity) the same way.

## On the Samsung

Samsung closes apps in the back to save battery. For a fair pickup check: Settings → Apps → Maplewick → Battery → **Unrestricted**. When the game asks to allow notifications, allow them, and allow "Alarms & reminders" on the screen that follows, so lap bells ring on time.

## What to try first

- Start a 25-minute focus, lock the phone, wait, unlock: the countdown is on the lock screen; back in Maplewick, focus goes on.
- During focus, open another app for a few seconds and come back: still focusing.
- Open another app and stay 20 seconds: the "still running" notification, then "Sam stopped working" when you come back.
- Laps: after a lap, open another app: you're on your break, the lap is kept.
- Leave the app during a lap and wait for the lap to end: the bell rings with the app in the back.
- Friends → Sign in with Google (after the setup step above).

## iPhone

Not yet. The app is ready for it except the pickup module, which on iPhone needs Apple's Screen Time permission (Family Controls), and the Google sign-in plugin needs `iosUrlScheme` in `app.json`.
