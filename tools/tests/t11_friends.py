# 11.10: focusing with friends (roadmap part 8), with two players in two browsers and a fake board server that
# enforces the real firestore.rules (only the listed fields, layout string up to 12,000 characters).
import json, time, os, pathlib
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('MAPLEWICK_URL', (HERE.parent.parent / 'app' / 'maplewick.html').as_uri())
SH = str(HERE / 'shots') + '/'; os.makedirs(SH, exist_ok=True)
def D(pg, e): return pg.evaluate(f"() => window.MaplewickDebug.{e}")
fails = []
def ok(c, m):
    print(('ok   ' if c else 'FAIL ') + m)
    if not c: fails.append(m)
KEYS = {'v', 'name', 'town', 'builder', 'level', 'residents', 'mood', 'streak', 'week', 'weekMin', 'day', 'dayMin', 'total', 'badges', 'hall', 'land', 'bs', 'staff', 'cheers', 'updatedAt'}
DB, REJECT = {}, []
def valid(d):
    if not set(d) <= KEYS: return 'keys ' + str(set(d) - KEYS)
    if not isinstance(d.get('bs'), str) or len(d['bs']) > 12000: return 'bs'
    if not isinstance(d.get('weekMin'), int) or not isinstance(d.get('level'), int) or not isinstance(d.get('total'), int): return 'ints'
    if len(d.get('name', '')) > 24 or len(d.get('town', '')) > 24: return 'names'
    return None
FAKE = """
const B = 'https://fakefb.test';
export function init(cfg) {
  let user = null; const subs = []; try { user = JSON.parse(localStorage.getItem('fake-user') || 'null'); } catch (e) {}
  const emit = () => subs.forEach((f) => f(user));
  const post = async (p, d) => { const r = await fetch(B + p, { method: 'POST', body: JSON.stringify(d || {}) }); if (!r.ok) { const e = new Error('denied'); e.code = 'permission-denied'; throw e; } };
  return {
    onUser(fn) { subs.push(fn); setTimeout(() => fn(user), 0); return () => {}; }, current() { return user; },
    async redirectResult() { return null; },
    async joinAnon() { user = { uid: localStorage.getItem('fake-uid'), anon: true, name: '', google: false }; localStorage.setItem('fake-user', JSON.stringify(user)); setTimeout(emit, 0); return user; },
    async google() { return 'closed'; }, async googleIdToken() { return 'ok'; }, async signOut() { user = null; emit(); },
    async list() { return (await fetch(B + '/list')).json(); },
    put: (id, d) => post('/put/' + id, d), merge: (id, d) => post('/merge/' + id, d), remove: (id) => post('/remove/' + id)
  };
}
"""
def serve(route):
    req = route.request; u = req.url.split('fakefb.test')[1]; H = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*'}
    if req.method == 'OPTIONS': return route.fulfill(status=204, headers=H)
    if u == '/fb.js': return route.fulfill(status=200, body=FAKE, headers=dict(H, **{'Content-Type': 'text/javascript'}))
    if u == '/list': return route.fulfill(status=200, body=json.dumps([dict(v, id=k) for k, v in DB.items()]), headers=dict(H, **{'Content-Type': 'application/json'}))
    op, _, uid = u[1:].partition('/'); d = json.loads(req.post_data or '{}')
    if op == 'put':
        why = valid(d)
        if why: REJECT.append((uid, why)); return route.fulfill(status=403, body='no', headers=H)
        DB[uid] = d
    elif op == 'merge':
        cur = DB.setdefault(uid, {})
        for k, v in d.items():
            if isinstance(v, dict) and isinstance(cur.get(k), dict): cur[k].update(v)
            else: cur[k] = v
    elif op == 'remove': DB.pop(uid, None)
    route.fulfill(status=200, body='{}', headers=H)
errs = {'alice': [], 'bob': []}
with sync_playwright() as p:
    br = p.chromium.launch()
    c0 = br.new_context(viewport={'width': 390, 'height': 844}); pg0 = c0.new_page(); pg0.goto(URL); pg0.wait_for_timeout(700); base = D(pg0, 'state()'); c0.close()
    def player(uid, name, town, food, gold, wmin):
        st = json.loads(json.dumps(base))
        st.update({'named': True, 'town': town, 'builder': name, 'food': food, 'gold': gold, 'questsDone': ['gift', 'repair'], 'tray': []})
        st['flags']['tourDone'] = True; st['flags']['coachAsked'] = True; st['speed'] = 60
        st['board'] = {'joined': True, 'fb': True, 'name': name, 'cheers': {}}
        ctx = br.new_context(viewport={'width': 390, 'height': 844}); ctx.route('https://fakefb.test/**', serve)
        pg = ctx.new_page(); pg.on('pageerror', lambda e: errs[uid].append(str(e)))
        pg.add_init_script("window.MAPLEWICK_FIREBASE = { apiKey: 'test' }; window.MAPLEWICK_FB_URL = 'https://fakefb.test/fb.js';"
            + "if (!sessionStorage.getItem('seeded')) { localStorage.setItem('maplewick-town-v7', " + json.dumps(json.dumps(st)) + "); localStorage.setItem('fake-uid', '" + uid + "'); localStorage.setItem('fake-user', JSON.stringify({ uid: '" + uid + "', anon: true, name: '', google: false })); sessionStorage.setItem('seeded','1'); }")
        pg.goto(URL); pg.wait_for_timeout(1500)
        pg.evaluate(f"() => {{ const s = window.MaplewickDebug.state(); }}")
        return pg
    A = player('alice', 'Alice', 'Appleby', 200, 2000, 300)
    B = player('bob', 'Bob', 'Brookfield', 200, 2000, 200)
    def sync(*pgs):
        for pg in pgs: pg.evaluate("() => window.MaplewickDebug.frPush()"); pg.wait_for_timeout(150)
        for pg in pgs: pg.evaluate("() => window.MaplewickDebug.frPoll()"); pg.wait_for_timeout(150)
    sync(A, B); sync(A, B)
    fa = D(A, 'friends()'); ok(fa['me'] == 'alice' and fa['kind'] == 'firebase' and 'alice' in DB and 'bob' in DB, f"both on the board: {sorted(DB)} · rejected writes {REJECT}")
    # friends: Alice adds Bob, Bob adds back
    D(A, "frCall('addFriend', 'bob')"); sync(A, B)
    A.evaluate("() => document.querySelector('#open-friends').click()"); B.evaluate("() => document.querySelector('#open-friends').click()"); A.wait_for_timeout(400)
    ok('added you as a friend' in B.inner_text('#sheet'), 'Bob sees "Alice added you as a friend · Add back"')
    D(B, "frCall('addFriend', 'alice')"); sync(B, A)
    ok(D(A, 'friends()')['mutual'] == ['bob'] and D(B, 'friends()')['mutual'] == ['alice'], 'Alice and Bob are friends')
    A.keyboard.press('Escape'); B.keyboard.press('Escape')
    # a gift of food, once a day
    f0, g0 = D(B, 'friends()')['food'], D(B, 'friends()')['gold']; fon = B.evaluate("() => window.MaplewickDebug.food().on")
    D(A, "frCall('sendGift', 'bob', 'food')"); sync(A, B)
    f1, g1 = D(B, 'friends()')['food'], D(B, 'friends()')['gold']
    ok((abs(f1 - f0 - 25) < 0.6 if fon else g1 - g0 >= 12) and D(A, 'friends()')['food'] < 200 - 24, f"gift of 25 food: Bob's food {f0:.0f} → {f1:.0f}, gold {g0:.0f} → {g1:.0f} (food store on: {fon})")
    D(A, "frCall('sendGift', 'bob', 'food')"); ok(sum(1 for m in D(A, 'friends()')['ob'] if m['k'] == 'gift') == 1, 'only one gift a day')
    # trade: Alice sells 25 food for 25 gold; the food waits safely until Bob answers
    a0 = D(A, 'friends()'); b0 = D(B, 'friends()')
    D(A, "frCall('makeOffer', 'bob', true, 25, 1)"); ok(abs(D(A, 'friends()')['food'] - (a0['food'] - 25)) < 0.6, 'offer made: 25 food set aside')
    sync(A, B); inb = D(B, 'friends()')['inbox']; ok(any(x['k'] == 'offer' for x in inb), 'Bob gets the offer')
    D(B, f"frCall('acceptOffer', {[i for i, x in enumerate(inb) if x['k'] == 'offer'][0]})"); sync(B, A)
    a1 = D(A, 'friends()'); b1 = D(B, 'friends()')
    ok(abs(a1['gold'] - a0['gold'] - 25) < 1 and abs(b1['gold'] - b0['gold'] + 25) < 1 and abs(b1['food'] - b0['food'] - 25) < 0.6, f"trade done: Alice +{a1['gold'] - a0['gold']:.0f} gold, Bob +{b1['food'] - b0['food']:.0f} food −{b0['gold'] - b1['gold']:.0f} gold")
    # a loan: Bob asks Alice for 100 at 3%
    D(B, "frCall('ask', 'alice', 70, 3)"); sync(B, A)
    inb = D(A, 'friends()')['inbox']; ga = D(A, 'friends()')['gold']
    D(A, f"frCall('lendTo', {[i for i, x in enumerate(inb) if x['k'] == 'lreq'][0]})"); sync(A, B)
    fb = D(B, 'friends()'); ok(any(L['friend'] == 'alice' and L['amount'] == 70 for L in fb['loans']) and abs(D(A, 'friends()')['gold'] - ga + 70) < 1, f"Alice lent Bob 70 gold (a quarter of her 300 treasury, rounded): Bob's loans {fb['loans']}")
    D(B, 'payLoan(3)'); sync(B, A)
    la = D(A, 'friends()')['lent'][0]; ok(la['got'] > 10, f"Bob paid some back while playing: Alice got {la['got']}")
    # the bank's promise: Bob goes quiet for 15 days
    gA = D(A, 'friends()')['gold']
    DB['bob']['updatedAt'] = int(time.time() * 1000) - 15 * 86400000; D(A, "frCall('age', 15)")
    A.evaluate("() => window.MaplewickDebug.frPoll()"); A.wait_for_timeout(200)
    la = D(A, 'friends()')['lent'][0]; gA2 = D(A, 'friends()')['gold']
    ok(la.get('closed') and la.get('bank') and abs(gA2 - gA - (70 - 37)) < 1.5, f"Bob went quiet for 15 days: the town bank paid Alice the rest ({gA2 - gA:.0f} gold) and closed the loan")
    D(A, 'frPush()'); B.evaluate("() => window.MaplewickDebug.frPoll()"); B.wait_for_timeout(200)
    ok(not any(L['friend'] for L in D(B, 'friends()')['loans']), "Bob's side: the loan is settled, he owes nothing more")
    # set a time
    D(A, "frCall('setTime', 'bob', 1, 9, 0)"); sync(A, B)
    ok(D(B, 'friends()')['dates'] == [['alice', 1, 9, 0]], f"Bob got the set time Tuesday 09:00: {D(B, 'friends()')['dates']}")
    # focus together: Alice invites Bob, Bob joins, both finish
    A.keyboard.press('Escape'); A.wait_for_timeout(200)
    D(A, "frCall('startTogether', ['bob'], 25)"); A.wait_for_timeout(300); D(A, 'skipReady()')
    sync(A, B); inb = D(B, 'friends()')['inbox']
    ok(any(x['k'] == 'inv' for x in inb), 'Bob gets the invitation')
    B.wait_for_timeout(2200); ok(not B.is_hidden('#frbanner') and 'invites you' in B.inner_text('#frbanner'), f"Bob's Home shows it: {B.inner_text('#frbanner') if not B.is_hidden('#frbanner') else 'hidden'}")
    D(B, f"frCall('joinTogether', {[i for i, x in enumerate(inb) if x['k'] == 'inv'][0]})"); B.wait_for_timeout(300); D(B, 'skipReady()')
    sync(A, B); sync(A, B); A.wait_for_timeout(1200)
    strip = A.inner_text('#focus-tg') if not A.is_hidden('#focus-tg') else ''
    ok('Bob' in strip and 'focusing' in strip, f"Alice's focus screen shows Bob: {strip.replace(chr(10), ' · ')}")
    A.screenshot(path=SH + 's11_together.png')
    ga, gb = D(A, 'friends()')['gold'], D(B, 'friends()')['gold']
    D(A, 'jumpFocus(26)'); A.wait_for_timeout(1500); D(B, 'jumpFocus(26)'); B.wait_for_timeout(1500)
    sync(A, B); sync(A, B)
    ta, tb = D(A, 'friends()')['tg'], D(B, 'friends()')['tg']
    ok(ta and ta.get('res') == 'bonus' and tb and tb.get('res') == 'bonus', f"both finished: Together bonus for both ({ta and ta.get('bonus')}, {tb and tb.get('bonus')})")
    # the Town Fair: Alice 300 + Bob 200 minutes ≥ 8 h for two?
    A.click('#cele-go'); A.wait_for_timeout(500)
    if not A.is_hidden('#chest'): A.click('#chest-go'); A.wait_for_timeout(5500); A.click('#chest-go'); A.wait_for_timeout(600)
    if not A.is_hidden('#result'): A.click('#result-home'); A.wait_for_timeout(2600)
    ok('Together chest' in A.inner_text('#sheet'), 'Alice: "Focused together" card with the Together chest')
    A.screenshot(path=SH + 's11_together_prize.png'); A.keyboard.press('Escape')
    # the Town Fair: two friends, 8 hours together this week
    D(A, 'frCall("weekMin", 300)'); D(B, 'frCall("weekMin", 200)'); sync(A, B); sync(A, B)
    fa, fb = D(A, 'friends()'), D(B, 'friends()')
    trA = D(A, 'state()')['tray']; trB = D(B, 'state()')['tray']
    ok(fa['fair']['total'] >= fa['fair']['goal'] and any(t['type'] == 'fairstall' for t in trA) and any(t['type'] == 'fairstall' for t in trB), f"Town Fair reached ({fa['fair']['total']} of {fa['fair']['goal']} min): a fair stall in both towns")
    A.evaluate("() => document.querySelector('#open-friends').click()"); A.wait_for_timeout(500); A.screenshot(path=SH + 's11_friends.png')
    print('rejected writes', REJECT[:3]); ok(not REJECT, 'the server accepted every write (only its own fields)')
    print('errors', errs['alice'][:2], errs['bob'][:2]); ok(not errs['alice'] and not errs['bob'], 'no page errors')
    br.close()
print('FAILED:' if fails else 'ALL OK', fails)
