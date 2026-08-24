import type { PetAction } from "../behavior/types";
import type {
  AnimationCategory,
  AnimationCompletionRule,
  AnimationDefinition,
  AnimationDirection,
  AnimationInteractionPhase,
  AnimationRegistryDocument,
  AnimationStatus,
  AnimationTrigger,
} from "./types";

const actions = new Set<PetAction>([
  "Breathe",
  "Blink",
  "WaddleWalk",
  "BellySlide",
  "SlipFall",
  "Shiver",
  "EatFish",
  "FlapHappy",
  "BalanceIce",
  "Sleep",
  "SleepInBed",
  "TypeKeyboard",
  "TiltHead",
  "PuffAngry",
  "HeadPat",
  "BellyTickled",
  "BellyDislike",
  "FlipperReact",
  "FeetReact",
  "HoverJump",
  "Dragged",
]);
const categories = new Set<AnimationCategory>([
  "Movement",
  "Idle",
  "Life",
  "Rest",
  "Work",
  "Emote",
  "Touch",
]);
const triggers = new Set<AnimationTrigger>([
  "idle_random",
  "movement",
  "user_drag",
  "user_click",
  "ai_intent",
  "scheduled",
  "manual",
]);
const statuses = new Set<AnimationStatus>(["active", "planned"]);
const directions = new Set<AnimationDirection>([
  "Left",
  "Right",
  "Forward",
  "Backward",
  "None",
]);
const interactionPhases = new Set<AnimationInteractionPhase>([
  "start",
  "loop",
  "end",
  "reaction",
]);

export class AnimationRegistry {
  private readonly byId = new Map<string, AnimationDefinition>();
  private readonly byRuntimeClipId = new Map<string, AnimationDefinition>();

  public constructor(public readonly definitions: readonly AnimationDefinition[]) {
    for (const definition of definitions) {
      this.byId.set(definition.id, definition);
      if (definition.runtimeClipId) {
        this.byRuntimeClipId.set(definition.runtimeClipId, definition);
      }
    }
  }

  public static empty(): AnimationRegistry {
    return new AnimationRegistry([]);
  }

  public getById(id: string): AnimationDefinition | undefined {
    return this.byId.get(id);
  }

  public getByRuntimeClipId(runtimeClipId: string): AnimationDefinition | undefined {
    return this.byRuntimeClipId.get(runtimeClipId);
  }

  public getByAction(action: PetAction): readonly AnimationDefinition[] {
    return this.definitions.filter((definition) => definition.action === action);
  }

  public getByCategory(
    category: AnimationCategory,
  ): readonly AnimationDefinition[] {
    return this.definitions.filter(
      (definition) => definition.category === category,
    );
  }

  public getActive(): readonly AnimationDefinition[] {
    return this.definitions.filter(
      (definition) => definition.status === "active",
    );
  }

  public getActiveByAction(action: PetAction): readonly AnimationDefinition[] {
    return this.getByAction(action).filter(
      (definition) => definition.status === "active",
    );
  }

  public getActiveByCategory(
    category: AnimationCategory,
  ): readonly AnimationDefinition[] {
    return this.getByCategory(category).filter(
      (definition) => definition.status === "active",
    );
  }

  public getRandomActive(
    candidates: readonly AnimationDefinition[] = this.definitions,
  ): AnimationDefinition | undefined {
    const active = candidates.filter(
      (definition) => definition.status === "active",
    );
    return active.length > 0
      ? active[Math.floor(Math.random() * active.length)]
      : undefined;
  }
}

export async function loadAnimationRegistry(): Promise<AnimationRegistry> {
  try {
    const module = await import("../config/animation-registry.json");
    const document = validateRegistryDocument(module.default);
    return new AnimationRegistry(document.animations);
  } catch (error) {
    console.warn("Animation registry is unavailable; using legacy behavior", error);
    return AnimationRegistry.empty();
  }
}

function validateRegistryDocument(value: unknown): AnimationRegistryDocument {
  if (!isRecord(value) || !Number.isInteger(value.version)) {
    throw new Error("Animation registry version is invalid");
  }
  if (!Array.isArray(value.animations)) {
    throw new Error("Animation registry animations must be an array");
  }

  const ids = new Set<string>();
  const runtimeClipIds = new Set<string>();
  const animations = value.animations.map((item, index) => {
    const definition = validateDefinition(item, index);
    if (ids.has(definition.id)) {
      throw new Error(`Duplicate animation registry id: ${definition.id}`);
    }
    ids.add(definition.id);
    if (definition.runtimeClipId) {
      if (runtimeClipIds.has(definition.runtimeClipId)) {
        throw new Error(
          `Duplicate animation runtime clip id: ${definition.runtimeClipId}`,
        );
      }
      runtimeClipIds.add(definition.runtimeClipId);
    }
    return definition;
  });

  return { version: Number(value.version), animations };
}

function validateDefinition(value: unknown, index: number): AnimationDefinition {
  if (!isRecord(value)) {
    throw new Error(`Animation definition at index ${index} is invalid`);
  }
  const id = requireNonEmptyString(value.id, "id", index);
  const action = requireSetValue(value.action, actions, "action", id);
  const category = requireSetValue(
    value.category,
    categories,
    "category",
    id,
  );
  const trigger = requireSetValue(value.trigger, triggers, "trigger", id);
  const status = requireSetValue(value.status, statuses, "status", id);
  const onComplete = validateCompletionRule(value.onComplete, id);

  if (!Number.isInteger(value.frameCount) || Number(value.frameCount) < 1) {
    throw new Error(`Invalid frameCount for animation: ${id}`);
  }
  if (typeof value.loop !== "boolean") {
    throw new Error(`Invalid loop flag for animation: ${id}`);
  }
  if (typeof value.defaultFps !== "number" || value.defaultFps <= 0) {
    throw new Error(`Invalid defaultFps for animation: ${id}`);
  }
  if (
    !Number.isInteger(value.interruptPriority) ||
    Number(value.interruptPriority) < 0
  ) {
    throw new Error(`Invalid interruptPriority for animation: ${id}`);
  }
  if (value.direction !== undefined && !directions.has(value.direction as AnimationDirection)) {
    throw new Error(`Invalid direction for animation: ${id}`);
  }
  if (
    value.runtimeClipId !== undefined &&
    (typeof value.runtimeClipId !== "string" || value.runtimeClipId.length === 0)
  ) {
    throw new Error(`Invalid runtimeClipId for animation: ${id}`);
  }
  if (
    value.interactionGroup !== undefined &&
    (typeof value.interactionGroup !== "string" ||
      value.interactionGroup.length === 0)
  ) {
    throw new Error(`Invalid interactionGroup for animation: ${id}`);
  }
  if (
    value.phase !== undefined &&
    !interactionPhases.has(value.phase as AnimationInteractionPhase)
  ) {
    throw new Error(`Invalid interaction phase for animation: ${id}`);
  }
  if (status === "active" && !value.runtimeClipId) {
    throw new Error(`Active animation requires runtimeClipId: ${id}`);
  }

  return {
    id,
    action,
    category,
    frameCount: Number(value.frameCount),
    loop: value.loop,
    defaultFps: value.defaultFps,
    trigger,
    onComplete,
    status,
    interruptPriority: Number(value.interruptPriority),
    direction: value.direction as AnimationDirection | undefined,
    runtimeClipId: value.runtimeClipId as string | undefined,
    interactionGroup: value.interactionGroup as string | undefined,
    phase: value.phase as AnimationInteractionPhase | undefined,
  };
}

function validateCompletionRule(
  value: unknown,
  id: string,
): AnimationCompletionRule {
  if (
    value === "stay" ||
    value === "return_idle" ||
    value === "restore_previous" ||
    value === "none" ||
    (typeof value === "string" && value.startsWith("transition_to:"))
  ) {
    return value as AnimationCompletionRule;
  }
  throw new Error(`Invalid completion rule for animation: ${id}`);
}

function requireNonEmptyString(
  value: unknown,
  field: string,
  index: number,
): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`Invalid ${field} at animation index ${index}`);
  }
  return value;
}

function requireSetValue<T extends string>(
  value: unknown,
  allowed: ReadonlySet<T>,
  field: string,
  id: string,
): T {
  if (typeof value !== "string" || !allowed.has(value as T)) {
    throw new Error(`Invalid ${field} for animation: ${id}`);
  }
  return value as T;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
