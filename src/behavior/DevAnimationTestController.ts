import { PetStateMachine } from "./PetStateMachine";

const bindings: Readonly<Record<string, string>> = {
  "1": "idle_breathe",
  "2": "idle_blink",
  "3": "walk_waddle_left",
  "4": "walk_waddle_right",
  "5": "emote_tilt_head",
  "6": "emote_puff_angry",
  "7": "touch_head_pat",
  "8": "touch_head_pat_push_away",
  "9": "touch_head_pat_nip",
  "0": "touch_belly_tickled",
};

/** Configurable keyboard bridge for requesting animations during visual QA. */
export class DevAnimationTestController {
  private started = false;

  public constructor(
    private readonly stateMachine: PetStateMachine,
    private readonly eventTarget: Window = window,
  ) {}

  public start(): void {
    if (this.started) {
      return;
    }
    this.started = true;
    this.eventTarget.addEventListener("keydown", this.handleKeyDown);
  }

  public dispose(): void {
    if (!this.started) {
      return;
    }
    this.started = false;
    this.eventTarget.removeEventListener("keydown", this.handleKeyDown);
  }

  private readonly handleKeyDown = (event: KeyboardEvent): void => {
    if (
      event.defaultPrevented ||
      event.repeat ||
      event.altKey ||
      event.ctrlKey ||
      event.metaKey ||
      event.shiftKey ||
      isEditableTarget(event.target)
    ) {
      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      this.stateMachine.returnToIdle();
      console.debug("[animation-test] returned to idle_breathe");
      return;
    }

    const registryId = bindings[event.key];
    if (!registryId) {
      return;
    }

    event.preventDefault();
    const result = this.stateMachine.requestAnimation(registryId);
    if (result.accepted) {
      console.debug(`[animation-test] accepted ${registryId}`);
      return;
    }
    console.warn(
      `[animation-test] rejected ${registryId}: ${result.reason ?? "unknown"}`,
    );
  };
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) {
    return false;
  }
  if (target.closest("input, textarea, select")) {
    return true;
  }
  return target instanceof HTMLElement && target.isContentEditable;
}
