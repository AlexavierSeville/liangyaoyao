import { AnimationRegistry } from "../animation/loadAnimationRegistry";
import type {
  AnimationCompletionRule,
  AnimationDefinition,
} from "../animation/types";
import type {
  BehaviorConfig,
  PetAction,
  PetDirection,
  PetState,
} from "./types";

export interface PetStateMachineEvents {
  playAnimation: (animationId: string) => void;
  onStateChange?: (state: PetState) => void;
  onActionChange?: (action: PetAction | null) => void;
  onDirectionChange?: (direction: PetDirection) => void;
  onMicroAction?: (animationId: string) => void;
}

export interface AnimationRequestResult {
  accepted: boolean;
  reason?: "planned" | "unknown" | "missing_runtime_clip" | "interrupted";
}

interface PlaybackContext {
  requestedId: string;
  runtimeClipId: string;
  definition?: AnimationDefinition;
  loop: boolean;
  onComplete: AnimationCompletionRule;
}

interface StateContext {
  state: PetState;
  action: PetAction | null;
  priority: number;
  playback: PlaybackContext | null;
}

interface TransitionOptions {
  state: PetState;
  action: PetAction | null;
  animationId?: string;
  fallbackLoop?: boolean;
  fallbackOnComplete?: AnimationCompletionRule;
  priority?: number;
  force?: boolean;
  rememberPrevious?: boolean;
}

/** Owns action priority and translates local input into configured animations. */
export class PetStateMachine {
  private state: PetState = "Idle";
  private action: PetAction | null = null;
  private priority = 0;
  private direction: PetDirection = "down";
  private lastIdleShortAction: string | null = null;
  private pendingDragDelta = { dx: 0, dy: 0 };
  private playback: PlaybackContext | null = null;
  private previousContext: StateContext | null = null;

  public constructor(
    private readonly config: BehaviorConfig,
    private readonly events: PetStateMachineEvents,
    private readonly registry: AnimationRegistry = AnimationRegistry.empty(),
  ) {}

  public get currentState(): PetState {
    return this.state;
  }

  public get currentAction(): PetAction | null {
    return this.action;
  }

  public start(): void {
    this.enterIdle(true);
  }

  public beginDrag(): void {
    this.pendingDragDelta = { dx: 0, dy: 0 };
    this.transition({
      state: "Dragged",
      action: "Dragged",
      priority: 100,
    });
  }

  public updateDrag(dx: number, dy: number): void {
    if (this.state !== "Dragged") {
      return;
    }
    this.pendingDragDelta.dx += dx;
    this.pendingDragDelta.dy += dy;
    const directionThreshold =
      this.action === "WaddleWalk"
        ? this.config.directionSwitchThresholdPx
        : this.config.directionThresholdPx;
    if (
      Math.hypot(this.pendingDragDelta.dx, this.pendingDragDelta.dy) <
      directionThreshold
    ) {
      return;
    }
    const direction = this.directionFromDelta(
      this.pendingDragDelta.dx,
      this.pendingDragDelta.dy,
    );
    this.pendingDragDelta = { dx: 0, dy: 0 };
    if (this.action === "WaddleWalk" && direction === this.direction) {
      return;
    }
    this.direction = direction;
    this.events.onDirectionChange?.(direction);
    this.transition({
      state: "Dragged",
      action: "WaddleWalk",
      animationId: this.config.animations.walking[direction],
      fallbackLoop: true,
      fallbackOnComplete: "stay",
      priority: 100,
      rememberPrevious: false,
    });
  }

  public endDrag(): void {
    this.pendingDragDelta = { dx: 0, dy: 0 };
    if (this.state === "Dragged") {
      this.enterIdle(true);
    }
  }

  public returnToIdle(): void {
    this.enterIdle(true);
  }

  public hoverEnter(): void {
    if (this.state !== "Idle") {
      return;
    }
    this.transition({
      state: "Emoting",
      action: "HoverJump",
      animationId: this.config.animations.hoverJump,
      fallbackLoop: false,
      fallbackOnComplete: "return_idle",
      priority: 40,
    });
  }

  public tryIdleShortAction(): boolean {
    if (this.state !== "Idle") {
      return false;
    }

    const candidates = this.registry.getActiveByCategory("Idle").filter(
      (definition) =>
        definition.trigger === "idle_random" &&
        !definition.loop &&
        definition.onComplete === "return_idle" &&
        Boolean(definition.runtimeClipId),
    );
    const choices = candidates.filter(
      (definition) =>
        !this.config.microActions.avoidRepeat ||
        definition.id !== this.lastIdleShortAction,
    );
    const selected = this.registry.getRandomActive(
      choices.length > 0 ? choices : candidates,
    );
    if (!selected) {
      return false;
    }

    const accepted = this.transition({
      state: "Idle",
      action: selected.action,
      animationId: selected.id,
      priority: selected.interruptPriority,
    });
    if (!accepted) {
      return false;
    }
    this.lastIdleShortAction = selected.id;
    this.events.onMicroAction?.(selected.id);
    return true;
  }

  public requestAnimation(animationId: string): AnimationRequestResult {
    const definition = this.registry.getById(animationId);
    if (definition?.status === "planned") {
      return { accepted: false, reason: "planned" };
    }
    if (definition && !definition.runtimeClipId) {
      return { accepted: false, reason: "missing_runtime_clip" };
    }
    if (!definition && !this.isKnownLegacyAnimation(animationId)) {
      return { accepted: false, reason: "unknown" };
    }

    const accepted = this.transition({
      state: definition ? this.stateForDefinition(definition) : "Emoting",
      action: definition?.action ?? null,
      animationId,
      fallbackLoop: false,
      fallbackOnComplete: "return_idle",
      priority: definition?.interruptPriority ?? 40,
    });
    return accepted
      ? { accepted: true }
      : { accepted: false, reason: "interrupted" };
  }

  public handleAnimationComplete(animationId: string): void {
    const completed = this.playback;
    if (!completed || completed.runtimeClipId !== animationId || completed.loop) {
      return;
    }

    switch (completed.onComplete) {
      case "return_idle":
        this.enterIdle(true);
        return;
      case "restore_previous":
        this.restorePrevious();
        return;
      case "stay":
      case "none":
        return;
      default:
        this.applyTransitionRule(completed.onComplete);
    }
  }

  private enterIdle(force: boolean): void {
    const breathe = this.registry
      .getActiveByAction("Breathe")
      .find(
        (definition) =>
          definition.category === "Idle" &&
          definition.loop &&
          Boolean(definition.runtimeClipId),
      );
    this.transition({
      state: "Idle",
      action: "Breathe",
      animationId: breathe?.id ?? this.config.animations.idle,
      fallbackLoop: true,
      fallbackOnComplete: "stay",
      priority: 10,
      force,
      rememberPrevious: false,
    });
  }

  private transition(options: TransitionOptions): boolean {
    const playback = options.animationId
      ? this.resolvePlayback(
          options.animationId,
          options.fallbackLoop ?? false,
          options.fallbackOnComplete ?? "none",
        )
      : null;
    if (options.animationId && !playback) {
      return false;
    }

    const action = playback?.definition?.action ?? options.action;
    const priority =
      options.priority ??
      playback?.definition?.interruptPriority ??
      this.priorityForAction(action);
    if (!options.force && priority < this.priority) {
      return false;
    }

    if (playback) {
      try {
        this.events.playAnimation(playback.runtimeClipId);
      } catch (error) {
        console.warn(`Unable to play animation: ${playback.runtimeClipId}`, error);
        return false;
      }
    }

    if (options.rememberPrevious !== false && options.state !== this.state) {
      this.previousContext = this.captureContext();
    }
    const stateChanged = options.state !== this.state;
    const actionChanged = action !== this.action;
    this.state = options.state;
    this.action = action;
    this.priority = priority;
    this.playback = playback;
    if (stateChanged) {
      this.events.onStateChange?.(this.state);
    }
    if (actionChanged) {
      this.events.onActionChange?.(this.action);
    }
    return true;
  }

  private resolvePlayback(
    animationId: string,
    fallbackLoop: boolean,
    fallbackOnComplete: AnimationCompletionRule,
  ): PlaybackContext | null {
    const definition =
      this.registry.getById(animationId) ??
      this.registry.getByRuntimeClipId(animationId);
    if (definition?.status === "planned" || (definition && !definition.runtimeClipId)) {
      return null;
    }
    return {
      requestedId: animationId,
      runtimeClipId: definition?.runtimeClipId ?? animationId,
      definition,
      loop: definition?.loop ?? fallbackLoop,
      onComplete: definition?.onComplete ?? fallbackOnComplete,
    };
  }

  private isKnownLegacyAnimation(animationId: string): boolean {
    return (
      animationId === this.config.animations.idle ||
      animationId === this.config.animations.hoverJump ||
      Object.values(this.config.animations.walking).includes(animationId) ||
      this.config.animations.microActions.includes(animationId)
    );
  }

  private captureContext(): StateContext {
    return {
      state: this.state,
      action: this.action,
      priority: this.priority,
      playback: this.playback,
    };
  }

  private restorePrevious(): void {
    const previous = this.previousContext;
    this.previousContext = null;
    if (!previous) {
      this.enterIdle(true);
      return;
    }
    this.transition({
      state: previous.state,
      action: previous.action,
      animationId: previous.playback?.requestedId,
      fallbackLoop: previous.playback?.loop,
      fallbackOnComplete: previous.playback?.onComplete,
      priority: previous.priority,
      force: true,
      rememberPrevious: false,
    });
  }

  private applyTransitionRule(rule: `transition_to:${string}`): void {
    const target = rule.slice("transition_to:".length);
    if (this.isPetState(target)) {
      this.transition({
        state: target,
        action: null,
        priority: 0,
        force: true,
        rememberPrevious: false,
      });
      return;
    }
    if (this.isPetAction(target)) {
      const definition = this.registry.getRandomActive(
        this.registry.getActiveByAction(target),
      );
      if (definition) {
        this.transition({
          state: this.stateForDefinition(definition),
          action: definition.action,
          animationId: definition.id,
          priority: definition.interruptPriority,
          force: true,
          rememberPrevious: false,
        });
      }
    }
  }

  private stateForDefinition(definition: AnimationDefinition): PetState {
    switch (definition.category) {
      case "Movement":
        return "Moving";
      case "Idle":
        return "Idle";
      case "Rest":
        return "Resting";
      case "Work":
        return "Working";
      case "Life":
      case "Emote":
        return "Emoting";
    }
  }

  private priorityForAction(action: PetAction | null): number {
    switch (action) {
      case "Dragged":
        return 100;
      case "SlipFall":
        return 80;
      case "TiltHead":
      case "PuffAngry":
        return 50;
      case "EatFish":
      case "FlapHappy":
      case "BalanceIce":
      case "TypeKeyboard":
        return 40;
      case "HoverJump":
        return 40;
      case "WaddleWalk":
      case "BellySlide":
        return 30;
      case "Sleep":
      case "SleepInBed":
      case "Shiver":
        return 20;
      case "Blink":
        return 15;
      case "Breathe":
        return 10;
      default:
        return 0;
    }
  }

  private isPetState(value: string): value is PetState {
    return [
      "Idle",
      "Moving",
      "Dragged",
      "Resting",
      "Working",
      "Emoting",
    ].includes(value);
  }

  private isPetAction(value: string): value is PetAction {
    return [
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
      "HoverJump",
      "Dragged",
    ].includes(value);
  }

  private directionFromDelta(dx: number, dy: number): PetDirection {
    if (Math.abs(dx) >= Math.abs(dy)) {
      return dx >= 0 ? "right" : "left";
    }
    return dy >= 0 ? "down" : "up";
  }
}
