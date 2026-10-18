/** What the phone did during a focus session. */
export type FocusEventName = 'off' | 'on' | 'unlock' | 'fg' | 'bg';

export type FocusEvent = { t: number; e: FocusEventName };

export type FocusGuardModuleEvents = {
  onEvent: (event: FocusEvent) => void;
  onShake: (event: { t: number }) => void;
};
