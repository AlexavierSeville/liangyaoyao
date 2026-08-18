export type PetDirection = "up" | "down" | "left" | "right";

export type PetState =
  | "Idle"
  | "Moving"
  | "Dragged"
  | "Resting"
  | "Working"
  | "Emoting";

export type PetAction =
  | "Breathe"
  | "Blink"
  | "WaddleWalk"
  | "BellySlide"
  | "SlipFall"
  | "Shiver"
  | "EatFish"
  | "FlapHappy"
  | "BalanceIce"
  | "Sleep"
  | "SleepInBed"
  | "TypeKeyboard"
  | "TiltHead"
  | "PuffAngry"
  | "HoverJump"
  | "Dragged";

export interface BehaviorIntent {
  type: string;
  action?: PetAction;
  intensity?: number;
  durationMs?: number;
}

export interface BehaviorConfig {
  directionThresholdPx: number;
  directionSwitchThresholdPx: number;
  animations: {
    idle: string;
    hoverJump: string;
    walking: Record<PetDirection, string>;
    microActions: string[];
  };
  microActions: {
    minDelayMs: number;
    maxDelayMs: number;
    avoidRepeat: boolean;
  };
  size: {
    minPercent: number;
    maxPercent: number;
    stepPercent: number;
    defaultPercent: number;
  };
}
