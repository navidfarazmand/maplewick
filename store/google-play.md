# Google Play: everything to paste in

Prepared 18 October 2026 for the Khoreh developer account. Each part says where it goes in Play Console. Anything marked **Your call** is a decision for Navid; the suggestion is first.

## Create app

| Field | Answer |
|---|---|
| App name | **Maplewick: Focus Town** (30 characters at most; "Maplewick" alone also works. It can be changed any time.) |
| Default language | English (United States) – en-US |
| App or game | **App** (Your call: "Game" puts it next to games, where focus apps are rare; "App" puts it in Productivity, where people look for focus timers. Suggested: App, category Productivity.) |
| Free or paid | Free (a free app can never become paid later; in-app purchases are still possible) |

## Store listing (Grow → Store presence → Main store listing)

**Short description** (80 characters at most):

> A cozy island town that only grows while you focus. Made for ADHD minds.

**Full description** (4,000 characters at most):

> Maplewick is a little island town that only grows while you focus.
>
> Start a session, put your phone down, and come back to new streets, happy neighbours and a chest of gold. Focus is the gate; play is the break.
>
> HOW IT WORKS
> • Pick a length, from 5 minutes to 2 hours, or work in laps of 25 minutes with 5-minute breaks.
> • Put the phone away. Sam the builder works on the town while you work on your thing.
> • Every session pays gold, XP and play time, and ends with a chest: wooden, silver, gold or royal.
> • Spend your play time building and running the town. When it runs out, the break is over.
>
> MADE FOR WANDERING MINDS
> • Five minutes counts. Short sessions earn their share, and starting again soon builds a combo.
> • A break with edges: you bank at most 45 minutes of play, so the game never swallows the evening.
> • Name what you're working on. Each lap gets a small step, and finished projects become stones on your town's Monument.
> • Every problem is a button: a fire, trash on the street, a sick neighbour. Tap it and the fix is right there.
> • Quiet while you work: nothing goes wrong in town while you focus, and a finished session shields it.
>
> A TOWN THAT KEEPS LIVING
> Days, weather and seasons. Firefighters, police, nurses, teachers, sweepers and gardeners each work from their own building and only reach so far, so where you build matters. Grow from a few cottages to a harbour town with a farm, a market hall and a Monument to everything you finished.
>
> FRIENDS, NOT FEEDS
> • Weekly leagues count one thing: real minutes of focus. Nothing you buy or win adds to them.
> • Focus together with up to 4 friends: you see their workers walk to work beside yours. No chat while you focus.
> • Visit friends' towns, send gifts, trade food, and reach the weekly Town Fair together.
> • Signing in is optional. Your town works without an account.
>
> THE PHONE APP
> • A gentle phone-pickup check: unlock the phone and leave Maplewick during focus, and you get a reminder to come back. Stay away, and the session ends where you left. The record stays on your phone.
> • The time left on your lock screen, and a bell at the end of every lap.
>
> Free, no ads. Maplewick is a game that helps you practise focusing; it is not a treatment for ADHD.
>
> Privacy: https://khoreh.com/privacy.html · Support: https://khoreh.com/support.html

**Graphics** (in `store/`, made from the game):

| Asset | File | Size |
|---|---|---|
| App icon | `store/icon-512.png` | 512 × 512 |
| Feature graphic | `store/feature-graphic.png` | 1024 × 500 |
| Phone screenshots | `store/screenshots/*.png` | 1080 × 1920 (Play needs 2 to 8) |

**Contact details:** email hello@khoreh.com, website https://khoreh.com. Phone number: leave empty.

**Privacy policy URL:** https://khoreh.com/privacy.html

## App content (Policy → App content)

**Ads:** No, the app doesn't contain ads.

**App access:** All functionality is available without special access. (Sign-in is optional and Google sign-in needs no test account.)

**Content rating** (IARC questionnaire): category *All other app types*; answers:
- Violence: No. (Fires, thieves, pirates and bandit camps are cartoon town events; nobody is shown being hurt.) If the form asks about "fantasy violence", answer No.
- Fear, sexuality, language, drugs, gambling: No. Chests are rewards for focusing; they can't be bought, so this is not gambling or loot boxes.
- Users can interact or exchange content: **Yes** (leaderboard names, visits, gifts between friends). Shares location: No. Digital purchases: No.
Expected rating: Everyone / PEGI 3, with "Users Interact".

**Target audience:** 13–15, 16–17 and 18 and over (not under 13; the privacy policy says so). The app is not designed for children.

**News app:** No. **COVID-19:** No. **Government app:** No. **Financial features:** None (the loans are game gold). **Health:** No health features (it does not treat ADHD; don't tick health).

**Data safety** (what Maplewick collects; it shares nothing and sells nothing):

| Data type | Collected? | Why | Optional? |
|---|---|---|---|
| Personal info → Name | Yes (the leaderboard name you choose) | App functionality | Yes, only if you join the leaderboard |
| Personal info → Email address | Yes (kept by Firebase sign-in, never shown) | Account management | Yes, only with Google sign-in |
| Personal info → User IDs | Yes (the Firebase account ID) | App functionality, account management | Yes |
| App activity → Other user-generated content | Yes (town name, layout, Monument names you choose to show) | App functionality | Yes |
| App activity → Other actions | Yes (focus minutes per day and week, league results) | App functionality | Yes |
| Location, contacts, photos, files, messages, health, financial info, device IDs | No | | |

- Is all data encrypted in transit? **Yes** (HTTPS).
- Can users ask for their data to be deleted? **Yes**: in the game (Friends → Leave) or by email to hello@khoreh.com.
- The phone-pickup record never leaves the phone, so it isn't "collected" in Play's sense.

## Testing (Test and release → Testing → Closed testing)

New personal accounts need **12 testers opted in for 14 days in a row** before applying for production.

1. Create a closed testing track and a list of testers (their Gmail addresses).
2. Upload the release (an `.aab` signed with the upload key, see below) and roll it out to the track.
3. Send testers the opt-in link from the track page. They tap it, accept, and install from Google Play.
4. After 14 days with at least 12 testers, Dashboard → Apply for production.

## The release build

Google Play needs an Android App Bundle signed with your own upload key (the test builds use a public test key and can't be uploaded). Two ways, both free:

- **EAS (Expo):** free Expo account; in `mobile/`: `npx eas-cli@latest build --platform android --profile production`. EAS makes and keeps the upload key, and the `.aab` downloads from expo.dev.
- **GitHub:** an upload key saved as repository secrets, and the Android workflow builds the `.aab` too. Claude can set this up; the key's passwords have to be typed into GitHub by Navid.

After the first upload, Play Console → Test and release → App integrity shows **Play's app-signing SHA-1**. Add it as a second Android OAuth client in Google Cloud (same package, `com.khoreh.maplewick`), or Google sign-in won't work in the Play version.
