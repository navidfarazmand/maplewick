// The server's rules, without Firebase itself, so the tests can run them on a stand-in database. index.js wires them up.
'use strict';

const L = require('./leagues');
const bad = (msg) => Object.assign(new Error(msg), { code: 'invalid-argument' });

const TZ = 'America/Toronto';
const MAX_SESSION_MIN = 300; // the longest session the game allows is 4 hours; a little room on top
const KEEP_WEEKS = 8;


// ---- Focus sessions, timed by the server ----

async function focusStart(db, uid, data, now) {
  const sid = String((data && data.sid) || '').slice(0, 40);
  if (!sid) throw bad('sid');
  const ref = db.collection('focus').doc(uid);
  const open = { sid, start: now, week: L.weekKey(now, TZ), app: !!(data && data.app) };
  await ref.set({ open, updatedAt: now }, { merge: true });
  return { ok: true, week: open.week };
}

async function focusEnd(db, uid, data, now) {
  const sid = String((data && data.sid) || '').slice(0, 40);
  const minutes = Number(data && data.minutes);
  if (!sid || !(minutes >= 0)) throw bad('sid, minutes');
  const ref = db.collection('focus').doc(uid);
  return db.runTransaction(async (tx) => {
    const snap = await tx.get(ref), d = snap.exists ? snap.data() : {};
    const open = d.open;
    if (!open || open.sid !== sid) return { ok: false, credited: 0 }; // not a session the server saw start
    const elapsed = Math.max(0, (now - open.start) / 60000);
    const credited = Math.round(L.clamp(Math.min(minutes, elapsed + 0.5), 0, MAX_SESSION_MIN) * 100) / 100;
    const weeks = Object.assign({}, d.weeks || {});
    const w = Object.assign({ min: 0, app: 0, n: 0 }, weeks[open.week]);
    w.min = Math.round((w.min + credited) * 100) / 100;
    if (open.app) w.app = Math.round((w.app + credited) * 100) / 100;
    if (credited > 0) w.n += 1;
    weeks[open.week] = w;
    for (const k of Object.keys(weeks).sort().slice(0, -KEEP_WEEKS)) delete weeks[k];
    tx.set(ref, { open: null, weeks, updatedAt: now }, { merge: true });
    return { ok: true, credited, week: open.week, weekMin: w.min };
  });
}

// ---- The weekly leagues ----

// The league data each player's game puts in the board's layout string ("~" + JSON before the first ";").
function boardExtra(bs) {
  const s = String(bs || ''); if (s[0] !== '~') return {};
  try { const end = s.indexOf(';'); const x = JSON.parse(decodeURIComponent(s.slice(1, end >= 0 ? end : s.length))); return x && typeof x === 'object' ? x : {}; } catch (e) { return {}; }
}
// The league a player was in for week W: what the server last decided, else (the first time) what their game says.
function tierFor(W, res, board) {
  if (res && Number.isInteger(res.t)) return L.clamp(res.t, 0, L.LEAGUES.length - 1);
  const lg = board ? boardExtra(board.bs).lg : null;
  if (lg && lg.w === W && Number.isInteger(lg.t)) return L.clamp(lg.t, 0, L.LEAGUES.length - 1);
  if (lg && lg.pw === W && Number.isInteger(lg.pt)) return L.clamp(lg.pt, 0, L.LEAGUES.length - 1);
  return 0;
}

async function runWeek(db, W, now) {
  const weekRef = db.collection('leagueWeeks').doc(W);
  if ((await weekRef.get()).exists) return { skipped: true };
  const cfg = (await db.collection('config').doc('server').get()).data() || {};
  const [focusSnap, resSnap, boardSnap] = await Promise.all([db.collection('focus').get(), db.collection('leagueResults').get(), db.collection('board').get()]);
  const res = new Map(resSnap.docs.map((d) => [d.id, d.data()]));
  const board = new Map(boardSnap.docs.map((d) => [d.id, d.data()]));
  const byTier = new Map();
  for (const f of focusSnap.docs) {
    const wk = (f.data().weeks || {})[W]; if (!wk) continue;
    const min = Math.round(cfg.appOnly ? wk.app || 0 : wk.min || 0);
    if (min <= 0) continue;
    const r = res.get(f.id); if (r && r.last && r.last.w === W) continue; // already counted
    const b = board.get(f.id) || {}, t = tierFor(W, r, b);
    if (!byTier.has(t)) byTier.set(t, []);
    byTier.get(t).push({ id: f.id, min, name: String(b.name || 'A mayor').slice(0, 20), town: String(b.town || '').slice(0, 24) });
  }
  let players = 0, groups = 0, batch = db.batch(), ops = 0;
  const put = async (ref, data) => { batch.set(ref, data, { merge: true }); if (++ops >= 400) { await batch.commit(); batch = db.batch(); ops = 0; } };
  for (const [t, list] of byTier) {
    for (const G of L.leagueGroups(W, t, list)) {
      groups++;
      await put(db.collection('leagueTables').doc(`${W}_${t}_${G.g}`), { w: W, t, g: G.g, rows: G.rows, at: now });
      for (const r of G.rows) {
        if (r.bot) continue;
        players++;
        const to = L.clamp(t + r.move, 0, L.LEAGUES.length - 1);
        await put(db.collection('leagueResults').doc(r.id), { t: to, last: { w: W, t, g: G.g, rank: r.rank, n: G.rows.length, move: r.move, to, min: r.min, trophy: r.rank <= 3 }, at: now });
      }
    }
  }
  await put(weekRef, { done: true, players, groups, at: now });
  if (ops) await batch.commit();
  return { players, groups };
}

module.exports = { TZ, focusStart, focusEnd, runWeek, boardExtra, tierFor };
