import type { PetAction } from "../behavior/types";

export interface AnimationAnchor {
  x: number;
  y: number;
}

export interface AnimationConfig {
  id: string;
  sourceType: "sprite" | "spritesheet";
  file?: string;
  files?: string[];
  frames: number;
  frameWidth: number;
  frameHeight: number;
  fps: number;
  loop: boolean;
  sheetRow: number;
  sheetColumns?: number;
  startFrame?: number;
  anchor?: AnimationAnchor;
}

export interface AnimationCatalog {
  version: number;
  defaultAnimation: string;
  animations: Record<string, AnimationConfig>;
}

export type AnimationCategory =
  | "Movement"
  | "Idle"
  | "Life"
  | "Rest"
  | "Work"
  | "Emote"
  | "Touch";

export type AnimationTrigger =
  | "idle_random"
  | "movement"
  | "user_drag"
  | "user_click"
  | "ai_intent"
  | "scheduled"
  | "manual";

export type AnimationCompletionRule =
  | "stay"
  | "return_idle"
  | "restore_previous"
  | `transition_to:${string}`
  | "none";

export type AnimationStatus = "active" | "planned";

export type AnimationInteractionPhase = "start" | "loop" | "end" | "reaction";

export type AnimationDirection =
  | "Left"
  | "Right"
  | "Forward"
  | "Backward"
  | "None";

/** Semantic behavior metadata, independent from sprite-sheet layout. */
export interface AnimationDefinition {
  id: string;
  action: PetAction;
  category: AnimationCategory;
  frameCount: number;
  loop: boolean;
  defaultFps: number;
  trigger: AnimationTrigger;
  onComplete: AnimationCompletionRule;
  status: AnimationStatus;
  interruptPriority: number;
  direction?: AnimationDirection;
  runtimeClipId?: string;
  interactionGroup?: string;
  phase?: AnimationInteractionPhase;
}

export interface AnimationRegistryDocument {
  version: number;
  animations: AnimationDefinition[];
}

export type AnimationCompletionListener = (animationId: string) => void;
