// A tiny in-memory stand-in for the parts of Firestore the server uses.
'use strict';
const merge = (a, b) => { const o = Object.assign({}, a); for (const [k, v] of Object.entries(b)) o[k] = v; return o; };
function fakeDb(init) {
  const data = new Map(); // "col/id" -> object
  for (const [k, v] of Object.entries(init || {})) data.set(k, JSON.parse(JSON.stringify(v)));
  const snap = (key) => ({ id: key.split('/')[1], exists: data.has(key), data: () => (data.has(key) ? JSON.parse(JSON.stringify(data.get(key))) : undefined) });
  const write = (key, v, opts) => data.set(key, JSON.parse(JSON.stringify(opts && opts.merge && data.has(key) ? merge(data.get(key), v) : v)));
  const doc = (col, id) => ({ _key: `${col}/${id}`, get: async () => snap(`${col}/${id}`), set: async (v, o) => write(`${col}/${id}`, v, o) });
  return {
    data,
    collection: (col) => ({
      doc: (id) => doc(col, id),
      get: async () => ({ docs: [...data.keys()].filter((k) => k.startsWith(col + '/')).map(snap) }),
    }),
    runTransaction: async (fn) => fn({ get: (ref) => ref.get(), set: (ref, v, o) => write(ref._key, v, o) }),
    batch: () => { const ops = []; return { set: (ref, v, o) => ops.push([ref._key, v, o]), commit: async () => { for (const [k, v, o] of ops) write(k, v, o); } }; },
  };
}
module.exports = { fakeDb };
