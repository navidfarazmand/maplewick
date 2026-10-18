// Runs inside the Firebase emulators (npm run test:emulator, and on GitHub: .github/workflows/server.yml):
// the security rules, the two session functions over HTTP, and a week of leagues on a real (emulated) Firestore.
import test, { before, after } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import { createRequire } from 'node:module';
import { initializeTestEnvironment, assertFails, assertSucceeds } from '@firebase/rules-unit-testing';
import { doc, getDoc, setDoc } from 'firebase/firestore';

const require = createRequire(import.meta.url);
const PROJECT = 'demo-maplewick';
const [fsHost, fsPort] = (process.env.FIRESTORE_EMULATOR_HOST || '127.0.0.1:8080').split(':');
const FN = `http://${process.env.FUNCTIONS_EMULATOR_HOST || '127.0.0.1:5001'}/${PROJECT}/us-central1`;
const AUTH = `http://${process.env.FIREBASE_AUTH_EMULATOR_HOST || '127.0.0.1:9099'}`;
let env;

before(async () => {
  env = await initializeTestEnvironment({ projectId: PROJECT, firestore: { host: fsHost, port: +fsPort, rules: fs.readFileSync(new URL('../firestore.rules', import.meta.url), 'utf8') } });
});
after(async () => { if (env) await env.cleanup(); });

test('rules: the server-only collections can be read by their owner and written by nobody', async () => {
  await env.withSecurityRulesDisabled(async (c) => {
    const db = c.firestore();
    await setDoc(doc(db, 'focus/alice'), { weeks: {} });
    await setDoc(doc(db, 'leagueResults/alice'), { t: 1 });
    await setDoc(doc(db, 'leagueTables/2026-W42_0_0'), { rows: [] });
    await setDoc(doc(db, 'config/server'), { on: true });
  });
  const alice = env.authenticatedContext('alice').firestore(), bob = env.authenticatedContext('bob').firestore(), anon = env.unauthenticatedContext().firestore();
  await assertSucceeds(getDoc(doc(alice, 'focus/alice')));
  await assertFails(getDoc(doc(bob, 'focus/alice')));
  await assertFails(setDoc(doc(alice, 'focus/alice'), { weeks: { x: { min: 9999 } } }));
  await assertSucceeds(getDoc(doc(alice, 'leagueResults/alice')));
  await assertFails(getDoc(doc(bob, 'leagueResults/alice')));
  await assertFails(setDoc(doc(alice, 'leagueResults/alice'), { t: 9 }));
  await assertSucceeds(getDoc(doc(bob, 'leagueTables/2026-W42_0_0')));
  await assertFails(getDoc(doc(anon, 'leagueTables/2026-W42_0_0')));
  await assertSucceeds(getDoc(doc(anon, 'config/server')));
  await assertFails(setDoc(doc(alice, 'config/server'), { on: false }));
  await assertFails(getDoc(doc(alice, 'push/alice')));
  await assertFails(setDoc(doc(alice, 'push/alice'), { tokens: ['x'] }));
});

test('rules: the board works as before', async () => {
  const alice = env.authenticatedContext('alice').firestore();
  const entry = { v: 1, name: 'Alice', town: 'Oakby', builder: 'Sam', level: 3, residents: 9, mood: 70, streak: 2, week: '2026-W42', weekMin: 90, day: '2026-10-18', dayMin: 30, total: 400, badges: 2, hall: 2, land: 1, bs: '', staff: {}, cheers: {}, updatedAt: 1 };
  await assertSucceeds(setDoc(doc(alice, 'board/alice'), entry));
  await assertFails(setDoc(doc(alice, 'board/bob'), entry));
  await assertFails(setDoc(doc(alice, 'board/alice'), Object.assign({}, entry, { weekMin: 99999 })));
});

async function signUp() {
  const r = await fetch(`${AUTH}/identitytoolkit.googleapis.com/v1/accounts:signUp?key=fake`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ returnSecureToken: true }) });
  const j = await r.json(); return { token: j.idToken, uid: j.localId };
}
async function call(name, data, token) {
  const r = await fetch(`${FN}/${name}`, { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, token ? { Authorization: 'Bearer ' + token } : {}), body: JSON.stringify({ data }) });
  return { status: r.status, body: await r.json() };
}

test('functions: a session is timed by the server', async () => {
  const { token, uid } = await signUp();
  const s = await call('focusStart', { sid: 'abc', app: true }, token);
  assert.strictEqual(s.status, 200, JSON.stringify(s.body)); assert.strictEqual(s.body.result.ok, true);
  const e = await call('focusEnd', { sid: 'abc', minutes: 25 }, token); // claims 25 minutes a second after starting
  assert.strictEqual(e.status, 200); assert.ok(e.body.result.credited < 1, 'credited ' + e.body.result.credited);
  const no = await call('focusStart', { sid: 'x' });
  assert.strictEqual(no.status, 401);
  const bad = await call('focusEnd', { sid: 'abc', minutes: -5 }, token);
  assert.strictEqual(bad.status, 400);
  let f;
  await env.withSecurityRulesDisabled(async (c) => { f = (await getDoc(doc(c.firestore(), 'focus/' + uid))).data(); });
  assert.strictEqual(f.open, null);
  const w = Object.values(f.weeks)[0]; assert.strictEqual(w.n, 1); assert.ok(w.app > 0);
});

test('a week of leagues on the emulated Firestore', async () => {
  process.env.GCLOUD_PROJECT = PROJECT;
  const { initializeApp, getApps } = require('firebase-admin/app');
  const { getFirestore } = require('firebase-admin/firestore');
  if (!getApps().length) initializeApp({ projectId: PROJECT });
  const db = getFirestore();
  const { runWeek } = require('../functions/core.js');
  const W = '2030-W10';
  for (let i = 0; i < 35; i++) await db.collection('focus').doc('p' + i).set({ weeks: { [W]: { min: 10 + i * 7, app: 0, n: 1 } } });
  const out = await runWeek(db, W, Date.now());
  assert.deepStrictEqual(out, { players: 35, groups: 2 });
  const t0 = (await db.collection('leagueTables').doc(`${W}_0_0`).get()).data();
  const t1 = (await db.collection('leagueTables').doc(`${W}_0_1`).get()).data();
  assert.strictEqual(t0.rows.length, 30); assert.strictEqual(t1.rows.length, 30);
  assert.strictEqual(t0.rows.filter((r) => !r.bot).length + t1.rows.filter((r) => !r.bot).length, 35);
  assert.deepStrictEqual(await runWeek(db, W, Date.now()), { skipped: true });
});
