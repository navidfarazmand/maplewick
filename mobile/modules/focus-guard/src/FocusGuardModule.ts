import { NativeModule, requireOptionalNativeModule } from 'expo';

import { FocusGuardModuleEvents } from './FocusGuard.types';

declare class FocusGuardModule extends NativeModule<FocusGuardModuleEvents> {
  /** Starts a new log for a focus session. `nudgeText` may hold %d for the grace seconds. */
  start(graceSec: number, nudgeTitle: string, nudgeText: string): void;
  stop(): void;
  isOn(): boolean;
  /** JSON text: [{ t, e }, …] */
  getLog(): string;
  isLocked(): boolean;
  showCountdown(untilMs: number, title: string, text: string): void;
  hideCountdown(): void;
  /** Sends the app to the back (the Android back button on Home), without closing it. */
  moveToBack(): void;
}

/** Android only for now; null on iPhone until the Screen Time version exists. */
export default requireOptionalNativeModule<FocusGuardModule>('FocusGuard');
