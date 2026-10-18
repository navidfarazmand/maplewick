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


// ---- Friends: a notification when a friend sends you something (roadmap part 8) ----

// Push tokens for a player's phones (the Android app sends its token once notifications are allowed).
async function registerPush(db, uid, data, now) {
  const token = String((data && data.token) || '');
  if (!token || token.length > 400) throw bad('token');
  const ref = db.collection('push').doc(uid), d = (await ref.get()).data() || {};
  const tokens = (d.tokens || []).filter((x) => x !== token).concat([token]).slice(-5);
  await ref.set({ tokens, platform: String((data && data.platform) || '').slice(0, 12), updatedAt: now });
  return { ok: true };
}

const MSG_FRESH = 30 * 60000; // only messages written in the last half hour (not old ones found on a resave)
// What a friend should hear about, from one player's board entry before and after a save:
// [{ to, title, body, kind }]. New messages in their outbox, and new names on their friends list.
function friendPushes(before, after, now) {
  if (!after) return [];
  const xa = boardExtra(after.bs), xb = before ? boardExtra(before.bs) : {};
  const name = String(after.name || 'A friend').slice(0, 20);
  const seen = new Set((Array.isArray(xb.ob) ? xb.ob : []).map((m) => m && m.i));
  const out = [];
  for (const m of Array.isArray(xa.ob) ? xa.ob : []) {
    if (!m || !m.to || seen.has(m.i) || !(now - (m.at || 0) < MSG_FRESH)) continue;
    const to = String(m.to);
    if (m.k === 'inv') out.push({ to, kind: 'inv', title: `${name} invites you to focus together`, body: `${m.len | 0} minutes. Open Maplewick within 20 minutes to join.` });
    else if (m.k === 'gift') out.push({ to, kind: 'gift', title: `${name} sent you a gift`, body: m.f ? `${m.f | 0} food for your town.` : 'A decoration for your town.' });
    else if (m.k === 'offer') out.push({ to, kind: 'offer', title: `${name} offers a trade`, body: 'Open Maplewick to see it. Offers last two days.' });
    else if (m.k === 'lreq') out.push({ to, kind: 'lreq', title: `${name} asks to borrow gold`, body: `${m.g | 0} gold. Open Maplewick to answer.` });
    else if (m.k === 'lgive') out.push({ to, kind: 'lgive', title: `${name} lent you gold`, body: `${m.g | 0} gold is in your treasury.` });
    else if (m.k === 'acc') out.push({ to, kind: 'acc', title: `${name} took your trade`, body: 'Open Maplewick to see what you got.' });
  }
  const fb = new Set(Array.isArray(xb.fr) ? xb.fr : []);
  if (before) for (const f of Array.isArray(xa.fr) ? xa.fr : []) if (!fb.has(f)) out.push({ to: String(f), kind: 'friend', title: `${name} added you as a friend`, body: 'Add them back in Friends to focus together, trade and send gifts.' });
  return out.slice(0, 10);
}

// ---- Bug reports (shake the phone, or Menu → Report a problem) ----

const REPORT_MAX = 700000; // characters of JSON; a Firestore document holds at most about 1 MB
const CODE = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
const reportId = () => 'R-' + Array.from({ length: 4 }, () => CODE[Math.floor(Math.random() * CODE.length)]).join('');
async function bugReport(db, uid, data, now) {
  if (!data || typeof data !== 'object') throw bad('report');
  const r = Object.assign({}, data);
  if (typeof r.shot !== 'string' || !/^data:image\/(jpeg|png|webp);base64,/.test(r.shot) || r.shot.length > 400000) delete r.shot;
  let json = JSON.stringify(r);
  if (json.length > REPORT_MAX) { delete r.shot; json = JSON.stringify(r); }
  if (json.length > REPORT_MAX) throw bad('report too big');
  for (let i = 0; i < 5; i++) {
    const id = reportId(), ref = db.collection('reports').doc(id);
    if ((await ref.get()).exists) continue;
    await ref.set(Object.assign({ at: now, iso: new Date(now).toISOString(), uid: uid || null }, JSON.parse(json)));
    return { id };
  }
  throw bad('no id');
}

module.exports = { TZ, focusStart, focusEnd, runWeek, boardExtra, tierFor, registerPush, friendPushes, bugReport };
