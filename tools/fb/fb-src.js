// The small Firebase helper the home-screen game loads (app/github-pages/fb.js). Build: npm install && npm run build.
// The game calls init(config) once and uses only what this returns. Firestore is the "lite" client (no live updates),
// which keeps the file small.
//
// 12.00 adds getDoc(path) and call(name, data) for the server (server/ in the repo).
import { initializeApp } from 'firebase/app';
import {
  getAuth, onAuthStateChanged, getRedirectResult, signInAnonymously, GoogleAuthProvider, linkWithRedirect, signInWithRedirect,
  linkWithPopup, signInWithPopup, signInWithCredential, linkWithCredential, signOut,
} from 'firebase/auth';
import { getFirestore, getDocs, getDoc as fsGetDoc, query, collection, limit, setDoc, doc, deleteDoc } from 'firebase/firestore/lite';

export function init(config) {
  const app = initializeApp(config), auth = getAuth(app), db = getFirestore(app);
  const me = (u) => (u ? { uid: u.uid, anon: u.isAnonymous, name: u.displayName || '', google: u.providerData.some((p) => p.providerId === 'google.com') } : null);
  // When a guest signs in to an account that already exists, their guest entry on the board goes away.
  const dropGuest = async (u) => { if (u && u.isAnonymous) try { await deleteDoc(doc(db, 'board', u.uid)); } catch (e) { /* gone already */ } };
  const popupBroken = (code) => ['auth/popup-blocked', 'auth/operation-not-supported-in-this-environment', 'auth/web-storage-unsupported', 'auth/cancelled-popup-request'].includes(code);
  const region = config.functionsRegion || 'us-central1';
  return {
    onUser(fn) { return onAuthStateChanged(auth, (u) => fn(me(u))); },
    current() { return me(auth.currentUser); },
    async redirectResult() {
      try { return (await getRedirectResult(auth)) ? 'ok' : null; } catch (e) {
        if (e && (e.code === 'auth/credential-already-in-use' || e.code === 'auth/email-already-in-use')) { const c = GoogleAuthProvider.credentialFromError(e); if (c) { await signInWithCredential(auth, c); return 'switched'; } }
        return e && e.code ? e.code : 'error';
      }
    },
    async joinAnon() { await signInAnonymously(auth); return me(auth.currentUser); },
    async google(redirect) {
      const p = new GoogleAuthProvider(); p.setCustomParameters({ prompt: 'select_account' });
      const u = auth.currentUser;
      if (redirect) { if (u && u.isAnonymous) await linkWithRedirect(u, p); else await signInWithRedirect(auth, p); return 'redirect'; }
      try { if (u && u.isAnonymous) await linkWithPopup(u, p); else await signInWithPopup(auth, p); return 'ok'; } catch (e) {
        const code = e && e.code;
        if (code === 'auth/credential-already-in-use' || code === 'auth/email-already-in-use') { const c = GoogleAuthProvider.credentialFromError(e); if (c) { await dropGuest(u); await signInWithCredential(auth, c); return 'switched'; } }
        if (popupBroken(code)) { await signInWithRedirect(auth, p); return 'redirect'; }
        if (code === 'auth/popup-closed-by-user') return 'closed';
        throw e;
      }
    },
    async googleIdToken(token) {
      const c = GoogleAuthProvider.credential(token), u = auth.currentUser;
      try { if (u && u.isAnonymous) await linkWithCredential(u, c); else await signInWithCredential(auth, c); return 'ok'; } catch (e) {
        if (e && (e.code === 'auth/credential-already-in-use' || e.code === 'auth/email-already-in-use')) { await dropGuest(u); await signInWithCredential(auth, GoogleAuthProvider.credentialFromError(e) || c); return 'switched'; }
        throw e;
      }
    },
    async signOut() { await signOut(auth); },
    async list() { return (await getDocs(query(collection(db, 'board'), limit(300)))).docs.map((d) => Object.assign({}, d.data(), { id: d.id })); },
    async put(id, data) { await setDoc(doc(db, 'board', id), data); },
    async merge(id, data) { await setDoc(doc(db, 'board', id), data, { merge: true }); },
    async remove(id) { await deleteDoc(doc(db, 'board', id)); },
    // 12.00: one document by path ("config/server", "leagueResults/<uid>"); null when it isn't there
    async getDoc(path) { const s = await fsGetDoc(doc(db, path)); return s.exists() ? s.data() : null; },
    // 12.00: a server function (an https callable). Resolves to its result; rejects with { code } when it fails.
    async call(name, data) {
      const u = auth.currentUser; if (!u) throw { code: 'unauthenticated' };
      const tok = await u.getIdToken();
      const res = await fetch(`https://${region}-${config.projectId}.cloudfunctions.net/${name}`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + tok }, body: JSON.stringify({ data: data || {} }) });
      let body = null; try { body = await res.json(); } catch (e) { /* not json */ }
      if (!res.ok || !body || body.error) throw { code: (body && body.error && body.error.status) || 'http-' + res.status };
      return body.result;
    },
  };
}
