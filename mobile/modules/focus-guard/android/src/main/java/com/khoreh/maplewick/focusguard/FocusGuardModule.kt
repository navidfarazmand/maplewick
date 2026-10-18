package com.khoreh.maplewick.focusguard

import android.app.Activity
import android.content.Context
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
    Events("onEvent")

    OnCreate {
      FocusLog.listener = { t, e -> sendEvent("onEvent", mapOf("t" to t.toDouble(), "e" to e)) }
      appContext.reactContext?.applicationContext?.let { FocusLog.resume(it) }
    }

    OnDestroy {
      FocusLog.listener = null
    }

    OnActivityEntersForeground {
      FocusLog.inFront = true
      appContext.reactContext?.applicationContext?.let { FocusLog.add(it, "fg") }
    }

    OnActivityEntersBackground {
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
