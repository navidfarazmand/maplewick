/**
 * The script the app puts into the game page before it loads. It gives the page `window.MaplewickApp`:
 *
 *   post(msg)   page → app (focus started or ended, leaving the app, Google sign-in, …)
 *   on(fn)      the game's handler for app → page messages (queued until the game is ready)
 *   recv(msg)   called by the app to deliver a message
 *
 * It also stands in for the browser's Notification API (which Android's WebView lacks), so the game's existing
 * "Allow notifications" button and its notifications work, and it makes sure the page knows when the app is in the
 * back (document.hidden), which the game uses for time away.
 */
export type BridgeInfo = {
  appVersion: string;
  notifPermission: 'granted' | 'denied' | 'default';
};

export function bridgeScript(info: BridgeInfo): string {
  return `(function () {
  if (window.MaplewickApp) return;
  var queue = [], handler = null, permWaiters = [];
  var A = window.MaplewickApp = {
    platform: 'android',
    appVersion: ${JSON.stringify(info.appVersion)},
    post: function (m) { try { window.ReactNativeWebView.postMessage(JSON.stringify(m)); } catch (e) {} },
    on: function (fn) { handler = fn; var q = queue; queue = []; for (var i = 0; i < q.length; i++) { try { fn(q[i]); } catch (e) {} } },
    recv: function (m) {
      if (m && m.t === 'perm') { N.permission = m.perm; var w = permWaiters; permWaiters = []; for (var i = 0; i < w.length; i++) w[i](m.perm); return; }
      if (m && m.t === 'visible') { A.setHidden(!m.on); return; }
      if (handler) { try { handler(m); } catch (e) {} } else queue.push(m);
    },
    // The app tells the page when it goes to the back or comes to the front. If the WebView didn't already change
    // document.hidden, this does it and fires the visibilitychange event the game listens for.
    _fake: null,
    _dark: null,
    _seq: 0,
    setHidden: function (h) {
      // Only the latest call counts: a late "hidden" (its timer is longer) must not win over "back in front".
      var seq = ++A._seq;
      setTimeout(function () {
        if (seq !== A._seq) return;
        if (A._fake === null && document.hidden === h) return;
        if (A._fake === h) return;
        A._fake = h;
        try {
          Object.defineProperty(document, 'hidden', { configurable: true, get: function () { return A._fake; } });
          Object.defineProperty(document, 'visibilityState', { configurable: true, get: function () { return A._fake ? 'hidden' : 'visible'; } });
        } catch (e) {}
        try { document.dispatchEvent(new Event('visibilitychange')); } catch (e) {}
      }, h ? 600 : 300);
    }
  };
  // A tap means the app is in front: if the page still thinks it's hidden, wake it up.
  document.addEventListener('pointerdown', function () { if (A._fake === true) A.setHidden(false); }, true);
  // The status bar icons follow the game's theme (its own setting, or the phone's).
  function theme() {
    var t = document.documentElement.getAttribute('data-theme');
    var dark = t === 'dark' || (t !== 'light' && !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches));
    if (dark !== A._dark) { A._dark = dark; A.post({ t: 'theme', dark: dark }); }
  }
  try {
    new MutationObserver(theme).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    if (window.matchMedia) window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', theme);
    document.addEventListener('DOMContentLoaded', theme);
  } catch (e) {}
  // Notifications: shown by the app.
  function N(title, opts) { A.post({ t: 'notify', title: String(title || ''), body: String((opts && opts.body) || ''), tag: String((opts && opts.tag) || '') }); }
  N.permission = ${JSON.stringify(info.notifPermission)};
  N.requestPermission = function (cb) {
    return new Promise(function (res) {
      permWaiters.push(function (p) { res(p); if (typeof cb === 'function') cb(p); });
      A.post({ t: 'notif?' });
    });
  };
  N.prototype.close = function () {};
  try { window.Notification = N; } catch (e) {}
  try {
    if (window.ServiceWorkerRegistration) ServiceWorkerRegistration.prototype.showNotification = function (title, opts) { N(title, opts); return Promise.resolve(); };
  } catch (e) {}
})();
true;`;
}
