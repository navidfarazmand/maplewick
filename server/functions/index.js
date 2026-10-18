// Maplewick's server (version 12): focus minutes the server timed, and the weekly leagues worked out in one place.
//
//   focusStart / focusEnd   the game calls these when a focus session starts and ends. The server notes the start
//                           time itself, so a session can only count the minutes that really passed.
//   registerPush            the Android app's push token, so friends' messages can reach the phone.
//   friendNotify            when a player's board entry changes: a notification to each friend they just sent
//                           something (an invitation to focus together, a gift, a trade, a loan) or added.
//   bugReport               a problem report from the game (shake the phone): saved in reports/{id}, the id is
//                           shown to the player ("R-4F2K") so they can say which one.
//   weeklyLeagues           every Monday just after midnight (Toronto time): last week's tables from those minutes,
//                           robots filling every group up to 30, who moves up or down, and the top 3.
//
// Data (players can read only their own; nobody can write any of it except these functions):
//   focus/{uid}          { open: { sid, start, week, app } | null, weeks: { "2026-W42": { min, app, n } } }
//   leagueResults/{uid}  { t: league now, last: { w, t, g, rank, n, move, to, min, trophy } }
//   leagueTables/{id}    { w, t, g, rows: [{ id, bot, name, town, min, rank, move }] }   id = "2026-W42_3_0"
//   leagueWeeks/{w}      { done: true, players, groups, at }
//   push/{uid}           { tokens: [...] }   nobody but the server
//   config/server        { on: true, tz, appOnly }   readable by anyone: the game checks it to know the server is on
'use strict';

const { onCall, HttpsError } = require('firebase-functions/v2/https');
const { onSchedule } = require('firebase-functions/v2/scheduler');
const { setGlobalOptions } = require('firebase-functions/v2');
const { initializeApp } = require('firebase-admin/app');
const { getFirestore } = require('firebase-admin/firestore');
const { getMessaging } = require('firebase-admin/messaging');
const { onDocumentWritten } = require('firebase-functions/v2/firestore');
const L = require('./leagues');
const { TZ, focusStart, focusEnd, runWeek, registerPush, friendPushes, bugReport } = require('./core');

setGlobalOptions({ region: 'us-central1', maxInstances: 5 });
initializeApp();

const nowMs = () => Date.now();

// ---- Exported functions ----

const wrap = async (fn) => { try { return await fn(); } catch (e) { if (e && e.code === 'invalid-argument') throw new HttpsError('invalid-argument', e.message); throw e; } };
const signedIn = (req) => { if (!req.auth || !req.auth.uid) throw new HttpsError('unauthenticated', 'Sign in first'); return req.auth.uid; };

exports.focusEnd = onCall({ cors: true }, (req) => wrap(() => focusEnd(getFirestore(), signedIn(req), req.data, nowMs())));
exports.weeklyLeagues = onSchedule({ schedule: '10 0 * * 1', timeZone: TZ, retryCount: 3 }, async () => {
  const db = getFirestore(), now = nowMs();
  await db.collection('config').doc('server').set({ on: true, tz: TZ }, { merge: true });
  return runWeek(db, L.weekKey(now - 86400000, TZ), now);
});
// The game checks config/server to know the server is on: the first session after a deploy writes it.
// The game checks config/server to know the server is on: the first session after a deploy writes it.
const hello = { done: false };
exports.focusStart = onCall({ cors: true }, async (req) => {
  const db = getFirestore(), uid = signedIn(req), now = nowMs();
  const out = await wrap(() => focusStart(db, uid, req.data, now));
  if (!hello.done) { hello.done = true; db.collection('config').doc('server').set({ on: true, tz: TZ }, { merge: true }).catch(() => { hello.done = false; }); }
  return out;
});

// For the tests

exports.registerPush = onCall({ cors: true }, (req) => wrap(() => registerPush(getFirestore(), signedIn(req), req.data, nowMs())));

exports.friendNotify = onDocumentWritten('board/{uid}', async (event) => {
  const before = event.data && event.data.before && event.data.before.exists ? event.data.before.data() : null;
  const after = event.data && event.data.after && event.data.after.exists ? event.data.after.data() : null;
  const pushes = friendPushes(before, after, nowMs());
  if (!pushes.length) return;
  const db = getFirestore(), messaging = getMessaging();
  for (const p of pushes) {
    const ref = db.collection('push').doc(p.to), d = (await ref.get()).data();
    const tokens = (d && d.tokens) || []; if (!tokens.length) continue;
    const res = await messaging.sendEachForMulticast({ tokens, notification: { title: p.title, body: p.body }, data: { kind: p.kind, from: event.params.uid }, android: { priority: 'high', notification: { channelId: 'friends' } } });
    const dead = tokens.filter((t, i) => !res.responses[i].success && /registration-token-not-registered|invalid-argument|invalid-registration-token/.test(String(res.responses[i].error && res.responses[i].error.code)));
    if (dead.length) await ref.set({ tokens: tokens.filter((t) => !dead.includes(t)) }, { merge: true });
  }
});

exports.bugReport = onCall({ cors: true }, (req) => wrap(() => bugReport(getFirestore(), req.auth ? req.auth.uid : null, req.data, nowMs())));
