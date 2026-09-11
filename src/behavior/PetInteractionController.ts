import type { PointerDelta, TauriWindowService } from "../platform/TauriWindowService";
import type { PetStateMachine } from "./PetStateMachine";
import {
  selectLongHoldReaction,
} from "./longHoldReactions";
import hitZones from "../config/pet-hit-zones.json";
import characterConfig from "../config/character.json";

const DRAG_THRESHOLD_PX = 5;
const LONG_HOLD_MIN_DELAY_MS = 9000;
const LONG_HOLD_MAX_DELAY_MS = 13000;
const BODY_LONG_HOLD_MIN_DELAY_MS = 5000;
const BODY_LONG_HOLD_MAX_DELAY_MS = 10000;

interface PointerSession {
  pointerId: number;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
  hitZone: HitRegion;
  flipperSide: "screen_left" | "screen_right";
  startedAt: number;
  isDragging: boolean;
  isHolding: boolean;
  holdTimer: ReturnType<typeof setTimeout> | null;
  longHoldTimer: ReturnType<typeof setTimeout> | null;
  holdReactionTriggered: boolean;
  travelDistance: number;
  cancelled: boolean;
}

type HitRegion = "head" | "belly" | "flipper" | "feet" | "unknown";

const HOLD_DELAY_MS = 400;

interface HitZone {
  xMin?: number;
  xMax?: number;
  yMin: number;
  yMax: number;
  sideWidth?: number;
}

const zones = hitZones as Record<Exclude<HitRegion, "unknown">, HitZone>;

/** Separates click gestures from the existing native drag event chain. */
export class PetInteractionController {
  private pointer: PointerSession | null = null;
  private removeDragMoveListener: (() => void) | null = null;
  private removeDragEndListener: (() => void) | null = null;
  private started = false;

  public constructor(
    private readonly stageElement: HTMLElement,
    private readonly windowService: TauriWindowService,
    private readonly stateMachine: PetStateMachine,
    private readonly eventTarget: Window = window,
    private readonly now: () => number = () => Date.now(),
    private readonly beginNativeDrag: () => void = () => undefined,
    private readonly random: () => number = Math.random,
  ) {}

  public start(): void {
    if (this.started) {
      return;
    }
    this.started = true;
    this.stageElement.addEventListener("pointerdown", this.handlePointerDown);
    this.eventTarget.addEventListener("pointermove", this.handlePointerMove);
    this.eventTarget.addEventListener("pointerup", this.handlePointerUp);
    this.eventTarget.addEventListener("pointercancel", this.handlePointerCancel);
    this.removeDragMoveListener = this.windowService.onDragMove(
      this.handleNativeDragMove,
    );
    this.removeDragEndListener = this.windowService.onDragEnd(
      this.handleNativeDragEnd,
    );
  }

  public dispose(): void {
    if (!this.started) {
      return;
    }
    this.started = false;
    this.stageElement.removeEventListener("pointerdown", this.handlePointerDown);
    this.eventTarget.removeEventListener("pointermove", this.handlePointerMove);
    this.eventTarget.removeEventListener("pointerup", this.handlePointerUp);
    this.eventTarget.removeEventListener("pointercancel", this.handlePointerCancel);
    this.removeDragMoveListener?.();
    this.removeDragEndListener?.();
    this.removeDragMoveListener = null;
    this.removeDragEndListener = null;
    this.clearPointer();
  }

  private readonly handlePointerDown = (event: PointerEvent): void => {
    if (
      event.button !== 0 ||
      isProtectedTarget(event.target)
    ) {
      this.clearPointer();
      return;
    }

    this.clearPointer();
    const rect = this.stageElement.getBoundingClientRect();
    this.pointer = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      currentX: event.clientX,
      currentY: event.clientY,
      hitZone: this.resolveRegion(event.clientX, event.clientY),
      flipperSide: event.clientX < rect.left + rect.width / 2
        ? "screen_left" : "screen_right",
      startedAt: this.now(),
      isDragging: false,
      isHolding: false,
      holdTimer: null,
      longHoldTimer: null,
      holdReactionTriggered: false,
      travelDistance: 0,
      cancelled: false,
    };
    if (this.pointer.hitZone !== "unknown") {
      const pointerId = this.pointer.pointerId;
      this.pointer.holdTimer = setTimeout(
        () => this.handleHoldTimer(pointerId),
        HOLD_DELAY_MS,
      );
    }
  };

  private readonly handlePointerMove = (event: PointerEvent): void => {
    const pointer = this.pointer;
    if (!pointer || pointer.pointerId !== event.pointerId) {
      return;
    }
    pointer.currentX = event.clientX;
    pointer.currentY = event.clientY;
    this.markPointerDistance(
      Math.hypot(event.clientX - pointer.startX, event.clientY - pointer.startY),
    );
  };

  private readonly handleNativeDragMove = (delta: PointerDelta): void => {
    if (!this.pointer) {
      return;
    }
    this.markNativeDistance(Math.hypot(delta.dx, delta.dy));
  };

  private readonly handlePointerUp = (event: PointerEvent): void => {
    const pointer = this.pointer;
    if (!pointer || pointer.pointerId !== event.pointerId) {
      return;
    }
    pointer.currentX = event.clientX;
    pointer.currentY = event.clientY;
    pointer.travelDistance = Math.max(
      pointer.travelDistance,
      Math.hypot(event.clientX - pointer.startX, event.clientY - pointer.startY),
    );

    if (pointer.isDragging || this.windowService.isDragging) {
      this.clearPointer();
      return;
    }
    if (pointer.travelDistance > DRAG_THRESHOLD_PX) {
      pointer.cancelled = true;
      this.clearPointer();
      return;
    }
    if (pointer.isHolding) {
      console.debug(`[interaction] ended touch_hold: ${pointer.hitZone}`);
      if (pointer.hitZone === "head" && !pointer.holdReactionTriggered) {
        this.requestTouch("touch_head_pat_end");
      }
      this.clearPointer();
      return;
    }
    this.clearPointer();
    this.handleValidClick(event.clientX, event.clientY);
  };

  private readonly handlePointerCancel = (event: PointerEvent): void => {
    const pointer = this.pointer;
    if (pointer?.pointerId === event.pointerId) {
      pointer.cancelled = true;
      if (
        pointer.isHolding &&
        !pointer.isDragging &&
        pointer.hitZone === "head" &&
        !pointer.holdReactionTriggered
      ) {
        this.requestTouch("touch_head_pat_end");
      }
      this.clearPointer();
    }
  };

  private readonly handleNativeDragEnd = (): void => {
    this.clearPointer();
  };

  private readonly handleHoldTimer = (pointerId: number): void => {
    const pointer = this.pointer;
    if (
      !pointer ||
      pointer.pointerId !== pointerId ||
      pointer.cancelled ||
      pointer.isDragging ||
      this.windowService.isDragging
    ) {
      return;
    }
    pointer.holdTimer = null;
    pointer.isHolding = true;
    console.debug(`[interaction] touch_hold: ${pointer.hitZone}`);
    const registryId = this.touchRegistryIdForHold(pointer.hitZone);
    if (registryId) {
      const accepted = this.requestTouch(registryId);
      if (accepted && pointer.hitZone === "head") {
        this.scheduleLongHoldReaction(pointer);
      }
    }
    // Body impatience is timed from pointer down, independently of the loop.
    if (pointer.hitZone === "belly" || pointer.hitZone === "flipper") {
      this.scheduleLongHoldReaction(pointer);
    }
  };

  private scheduleLongHoldReaction(pointer: PointerSession): void {
    const isBody = pointer.hitZone === "belly" || pointer.hitZone === "flipper";
    const minimum = isBody ? BODY_LONG_HOLD_MIN_DELAY_MS : LONG_HOLD_MIN_DELAY_MS;
    const maximum = isBody ? BODY_LONG_HOLD_MAX_DELAY_MS : LONG_HOLD_MAX_DELAY_MS;
    const sample = this.random();
    const normalized = Number.isFinite(sample) ? Math.min(1, Math.max(0, sample)) : 0;
    const targetDelay = minimum + Math.floor(normalized * (maximum - minimum));
    const delay = isBody
      ? Math.max(0, targetDelay - (this.now() - pointer.startedAt))
      : targetDelay;
    const pointerId = pointer.pointerId;
    pointer.longHoldTimer = setTimeout(
      () => this.handleLongHoldReaction(pointerId),
      delay,
    );
    console.debug(`[interaction] scheduled ${pointer.hitZone} hold reaction in ${delay}ms`);
  }

  private handleLongHoldReaction(pointerId: number): void {
    const pointer = this.pointer;
    if (
      !pointer ||
      pointer.pointerId !== pointerId ||
      pointer.cancelled ||
      pointer.isDragging ||
      !pointer.isHolding ||
      pointer.holdReactionTriggered ||
      this.windowService.isDragging
    ) {
      return;
    }
    pointer.longHoldTimer = null;
    const registryId = pointer.hitZone === "head"
      ? selectLongHoldReaction(this.random())
      : pointer.hitZone === "belly"
        ? "touch_belly_dislike"
        : pointer.hitZone === "flipper"
          ? `touch_flipper_react_${pointer.flipperSide}`
          : null;
    if (!registryId) {
      return;
    }
    if (this.requestTouch(registryId)) {
      pointer.holdReactionTriggered = true;
      console.debug(`[interaction] triggered long ${pointer.hitZone} hold reaction: ${registryId}`);
    }
  }

  private markPointerDistance(distance: number): void {
    const pointer = this.pointer;
    if (!pointer || pointer.isDragging) {
      return;
    }
    pointer.travelDistance = Math.max(pointer.travelDistance, distance);
    this.maybeBeginDrag(pointer);
  }

  private markNativeDistance(distance: number): void {
    const pointer = this.pointer;
    if (!pointer || pointer.isDragging) {
      return;
    }
    pointer.travelDistance += Math.max(0, distance);
    this.maybeBeginDrag(pointer);
  }

  private maybeBeginDrag(pointer: PointerSession): void {
    if (pointer.travelDistance <= DRAG_THRESHOLD_PX) {
      return;
    }
    pointer.isDragging = true;
    pointer.cancelled = true;
    this.clearPointerTimers(pointer);
    this.endBodyHold();
    this.beginNativeDrag();
    console.debug("[interaction] drag threshold crossed");
  }

  private touchRegistryIdForHold(region: HitRegion): string | null {
    switch (region) {
      case "head":
        return "touch_head_pat_start";
      case "belly":
        return "touch_belly_rub_loop";
      case "flipper":
        return this.pointer ? `touch_flipper_hold_${this.pointer.flipperSide}` : null;
      case "feet":
        return "touch_feet_react";
      default:
        return null;
    }
  }

  private handleValidClick(clientX: number, clientY: number): void {
    const region = this.resolveRegion(clientX, clientY);
    if (region === "unknown") {
      console.debug("[interaction] ignored click: unknown region");
      return;
    }

    const registryId = {
      head: "touch_head_pat",
      belly: "touch_belly_tickled",
      flipper: null,
      feet: "touch_feet_react",
    }[region];
    if (registryId) {
      this.requestTouch(registryId);
    }
  }

  private resolveRegion(clientX: number, clientY: number): HitRegion {
    const rect = this.stageElement.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) {
      return "unknown";
    }
    // Transparent rendering gutters accommodate hands without changing the
    // body's size or stretching its established head/belly/flipper hit zones.
    const interaction = characterConfig.interactionCanvas;
    const interactionWidth = rect.width * interaction.width / characterConfig.canvas.width;
    const interactionHeight = rect.height * interaction.height / characterConfig.canvas.height;
    const x = (clientX - rect.left - (rect.width - interactionWidth) / 2) / interactionWidth;
    const y = (clientY - rect.top - (rect.height - interactionHeight) / 2) / interactionHeight;
    if (x < 0 || x > 1 || y < 0 || y > 1) {
      return "unknown";
    }

    if (inZone(x, y, zones.feet)) {
      return "feet";
    }
    if (inZone(x, y, zones.head)) {
      return "head";
    }
    const flipper = zones.flipper;
    if (
      y >= flipper.yMin &&
      y <= flipper.yMax &&
      (x <= (flipper.sideWidth ?? 0) || x >= 1 - (flipper.sideWidth ?? 0))
    ) {
      return "flipper";
    }
    if (inZone(x, y, zones.belly)) {
      return "belly";
    }
    return "unknown";
  }

  private requestTouch(registryId: string): boolean {
    if (this.stateMachine.currentState === "Dragged") {
      console.debug(`[interaction] skipped ${registryId}: dragged`);
      return false;
    }
    const result = this.stateMachine.requestAnimation(registryId);
    if (result.accepted) {
      console.debug(`[interaction] accepted ${registryId}`);
      return true;
    }
    console.warn(
      `[interaction] rejected ${registryId}: ${result.reason ?? "unknown"}`,
    );
    return false;
  }

  private clearPointer(): void {
    if (this.pointer) {
      this.clearPointerTimers(this.pointer);
      this.endBodyHold();
    }
    this.pointer = null;
  }

  private endBodyHold(): void {
    if (
      (this.pointer?.hitZone === "belly" && this.stateMachine.currentAction === "BellyRub") ||
      (this.pointer?.hitZone === "flipper" && this.stateMachine.currentAction === "FlipperHold")
    ) {
      this.stateMachine.returnToIdle();
    }
  }

  private clearPointerTimers(pointer: PointerSession): void {
    if (pointer.holdTimer !== null) {
      clearTimeout(pointer.holdTimer);
      pointer.holdTimer = null;
    }
    if (pointer.longHoldTimer !== null) {
      clearTimeout(pointer.longHoldTimer);
      pointer.longHoldTimer = null;
    }
  }
}

function inZone(x: number, y: number, zone: HitZone): boolean {
  return (
    x >= (zone.xMin ?? 0) &&
    x <= (zone.xMax ?? 1) &&
    y >= zone.yMin &&
    y <= zone.yMax
  );
}

function isProtectedTarget(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) {
    return false;
  }
  if (target.closest("input, textarea, select, button")) {
    return true;
  }
  return target instanceof HTMLElement && target.isContentEditable;
}
