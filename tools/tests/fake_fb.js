// A stand-in for fb.js (the Firebase helper) in tests: a signed-in player, a board in memory, and a server that
// records calls. Tests set window.__docs[path] for getDoc and read window.__calls.
export function init() {
  window.__calls = window.__calls || []; window.__docs = window.__docs || {}; window.__board = window.__board || {};
  const user = { uid: 'u1', anon: false, name: 'Navid', google: true };
  return {
    onUser(fn) { setTimeout(() => fn(user), 50); return () => {}; },
    current() { return user; },
    async redirectResult() { return null; },
    async joinAnon() { return user; }, async google() { return 'ok'; }, async googleIdToken() { return 'ok'; }, async signOut() {},
    async list() { return Object.entries(window.__board).map(([id, d]) => Object.assign({}, d, { id })); },
    async put(id, d) { window.__board[id] = d; }, async merge(id, d) { window.__board[id] = Object.assign({}, window.__board[id], d); }, async remove(id) { delete window.__board[id]; },
    async getDoc(path) { return window.__docs[path] || null; },
    async call(name, data) { window.__calls.push({ name, data }); if (window.__srvDown) throw { code: 'http-404' }; return { ok: true }; },
  };
}
