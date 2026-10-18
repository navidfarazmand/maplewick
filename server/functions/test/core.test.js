'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { fakeDb } = require('./fake-db');
const { focusStart, focusEnd, runWeek, TZ } = require('../core');
const L = require('../leagues');

const T0 = Date.UTC(2026, 9, 14, 15, 0); // Wednesday 14 Oct 2026, 11:00 in Toronto
const W = L.weekKey(T0, TZ);

test('week keys match the game', () => {
  assert.strictEqual(W, '2026-W42');
  assert.strictEqual(L.weekKey(Date.UTC(2026, 9, 19, 3, 59), TZ), '2026-W42'); // Sunday 23:59 in Toronto
  assert.strictEqual(L.weekKey(Date.UTC(2026, 9, 19, 4, 1), TZ), '2026-W43');  // Monday 00:01 in Toronto
  assert.strictEqual(L.weekKey(Date.UTC(2027, 0, 1, 17), TZ), '2026-W53');
});

test('a session counts only the minutes that really passed', async () => {
  const db = fakeDb();
  await focusStart(db, 'u1', { sid: 's1', app: true }, T0);
  const r = await focusEnd(db, 'u1', { sid: 's1', minutes: 50 }, T0 + 25 * 60000); // claims 50, only 25 passed
  assert.strictEqual(r.credited, 25.5);
  const f = db.data.get('focus/u1');
  assert.strictEqual(f.open, null);
  assert.deepStrictEqual(f.weeks[W], { min: 25.5, app: 25.5, n: 1 });
});

test('an honest session counts in full, and sessions add up', async () => {
  const db = fakeDb();
  await focusStart(db, 'u1', { sid: 'a' }, T0);
  await focusEnd(db, 'u1', { sid: 'a', minutes: 25 }, T0 + 26 * 60000);
  await focusStart(db, 'u1', { sid: 'b' }, T0 + 30 * 60000);
  await focusEnd(db, 'u1', { sid: 'b', minutes: 10 }, T0 + 41 * 60000);
  assert.deepStrictEqual(db.data.get('focus/u1').weeks[W], { min: 35, app: 0, n: 2 });
});

test('an end the server never saw start counts nothing', async () => {
  const db = fakeDb();
  const r = await focusEnd(db, 'u1', { sid: 'x', minutes: 240 }, T0);
  assert.strictEqual(r.ok, false);
  await focusStart(db, 'u1', { sid: 'a' }, T0);
  const r2 = await focusEnd(db, 'u1', { sid: 'other', minutes: 30 }, T0 + 60 * 60000);
  assert.strictEqual(r2.credited, 0);
});

test('bad input is refused', async () => {
  const db = fakeDb();
  await assert.rejects(focusStart(db, 'u1', {}, T0), /sid/);
  await assert.rejects(focusEnd(db, 'u1', { sid: 'a', minutes: -1 }, T0), /minutes/);
});

test('the weekly leagues: robots fill the group, top 10 up, top 3 win, a real player takes a robot\'s place', async () => {
  const init = {};
  // three real players in Bronze with server-timed minutes; one more who didn't focus
  init['focus/a'] = { weeks: { [W]: { min: 2000, app: 0, n: 40 } } };
  init['focus/b'] = { weeks: { [W]: { min: 30, app: 30, n: 1 } } };
  init['focus/c'] = { weeks: { [W]: { min: 0.4, app: 0, n: 1 } } }; // rounds to 0: sat it out
  init['focus/d'] = { weeks: {} };
  init['board/a'] = { name: 'Ana', town: 'Oakby', bs: '' };
  init['board/b'] = { name: 'Ben', town: 'Elmwick', bs: '~' + encodeURIComponent(JSON.stringify({ lg: { w: W, t: 2, m: 30 } })) + ';' };
  const db = fakeDb(init);
  const out = await runWeek(db, W, T0 + 6 * 86400000);
  assert.deepStrictEqual(out, { players: 2, groups: 2 }); // Bronze and Gold (Ben's game said Gold the first time)
  const tb = db.data.get(`leagueTables/${W}_0_0`);
  assert.strictEqual(tb.rows.length, 30);
  assert.strictEqual(tb.rows.filter((r) => !r.bot).length, 1);
  const a = db.data.get('leagueResults/a');
  assert.strictEqual(a.last.rank, 1); assert.strictEqual(a.last.move, 1); assert.strictEqual(a.t, 1); assert.strictEqual(a.last.trophy, true);
  const b = db.data.get('leagueResults/b');
  assert.strictEqual(b.last.t, 2); assert.strictEqual(b.last.n, 30);
  assert.ok(!db.data.has('leagueResults/c') && !db.data.has('leagueResults/d'));
  // running the same week again changes nothing
  assert.deepStrictEqual(await runWeek(db, W, T0 + 7 * 86400000), { skipped: true });
  // the next week, the server's league counts, not the game's
  const W2 = L.weekKey(T0 + 7 * 86400000, TZ);
  db.data.set('focus/a', { weeks: { [W2]: { min: 10, app: 0, n: 1 } } });
  await runWeek(db, W2, T0 + 13 * 86400000);
  assert.strictEqual(db.data.get('leagueResults/a').last.t, 1);
});

test('app-only leagues count only minutes focused in the phone app', async () => {
  const db = fakeDb({ 'config/server': { on: true, appOnly: true }, 'focus/a': { weeks: { [W]: { min: 100, app: 0, n: 2 } } }, 'focus/b': { weeks: { [W]: { min: 100, app: 60, n: 2 } } } });
  const out = await runWeek(db, W, T0);
  assert.strictEqual(out.players, 1);
  assert.strictEqual(db.data.get('leagueResults/b').last.min, 60);
});

test('31 real players make two groups, each filled to 30 with robots', () => {
  const ps = Array.from({ length: 31 }, (_, i) => ({ id: 'p' + i, min: 10 + i }));
  const gs = L.leagueGroups(W, 3, ps);
  assert.strictEqual(gs.length, 2);
  assert.deepStrictEqual(gs.map((g) => g.rows.length), [30, 30]);
  assert.deepStrictEqual(gs.map((g) => g.rows.filter((r) => !r.bot).length), [30, 1]);
});
