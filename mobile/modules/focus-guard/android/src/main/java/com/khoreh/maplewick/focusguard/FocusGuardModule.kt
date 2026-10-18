package com.khoreh.maplewick.focusguard

import android.content.Context
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
  }
}
