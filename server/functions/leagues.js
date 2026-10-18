// Maplewick leagues, as the game computes them (app/maplewick.html, "11.08: leagues"), so the server's table is the one
// players see. Every week each league is cut into groups of 30 real players, in an order everyone can work out the same
// way; robot towns fill each group up to 30. A real player who joins takes a robot's place. At the end of the week the
// top 10 move up a league, the bottom 5 move down, and the top 3 win a trophy and a royal chest.
//
// Keep these in step with the game: tools/tests (npm test here) checks them against the game file.
'use strict';

const LEAGUES = ['Bronze', 'Silver', 'Gold', 'Sapphire', 'Ruby', 'Emerald', 'Amethyst', 'Pearl', 'Obsidian', 'Diamond'];
const LG_SIZE = 30, LG_UP = 10, LG_DOWN = 5;

const hash32 = (s) => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; };
const seeded = (n) => { let s = (n % 2147483646) + 1; return () => { s = (s * 16807) % 2147483647; return s / 2147483647; }; };
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

const LG_TOWN_A = ['Pine', 'Salt', 'Willow', 'Copper', 'Thorn', 'Amber', 'Moss', 'Oak', 'Maple', 'Birch', 'Elder', 'Fern', 'Heather', 'Juniper', 'Lark', 'Mill', 'North', 'Orchard', 'Pebble', 'Raven', 'Stone', 'Thistle', 'Wren', 'Clover', 'Hollow', 'Bramble', 'Cedar', 'Linden', 'Rush', 'Sorrel'];
const LG_TOWN_B = ['haven', 'marsh', 'by', 'brook', 'field', ' Bay', 'gate', 'ford', 'wick', 'stead', 'holm', 'dale', 'combe', 'ton', 'mere', 'well', 'bridge', 'cliff', 'port', 'vale'];
const LG_MAYOR = ['Rosa', 'Abe', 'Juno', 'Milo', 'Greta', 'Kai', 'Lou', 'Ines', 'Theo', 'Nora', 'Omar', 'Pia', 'Ravi', 'Sana', 'Tess', 'Ugo', 'Vera', 'Wim', 'Yara', 'Zane', 'Ada', 'Bo', 'Cleo', 'Dev', 'Elif', 'Finn', 'Gus', 'Hana', 'Ivo', 'Jas'];

// A robot town for week W, league t, group g, place j. Its week total grows with the league.
function lgRobot(W, t, g, j) {
  const rnd = seeded(hash32(`${W}|${t}|${g}|${j}`)), h0g = hash32(`${W}|${t}|${g}`);
  const town = LG_TOWN_A[(h0g + j * 7) % LG_TOWN_A.length] + LG_TOWN_B[Math.floor(rnd() * LG_TOWN_B.length)], mayor = LG_MAYOR[(h0g + j * 11) % LG_MAYOR.length]; rnd();
  const z = Math.sqrt(-2 * Math.log(Math.max(1e-9, rnd()))) * Math.cos(2 * Math.PI * rnd());
  const M = Math.max(5, Math.round(60 * Math.pow(1.33, t) * Math.exp(0.6 * z)));
  return { id: `lgbot:${W}:${t}:${g}:${j}`, bot: true, mayor, town, M };
}

const lgMove = (rank, n, t) => (rank <= LG_UP && t < LEAGUES.length - 1 ? 1 : rank > n - LG_DOWN && t > 0 ? -1 : 0);

// The final tables of one league for week W. players: [{ id, min, name, town }] (only those with minutes > 0).
// Returns [{ g, rows: [{ id, bot, min, name, town, rank, move }] }].
function leagueGroups(W, t, players) {
  const hum = players.filter((p) => p.min > 0).slice().sort((a, b) => hash32(a.id + '|' + W) - hash32(b.id + '|' + W));
  const groups = [];
  for (let g = 0; g * LG_SIZE < hum.length; g++) {
    const rows = hum.slice(g * LG_SIZE, g * LG_SIZE + LG_SIZE).map((p) => ({ id: p.id, bot: false, min: p.min, name: p.name || '', town: p.town || '' }));
    for (let j = 0; rows.length < LG_SIZE; j++) { const R = lgRobot(W, t, g, j); rows.push({ id: R.id, bot: true, min: R.M, name: R.mayor, town: R.town }); }
    rows.sort((a, b) => b.min - a.min || (a.bot ? 1 : 0) - (b.bot ? 1 : 0) || hash32(a.id) - hash32(b.id));
    rows.forEach((r, i) => { r.rank = i + 1; r.move = lgMove(r.rank, rows.length, t); });
    groups.push({ g, rows });
  }
  return groups;
}

// The ISO week key the game uses ("2026-W42"), for a time in a given IANA time zone.
function weekKey(t, timeZone) {
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date(t)).map((x) => [x.type, x.value]));
  const d = new Date(Date.UTC(+p.year, +p.month - 1, +p.day));
  d.setUTCDate(d.getUTCDate() + 3 - ((d.getUTCDay() + 6) % 7));
  const w1 = new Date(Date.UTC(d.getUTCFullYear(), 0, 4));
  return `${d.getUTCFullYear()}-W${1 + Math.round(((d - w1) / 86400000 - 3 + ((w1.getUTCDay() + 6) % 7)) / 7)}`;
}

const WEEK_RE = /^\d{4}-W\d{1,2}$/;

module.exports = { LEAGUES, LG_SIZE, LG_UP, LG_DOWN, hash32, seeded, clamp, lgRobot, lgMove, leagueGroups, weekKey, WEEK_RE };
