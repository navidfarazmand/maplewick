import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, AppState, useColorScheme, BackHandler, Linking, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import Constants from 'expo-constants';
import * as Notifications from 'expo-notifications';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';
import { WebView, type WebViewMessageEvent } from 'react-native-webview';
import type { ShouldStartLoadRequest } from 'react-native-webview/lib/WebViewTypes';
import { GoogleSignin, isErrorWithCode, isSuccessResponse, statusCodes } from '@react-native-google-signin/google-signin';

import FocusGuard from './modules/focus-guard';
import { bridgeScript } from './src/bridge';

/** The game. The app shows the live home-screen version, so every new version reaches the app too. */
const GAME_URL: string = (Constants.expoConfig?.extra?.gameUrl as string) || 'https://navidfarazmand.github.io/maplewick/';
const GAME_ORIGIN = new URL(GAME_URL).origin;
const APP_VERSION = Constants.expoConfig?.version ?? '1.0.0';
const BG_DARK = '#101719', BG_LIGHT = '#E6ECE1'; // the game's two backgrounds

// Hosts the game itself talks to (Firebase, fonts). Any other page opens in the phone's browser.
const INSIDE_HOSTS = [/\.firebaseapp\.com$/, /\.googleapis\.com$/, /\.gstatic\.com$/, /\.web\.app$/];

type Note = { id: string; at: number; title: string; body: string };
type Countdown = { until: number; title: string; text: string } | null;
type PageMsg =
  | { t: 'hello'; version: string }
  | { t: 'focus'; on: boolean; resume?: boolean; start?: number; grace?: number; nudgeTitle?: string; nudgeText?: string }
  | { t: 'away'; countdown: Countdown; notes: Note[] }
  | { t: 'log?' }
  | { t: 'notif?' }
  | { t: 'notify'; title: string; body: string; tag: string }
  | { t: 'google'; clientId: string }
  | { t: 'back'; handled: boolean }
  | { t: 'theme'; dark: boolean };

Notifications.setNotificationHandler({
  handleNotification: async () => ({ shouldShowBanner: true, shouldShowList: true, shouldPlaySound: true, shouldSetBadge: false }),
});

export default function App() {
  return (
    <SafeAreaProvider>
      <Game />
    </SafeAreaProvider>
  );
}

function Game() {
  const insets = useSafeAreaInsets();
  const [dark, setDark] = useState(useColorScheme() !== 'light');
  const BG = dark ? BG_DARK : BG_LIGHT;
  const web = useRef<WebView<{}>>(null); // <{}>: the library's default type parameter makes every prop 'never'
  const [perm, setPerm] = useState<'granted' | 'denied' | 'default' | null>(null);
  const [failed, setFailed] = useState(false);
  const [key, setKey] = useState(0);
  const scheduled = useRef<Note[]>([]);
  const appState = useRef(AppState.currentState);

  const send = useCallback((m: object) => {
    web.current?.injectJavaScript(`window.MaplewickApp && window.MaplewickApp.recv(${JSON.stringify(m)}); true;`);
  }, []);

  // Notification permission as the page's Notification.permission sees it
  useEffect(() => {
    (async () => {
      await setupChannel();
      const p = await Notifications.getPermissionsAsync();
      setPerm(p.granted ? 'granted' : p.canAskAgain ? 'default' : 'denied');
    })();
  }, []);

  // Each thing the phone does during focus goes straight to the game
  useEffect(() => {
    if (!FocusGuard) return;
    const sub = FocusGuard.addListener('onEvent', (ev) => send({ t: 'ev', at: ev.t, e: ev.e }));
    return () => sub.remove();
  }, [send]);

  // The app going to the back or coming to the front
  useEffect(() => {
    const sub = AppState.addEventListener('change', (next) => {
      const was = appState.current;
      appState.current = next;
      if (next === 'active' && was !== 'active') {
        clearAway();
        send({ t: 'visible', on: true });
        sendLog();
      } else if (next === 'background' && was === 'active') {
        send({ t: 'visible', on: false });
      }
    });
    return () => sub.remove();
  }, [send]);

  // Android's back button: the game closes what is open, otherwise the app goes to the back
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      send({ t: 'back' });
      return true;
    });
    return () => sub.remove();
  }, [send]);

  const sendLog = useCallback(() => {
    if (!FocusGuard) return send({ t: 'log', events: [] });
    let events: unknown = [];
    try { events = JSON.parse(FocusGuard.getLog()); } catch { events = []; }
    send({ t: 'log', events });
  }, [send]);

  const clearAway = useCallback(() => {
    scheduled.current = [];
    Notifications.cancelAllScheduledNotificationsAsync().catch(() => {});
    FocusGuard?.hideCountdown();
  }, []);

  const onMessage = useCallback(async (e: WebViewMessageEvent) => {
    let m: PageMsg;
    try { m = JSON.parse(e.nativeEvent.data); } catch { return; }
    switch (m.t) {
      case 'hello':
        break;
      case 'focus':
        if (!FocusGuard) break;
        if (!m.on) { FocusGuard.stop(); break; }
        if (!m.resume || !FocusGuard.isOn()) FocusGuard.start(m.grace ?? 15, m.nudgeTitle ?? 'Your focus is still running', m.nudgeText ?? 'Tap to go back within %d seconds.');
        break;
      case 'away':
        await scheduleAway(m.countdown, m.notes);
        break;
      case 'log?':
        sendLog();
        break;
      case 'notif?': {
        const p = await askNotifications();
        setPerm(p);
        send({ t: 'perm', perm: p });
        break;
      }
      case 'notify':
        // The lap, break, plan and set-time alarms are already scheduled for this moment: don't ring twice
        if (scheduled.current.some((n) => n.title === m.title && Math.abs(n.at - Date.now()) < 180000)) break;
        Notifications.scheduleNotificationAsync({ content: { title: m.title, body: m.body }, trigger: null }).catch(() => {});
        break;
      case 'google':
        send(await googleSignIn(m.clientId));
        break;
      case 'theme':
        setDark(!!m.dark);
        break;
      case 'back':
        if (m.handled) break;
        if (FocusGuard) FocusGuard.moveToBack(); else BackHandler.exitApp();
        break;
    }
  }, [send, sendLog]);

  async function scheduleAway(countdown: Countdown, notes: Note[]) {
    scheduled.current = notes || [];
    await Notifications.cancelAllScheduledNotificationsAsync().catch(() => {});
    if (appState.current === 'active') return; // came back already
    if (countdown && countdown.until > Date.now()) FocusGuard?.showCountdown(countdown.until, countdown.title, countdown.text);
    for (const n of scheduled.current) {
      if (n.at <= Date.now()) continue;
      await Notifications.scheduleNotificationAsync({
        identifier: `mw-${n.id}`,
        content: { title: n.title, body: n.body },
        trigger: { type: Notifications.SchedulableTriggerInputTypes.DATE, date: n.at, channelId: 'alarms' },
      }).catch(() => {});
    }
  }

  const onNavigate = useCallback((req: ShouldStartLoadRequest) => {
    const url = req.url;
    if (/^(about:|blob:|data:|javascript:)/.test(url)) return true;
    let u: URL;
    try { u = new URL(url); } catch { return false; }
    if (u.origin === GAME_ORIGIN) return true;
    if (u.hostname === 'accounts.google.com') {
      // an older game version trying Google's web sign-in, which Google blocks inside apps: sign in natively
      const id = u.searchParams.get('client_id');
      if (id) googleSignIn(id).then(send);
      return false;
    }
    if (INSIDE_HOSTS.some((r) => r.test(u.hostname))) return true;
    Linking.openURL(url).catch(() => {});
    return false;
  }, [send]);

  if (perm === null) return <View style={[styles.fill, { backgroundColor: BG }]} />;

  return (
    // The game draws edge to edge and keeps clear of the status and navigation bars itself (CSS env(safe-area-inset-*),
    // which Android's WebView reports), so only the offline screen needs the insets.
    <View style={[styles.fill, { backgroundColor: BG }]}>
      <StatusBar style={dark ? 'light' : 'dark'} />
      {failed ? (
        <View style={[styles.center, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
          <Text style={styles.title}>Maplewick needs the internet the first time</Text>
          <Text style={styles.text}>After that it works offline. Check your connection and try again.</Text>
          <Pressable style={styles.btn} onPress={() => { setFailed(false); setKey((k) => k + 1); }}>
            <Text style={styles.btnText}>Try again</Text>
          </Pressable>
        </View>
      ) : (
        <WebView<{}>
          key={key}
          ref={web}
          source={{ uri: GAME_URL }}
          style={{ backgroundColor: BG }}
          injectedJavaScriptBeforeContentLoaded={bridgeScript({ appVersion: APP_VERSION, notifPermission: perm })}
          onMessage={onMessage}
          onShouldStartLoadWithRequest={onNavigate}
          onLoadEnd={sendLog}
          onError={() => setFailed(true)}
          onRenderProcessGone={() => setKey((k) => k + 1)}
          javaScriptEnabled
          domStorageEnabled
          cacheEnabled
          cacheMode="LOAD_DEFAULT"
          mediaPlaybackRequiresUserAction={false}
          allowsInlineMediaPlayback
          setSupportMultipleWindows={false}
          overScrollMode="never"
          textZoom={100}
          startInLoadingState
          renderLoading={() => (
            <View style={[styles.center, StyleSheet.absoluteFill, { backgroundColor: BG }]}>
              <ActivityIndicator color="#5b3bc4" />
            </View>
          )}
        />
      )}
    </View>
  );
}

async function setupChannel() {
  if (Platform.OS !== 'android') return;
  await Notifications.setNotificationChannelAsync('alarms', {
    name: 'Laps, breaks and focus plans',
    importance: Notifications.AndroidImportance.HIGH,
    vibrationPattern: [0, 300, 150, 300],
  }).catch(() => {});
}

/** Notifications, then (Android 12+) exact alarms, so lap bells ring on time. */
async function askNotifications(): Promise<'granted' | 'denied' | 'default'> {
  await setupChannel();
  let p = await Notifications.getPermissionsAsync();
  if (!p.granted && p.canAskAgain) p = await Notifications.requestPermissionsAsync();
  if (!p.granted) return p.canAskAgain ? 'default' : 'denied';
  try {
    const ex = await Notifications.getExactAlarmPermissionsAsync();
    // Opens the system screen; if it never comes back, the alarms still ring, just maybe a little late
    if (!ex.granted && ex.canAskAgain) await Promise.race([Notifications.requestExactAlarmPermissionsAsync(), new Promise((r) => setTimeout(r, 60000))]);
  } catch { /* older Android: nothing to ask */ }
  return 'granted';
}

/** Google sign-in on the phone; the game hands the token to Firebase. */
async function googleSignIn(clientId: string): Promise<{ t: 'google'; tok?: string; err?: string }> {
  try {
    GoogleSignin.configure({ webClientId: clientId });
    await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
    try { await GoogleSignin.signOut(); } catch { /* not signed in: fine */ } // always offer the account picker
    const res = await GoogleSignin.signIn();
    if (isSuccessResponse(res) && res.data.idToken) return { t: 'google', tok: res.data.idToken };
    return { t: 'google', err: 'cancelled' };
  } catch (e) {
    if (isErrorWithCode(e)) {
      if (e.code === statusCodes.SIGN_IN_CANCELLED) return { t: 'google', err: 'cancelled' };
      if (e.code === statusCodes.PLAY_SERVICES_NOT_AVAILABLE) return { t: 'google', err: 'play' };
    }
    return { t: 'google', err: 'failed' };
  }
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  title: { fontSize: 20, fontWeight: '700', color: '#8A80A8', textAlign: 'center', marginBottom: 8 },
  text: { fontSize: 15, color: '#8A86A0', textAlign: 'center', marginBottom: 20 },
  btn: { backgroundColor: '#5b3bc4', paddingHorizontal: 24, paddingVertical: 12, borderRadius: 12 },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
