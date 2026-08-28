import type { PointerDelta, TauriWindowService } from "../platform/TauriWindowService";
import type { PetStateMachine } from "./PetStateMachine";
import hitZones from "../config/pet-hit-zones.json";

const DRAG_THRESHOLD_PX = 5;
const MULTI_CLICK_WINDOW_MS = 2000;
const LONG_HOLD_MIN_DELAY_MS = 9000;
const LONG_HOLD_MAX_DELAY_MS = 13000;
const LONG_HOLD_REACTIONS = ["touch_head_pat_push_away"] as const;

interface PointerSession {
  pointerId: number;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
  hitZone: HitRegion;
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
  private bellyClickTimes: number[] = [];
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
    this.bellyClickTimes = [];
  }

  private readonly handlePointerDown = (event: PointerEvent): void => {
    if (
      event.button !== 0 ||
      isProtectedTarget(event.target)
    ) {
      this.clearPointer();
      return;
    }

    this.pointer = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      currentX: event.clientX,
      currentY: event.clientY,
      hitZone: this.resolveRegion(event.clientX, event.clientY),
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
      this.bellyClickTimes = [];
      return;
    }
    if (pointer.travelDistance > DRAG_THRESHOLD_PX) {
      pointer.cancelled = true;
      this.clearPointer();
      this.bellyClickTimes = [];
      return;
    }
    if (pointer.isHolding) {
      console.debug(`[interaction] ended touch_hold: ${pointer.hitZone}`);
      if (pointer.hitZone === "head" && !pointer.holdReactionTriggered) {
        this.requestTouch("touch_head_pat_end");
      }
      this.clearPointer();
      this.bellyClickTimes = [];
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
    this.bellyClickTimes = [];
  };

  private readonly handleNativeDragEnd = (): void => {
    this.clearPointer();
    this.bellyClickTimes = [];
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
  };

  private scheduleLongHoldReaction(pointer: PointerSession): void {
    const delayRange = LONG_HOLD_MAX_DELAY_MS - LONG_HOLD_MIN_DELAY_MS;
    const delay = LONG_HOLD_MIN_DELAY_MS + Math.floor(this.random() * delayRange);
    const pointerId = pointer.pointerId;
    pointer.longHoldTimer = setTimeout(
      () => this.handleLongHoldReaction(pointerId),
      delay,
    );
    console.debug(`[interaction] scheduled head hold reaction in ${delay}ms`);
  }

  private handleLongHoldReaction(pointerId: number): void {
    const pointer = this.pointer;
    if (
      !pointer ||
      pointer.pointerId !== pointerId ||
      pointer.cancelled ||
      pointer.isDragging ||
      !pointer.isHolding ||
      pointer.hitZone !== "head" ||
      this.windowService.isDragging
    ) {
      return;
    }
    pointer.longHoldTimer = null;
    const index = Math.min(
      LONG_HOLD_REACTIONS.length - 1,
      Math.floor(this.random() * LONG_HOLD_REACTIONS.length),
    );
    const registryId = LONG_HOLD_REACTIONS[index];
    if (this.requestTouch(registryId)) {
      pointer.holdReactionTriggered = true;
      console.debug(`[interaction] triggered long head hold reaction: ${registryId}`);
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
    this.bellyClickTimes = [];
    this.beginNativeDrag();
    console.debug("[interaction] drag threshold crossed");
  }

  private touchRegistryIdForHold(region: HitRegion): string | null {
    switch (region) {
      case "head":
        return "touch_head_pat_start";
      case "belly":
        return "touch_belly_tickled";
      case "flipper":
        return "touch_flipper_react";
      case "feet":
        return "touch_feet_react";
      default:
        return null;
    }
  }

  private handleValidClick(clientX: number, clientY: number): void {
    const region = this.resolveRegion(clientX, clientY);
    if (region === "unknown") {
      this.bellyClickTimes = [];
      console.debug("[interaction] ignored click: unknown region");
      return;
    }

    if (region !== "belly") {
      this.bellyClickTimes = [];
      this.requestTouch({
        head: "touch_head_pat",
        flipper: "touch_flipper_react",
        feet: "touch_feet_react",
      }[region]);
      return;
    }

    const timestamp = this.now();
    this.bellyClickTimes = this.bellyClickTimes.filter(
      (clickTime) => timestamp - clickTime <= MULTI_CLICK_WINDOW_MS,
    );
    this.bellyClickTimes.push(timestamp);
    if (this.bellyClickTimes.length >= 2) {
      this.bellyClickTimes = [];
      this.requestTouch("touch_belly_dislike");
      return;
    }
    this.requestTouch("touch_belly_tickled");
  }

  private resolveRegion(clientX: number, clientY: number): HitRegion {
    const rect = this.stageElement.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) {
      return "unknown";
    }
    const x = (clientX - rect.left) / rect.width;
    const y = (clientY - rect.top) / rect.height;
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
    }
    this.pointer = null;
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
