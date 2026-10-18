package com.khoreh.maplewick.focusguard

import android.app.KeyguardManager
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import org.json.JSONArray
import org.json.JSONObject

/**
 * The phone-pickup log for one focus session.
 *
 * While a session runs it notes, with the time:
 *   "off"    the screen went off
 *   "on"     the screen came on (still locked)
 *   "unlock" the phone was unlocked
 *   "fg"     Maplewick came to the front
 *   "bg"     Maplewick went to the back (another app, home screen, or the screen going off)
 *
 * The game reads the log and decides what counts as picking up the phone (unlocked with Maplewick in the back for
 * longer than the grace time, outside a lap break). The log is kept in SharedPreferences, so it survives the app's
 * JavaScript being paused; the game also gets each event as it happens.
 *
 * When the phone is unlocked with Maplewick in the back, a gentle notification says the focus is still running, so a
 * reflex unlock can be undone within the grace time.
 */
object FocusLog {
  private const val PREFS = "maplewick_focus_guard"
  private const val MAX_EVENTS = 2000
  const val CH_FOCUS = "maplewick_focus"
  const val CH_NUDGE = "maplewick_nudge"
  private const val ID_COUNTDOWN = 7301
  private const val ID_NUDGE = 7302

  @Volatile private var receiver: BroadcastReceiver? = null
  @Volatile var inFront: Boolean = true
  @Volatile var listener: ((Long, String) -> Unit)? = null
  private val main = Handler(Looper.getMainLooper())
  private var nudgeCheck: Runnable? = null

  private fun prefs(ctx: Context) = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

  fun isOn(ctx: Context): Boolean = prefs(ctx).getBoolean("on", false)

  @Synchronized
  fun add(ctx: Context, e: String) {
    val p = prefs(ctx)
    if (!p.getBoolean("on", false)) return
    val t = System.currentTimeMillis()
    val arr = try { JSONArray(p.getString("log", "[]")) } catch (x: Exception) { JSONArray() }
    if (arr.length() < MAX_EVENTS) {
      arr.put(JSONObject().put("t", t).put("e", e))
      p.edit().putString("log", arr.toString()).apply()
    }
    try { listener?.invoke(t, e) } catch (x: Exception) { /* the app's JavaScript may be gone */ }
    if (e == "unlock" || e == "bg") scheduleNudge(ctx)
    if (e == "fg" || e == "off") clearNudge(ctx)
  }

  fun log(ctx: Context): String = prefs(ctx).getString("log", "[]") ?: "[]"

  fun isLocked(ctx: Context): Boolean {
    val km = ctx.getSystemService(Context.KEYGUARD_SERVICE) as? KeyguardManager
    return km?.isKeyguardLocked ?: false
  }

  fun screenOn(ctx: Context): Boolean {
    val pm = ctx.getSystemService(Context.POWER_SERVICE) as? PowerManager
    return pm?.isInteractive ?: true
  }

  /** Starts a new log. The session starts in the app, with the phone in hand. */
  @Synchronized
  fun start(ctx: Context, graceSec: Int, nudgeTitle: String, nudgeText: String) {
    val app = ctx.applicationContext
    prefs(app).edit()
      .putBoolean("on", true)
      .putString("log", "[]")
      .putInt("grace", graceSec)
      .putString("nudgeTitle", nudgeTitle)
      .putString("nudgeText", nudgeText)
      .apply()
    register(app)
    add(app, if (inFront) "fg" else "bg")
    add(app, if (!screenOn(app)) "off" else if (isLocked(app)) "on" else "unlock")
  }

  @Synchronized
  fun stop(ctx: Context) {
    val app = ctx.applicationContext
    prefs(app).edit().putBoolean("on", false).apply()
    unregister(app)
    clearNudge(app)
    hideCountdown(app)
  }

  /** After the app's process was restarted in the middle of a session: listen again. */
  fun resume(ctx: Context) {
    val app = ctx.applicationContext
    if (isOn(app)) register(app)
  }

  private fun register(app: Context) {
    if (receiver != null) return
    val r = object : BroadcastReceiver() {
      override fun onReceive(c: Context, intent: Intent) {
        when (intent.action) {
          Intent.ACTION_SCREEN_OFF -> add(app, "off")
          Intent.ACTION_SCREEN_ON -> add(app, if (isLocked(app)) "on" else "unlock") // no lock screen: on means unlocked
          Intent.ACTION_USER_PRESENT -> add(app, "unlock")
        }
      }
    }
    val f = IntentFilter().apply {
      addAction(Intent.ACTION_SCREEN_OFF)
      addAction(Intent.ACTION_SCREEN_ON)
      addAction(Intent.ACTION_USER_PRESENT)
    }
    try {
      // Only the system sends these (protected broadcasts), so the flag changes nothing about who can reach us.
      if (Build.VERSION.SDK_INT >= 33) app.registerReceiver(r, f, Context.RECEIVER_EXPORTED) else app.registerReceiver(r, f)
      receiver = r
    } catch (x: Exception) { /* without it the game still sees the app going to the back */ }
  }

  private fun unregister(app: Context) {
    val r = receiver ?: return
    receiver = null
    try { app.unregisterReceiver(r) } catch (x: Exception) { /* already gone */ }
  }

  // ---- The nudge: "Your focus is still running" ----

  private fun scheduleNudge(ctx: Context) {
    val app = ctx.applicationContext
    nudgeCheck?.let { main.removeCallbacks(it) }
    // wait a moment: going to the back is also what happens when the screen turns off
    val r = Runnable {
      if (isOn(app) && !inFront && screenOn(app) && !isLocked(app)) showNudge(app)
    }
    nudgeCheck = r
    main.postDelayed(r, 1500)
  }

  private fun clearNudge(ctx: Context) {
    nudgeCheck?.let { main.removeCallbacks(it) }
    nudgeCheck = null
    val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager ?: return
    try { nm.cancel(ID_NUDGE) } catch (x: Exception) { /* ignore */ }
  }

  private fun showNudge(app: Context) {
    val p = prefs(app)
    val grace = p.getInt("grace", 15)
    val title = p.getString("nudgeTitle", null) ?: "Your focus is still running"
    val text = (p.getString("nudgeText", null) ?: "Tap to go back within %d seconds.").replace("%d", grace.toString())
    val nm = app.getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager ?: return
    channels(app, nm)
    val b = builder(app, CH_NUDGE)
      .setContentTitle(title)
      .setContentText(text)
      .setAutoCancel(true)
      .setCategory(Notification.CATEGORY_REMINDER)
    if (Build.VERSION.SDK_INT >= 26) b.setTimeoutAfter((grace + 5) * 1000L) else oldHeadsUp(b)
    openApp(app)?.let { b.setContentIntent(it) }
    try { nm.notify(ID_NUDGE, b.build()) } catch (x: Exception) { /* notifications not allowed */ }
  }

  // ---- The lock-screen countdown ----

  fun showCountdown(ctx: Context, untilMs: Long, title: String, text: String) {
    val app = ctx.applicationContext
    val nm = app.getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager ?: return
    channels(app, nm)
    val b = builder(app, CH_FOCUS)
      .setContentTitle(title)
      .setContentText(text)
      .setOngoing(true)
      .setOnlyAlertOnce(true)
      .setShowWhen(true)
      .setWhen(untilMs)
      .setUsesChronometer(true)
      .setVisibility(Notification.VISIBILITY_PUBLIC)
      .setCategory(Notification.CATEGORY_PROGRESS)
    if (Build.VERSION.SDK_INT >= 24) b.setChronometerCountDown(true)
    openApp(app)?.let { b.setContentIntent(it) }
    try { nm.notify(ID_COUNTDOWN, b.build()) } catch (x: Exception) { /* notifications not allowed */ }
  }

  fun hideCountdown(ctx: Context) {
    val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager ?: return
    try { nm.cancel(ID_COUNTDOWN) } catch (x: Exception) { /* ignore */ }
  }

  // ---- Helpers ----

  private fun channels(app: Context, nm: NotificationManager) {
    if (Build.VERSION.SDK_INT < 26) return
    if (nm.getNotificationChannel(CH_FOCUS) == null) {
      val c = NotificationChannel(CH_FOCUS, "Focus timer", NotificationManager.IMPORTANCE_LOW)
      c.description = "The time left while you focus, on the lock screen."
      c.setShowBadge(false)
      c.lockscreenVisibility = Notification.VISIBILITY_PUBLIC
      nm.createNotificationChannel(c)
    }
    if (nm.getNotificationChannel(CH_NUDGE) == null) {
      val c = NotificationChannel(CH_NUDGE, "Back to focus", NotificationManager.IMPORTANCE_HIGH)
      c.description = "A reminder when you unlock the phone during focus."
      c.enableVibration(true)
      c.setShowBadge(false)
      nm.createNotificationChannel(c)
    }
  }

  private fun builder(app: Context, channel: String): Notification.Builder {
    val b = if (Build.VERSION.SDK_INT >= 26) Notification.Builder(app, channel) else oldBuilder(app)
    return b.setSmallIcon(smallIcon(app))
  }

  @Suppress("DEPRECATION")
  private fun oldBuilder(app: Context): Notification.Builder = Notification.Builder(app)

  @Suppress("DEPRECATION")
  private fun oldHeadsUp(b: Notification.Builder) {
    b.setPriority(Notification.PRIORITY_HIGH).setDefaults(Notification.DEFAULT_VIBRATE)
  }

  private fun smallIcon(app: Context): Int {
    // The icon made by the expo-notifications plugin, else the app icon
    val id = app.resources.getIdentifier("notification_icon", "drawable", app.packageName)
    return if (id != 0) id else app.applicationInfo.icon
  }

  private fun openApp(app: Context): PendingIntent? {
    val i = app.packageManager.getLaunchIntentForPackage(app.packageName) ?: return null
    i.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)
    return PendingIntent.getActivity(app, 0, i, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
  }
}
