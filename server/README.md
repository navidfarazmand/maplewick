# Maplewick's server (version 12)

The game works without it. When it's live, two things change:

- **Focus minutes are timed by the server.** When you're signed in, the game tells the server when a session starts and ends. The server notes the start time itself, so a session can only count the minutes that really passed (a phone that lies about its clock, or a changed save, gets nothing extra).
- **The weekly leagues are worked out in one place.** Every Monday at 00:10 (Toronto time) the server takes last week's minutes, cuts each league into groups of 30 real players, fills every group up to 30 with robot towns (a real player who joins takes a robot's place), and decides who moves up (top 10), who moves down (bottom 5) and who wins a trophy (top 3). The game shows that result instead of working it out on the phone. The robots and the maths are exactly the game's: a test checks them against the game file.

If the server isn't deployed, or is down, the game carries on exactly as in 11.x.

| | |
|---|---|
| `functions/index.js` | The three functions: `focusStart`, `focusEnd` (called by the game) and `weeklyLeagues` (every Monday) |
| `functions/core.js` | What they do, without Firebase, so it can be tested |
| `functions/leagues.js` | The league maths, the same as the game's |
| `firestore.rules` | Who may read and write what. The board is unchanged; the new data can only be written by the server |
| `functions/test/` | Unit tests: `cd functions && npm test` |
| `test/emulator.test.mjs` | The rules and functions in the Firebase emulators: `npm run test:emulator` (needs Java) |

GitHub runs all the tests on every change (Actions → Server tests).

## Data

| Collection | What | Who can read |
|---|---|---|
| `focus/{uid}` | This week's open session and the minutes the server timed, per week | the player |
| `leagueResults/{uid}` | Your league now and last week's result | the player |
| `leagueTables/{week}_{league}_{group}` | Last week's final tables | anyone signed in |
| `config/server` | `{ on: true, tz, appOnly }` | anyone |

`appOnly: true` (set it by hand in the Firebase console, in `config/server`) makes the leagues count only minutes focused in the Android app, where the phone-pickup check runs. Off by default, so web and iPhone players still take part.

## Going live (once)

1. **Blaze plan.** Firebase console → project *maplewick* → Upgrade → Blaze, with a budget (for example $5 a month) and an alert. Functions need Blaze; at Maplewick's size it should cost nothing, since Blaze includes the free usage.
2. **Deploy from your computer** (needs Node.js 22):
   ```
   cd server
   npm ci && (cd functions && npm ci)
   npx firebase login
   npm run deploy
   ```
   `npx firebase login` opens Google in your browser; sign in with the account that owns the project. The first deploy may ask to turn on a few Google Cloud APIs (Cloud Functions, Cloud Build, Artifact Registry, Cloud Scheduler) and links to each.

That's it: the next focus session marks the server as on, and Monday's leagues come from it.

### Or deploy from GitHub (optional)

*Actions → Deploy server → Run workflow* does the same from GitHub, with one secret: a Google Cloud service account key (JSON) saved as the repository secret `FIREBASE_SERVICE_ACCOUNT`. The account needs the roles Firebase Admin, Cloud Functions Admin, Cloud Scheduler Admin and Service Account User. Delete the downloaded key file once it's saved in GitHub.

Later changes: edit, push (the tests run by themselves), deploy again.
