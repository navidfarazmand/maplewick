package com.khoreh.maplewick.focusguard

import android.app.Activity
import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Build
import android.view.View
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.view.WindowManager
import expo.modules.kotlin.exception.Exceptions
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

/**
 * Maplewick's phone-pickup check and lock-screen countdown (Android). The rules for what counts as a pickup live in
 * the game; this module only notes what the phone did (see FocusLog).
 */
class FocusGuardModule : Module() {
  private val ctx: Context
    get() = appContext.reactContext?.applicationContext ?: throw Exceptions.ReactContextLost()

  override fun definition() = ModuleDefinition {
    Name("FocusGuard")

    // Each event as it happens: { t: milliseconds, e: "off" | "on" | "unlock" | "fg" | "bg" }
    Events("onEvent", "onShake")

    OnCreate {
      FocusLog.listener = { t, e -> sendEvent("onEvent", mapOf("t" to t.toDouble(), "e" to e)) }
      appContext.reactContext?.applicationContext?.let { FocusLog.resume(it) }
    }

    OnDestroy {
      shakeOff()
      FocusLog.listener = null
    }

    OnActivityEntersForeground {
      shakeOn()
      FocusLog.inFront = true
      appContext.reactContext?.applicationContext?.let { FocusLog.add(it, "fg") }
    }

    OnActivityEntersBackground {
      shakeOff()
      FocusLog.inFront = false
      appContext.reactContext?.applicationContext?.let { FocusLog.add(it, "bg") }
    }

    Function("start") { graceSec: Int, nudgeTitle: String, nudgeText: String ->
      FocusLog.start(ctx, graceSec, nudgeTitle, nudgeText)
    }

    Function("stop") {
      FocusLog.stop(ctx)
    }

    Function("isOn") {
      FocusLog.isOn(ctx)
    }

    // The whole log as JSON text: [{ "t": 1760790000000, "e": "unlock" }, …]
    Function("getLog") {
      FocusLog.log(ctx)
    }

    Function("isLocked") {
      FocusLog.isLocked(ctx)
    }

    Function("showCountdown") { untilMs: Double, title: String, text: String ->
      FocusLog.showCountdown(ctx, untilMs.toLong(), title, text)
    }

    Function("hideCountdown") {
      FocusLog.hideCountdown(ctx)
    }

    Function("moveToBack") {
      appContext.currentActivity?.moveTaskToBack(true)
    }

    // Full screen like a game: the status bar and the navigation buttons are hidden, and a swipe from the edge shows
    // them for a moment. The game also fills the camera cut-out area (it keeps its buttons clear of it itself).
    Function("setImmersive") { on: Boolean ->
      val act: Activity? = appContext.currentActivity
      if (act != null) act.runOnUiThread { immersive(act, on) }
    }
  }

  // ---- Shake to report a problem: two strong shakes within a second, at most once every 3 seconds ----
  private var sensors: SensorManager? = null
  private var lastSpike = 0L
  private var lastShake = 0L
  private val shakeListener = object : SensorEventListener {
    override fun onSensorChanged(e: SensorEvent) {
      val x = e.values[0] / SensorManager.GRAVITY_EARTH
      val y = e.values[1] / SensorManager.GRAVITY_EARTH
      val z = e.values[2] / SensorManager.GRAVITY_EARTH
      val g = Math.sqrt((x * x + y * y + z * z).toDouble())
      if (g < 2.6) return
      val now = System.currentTimeMillis()
      val dt = now - lastSpike
      if (dt in 120L..1000L && now - lastShake > 3000L) {
        lastShake = now
        try { sendEvent("onShake", mapOf("t" to now.toDouble())) } catch (err: Exception) { /* JavaScript not ready */ }
      }
      lastSpike = now
    }
    override fun onAccuracyChanged(s: Sensor?, a: Int) {}
  }

  private fun shakeOn() {
    val c = appContext.reactContext?.applicationContext ?: return
    val sm = c.getSystemService(Context.SENSOR_SERVICE) as? SensorManager ?: return
    val acc = sm.getDefaultSensor(Sensor.TYPE_ACCELEROMETER) ?: return
    if (sensors != null) return
    sensors = sm
    sm.registerListener(shakeListener, acc, SensorManager.SENSOR_DELAY_UI)
  }

  private fun shakeOff() {
    sensors?.unregisterListener(shakeListener)
    sensors = null
  }

  private fun immersive(act: Activity, on: Boolean) {
    val w = act.window ?: return
    if (Build.VERSION.SDK_INT >= 28) {
      val lp = w.attributes
      lp.layoutInDisplayCutoutMode = if (on) WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES else WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_DEFAULT
      w.attributes = lp
    }
    if (Build.VERSION.SDK_INT >= 30) {
      val c = w.insetsController ?: return
      val bars = WindowInsets.Type.statusBars() or WindowInsets.Type.navigationBars()
      if (on) {
        c.systemBarsBehavior = WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        c.hide(bars)
      } else c.show(bars)
    } else oldImmersive(w.decorView, on)
  }

  @Suppress("DEPRECATION")
  private fun oldImmersive(v: View, on: Boolean) {
    val full = View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or View.SYSTEM_UI_FLAG_FULLSCREEN or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or View.SYSTEM_UI_FLAG_LAYOUT_STABLE or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
    v.systemUiVisibility = if (on) full else View.SYSTEM_UI_FLAG_LAYOUT_STABLE
  }
}
