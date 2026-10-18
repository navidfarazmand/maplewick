// The server's league maths must match the game's exactly, or players would see a different table than the server
// decides. This loads the functions from the game file itself and compares.
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const L = require('../leagues');

const GAME = path.join(__dirname, '..', '..', '..', 'app', 'maplewick.html');
function fromGame() {
  const src = fs.readFileSync(GAME, 'utf8');
  const grab = (re) => { const m = src.match(re); if (!m) throw new Error('not found in the game: ' + re); return m[0]; };
  const parts = [
    grab(/const LG_SIZE = 30[^\n]*\n/), grab(/  const hash32 = [^\n]*\n/), grab(/  const seeded = [^\n]*\n/),
    grab(/  const LG_TOWN_A = [^\n]*\n/), grab(/  const LG_TOWN_B = [^\n]*\n/), grab(/  const LG_MAYOR = [^\n]*\n/),
    grab(/  function lgRobot\(W, t, g, j\) \{[\s\S]*?\n  \}\n/), grab(/  const lgMove = [^\n]*\n/),
  ].join('').replace('BOOT_AT = Date.now()', 'BOOT_AT = 0');
  const LEAGUES = L.LEAGUES.map((name) => ({ name }));
  // eslint-disable-next-line no-new-func
  return new Function('LEAGUES', 'clamp', 'hash32x', parts + '\nreturn { hash32, seeded, lgRobot, lgMove, LG_SIZE, LG_UP, LG_DOWN };')(LEAGUES, L.clamp);
}

test('the league maths match the game file', () => {
  const G = fromGame();
  assert.strictEqual(G.LG_SIZE, L.LG_SIZE); assert.strictEqual(G.LG_UP, L.LG_UP); assert.strictEqual(G.LG_DOWN, L.LG_DOWN);
  for (const s of ['', 'abc', 'u1|2026-W42', 'lgbot:2026-W42:3:0:5']) assert.strictEqual(L.hash32(s), G.hash32(s));
  for (const W of ['2026-W42', '2026-W43', '2027-W01']) for (let t = 0; t < 10; t++) for (const g of [0, 1, 4]) for (let j = 0; j < 30; j++) {
    const a = L.lgRobot(W, t, g, j), b = G.lgRobot(W, t, g, j);
    assert.deepStrictEqual([a.id, a.mayor, a.town, a.M], [b.id, b.mayor, b.town, b.M]);
  }
  for (let t = 0; t < 10; t++) for (let r = 1; r <= 30; r++) assert.strictEqual(L.lgMove(r, 30, t), G.lgMove(r, 30, t));
});
