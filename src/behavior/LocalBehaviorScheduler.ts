import type { BehaviorConfig } from "./types";

/** Schedules local autonomous behavior without depending on rendering or AI. */
export class LocalBehaviorScheduler {
  private timer: number | null = null;

  public constructor(
    private readonly config: BehaviorConfig["microActions"],
    private readonly onTick: () => void,
  ) {}

  public start(): void {
    if (this.timer === null) {
      this.scheduleNext();
    }
  }

  public stop(): void {
    if (this.timer !== null) {
      window.clearTimeout(this.timer);
      this.timer = null;
    }
  }

  private scheduleNext(): void {
    const delay =
      this.config.minDelayMs +
      Math.random() * Math.max(0, this.config.maxDelayMs - this.config.minDelayMs);
    this.timer = window.setTimeout(() => {
      this.timer = null;
      this.onTick();
      this.scheduleNext();
    }, delay);
  }
}
