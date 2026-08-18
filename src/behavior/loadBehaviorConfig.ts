import behaviorConfig from "../config/behavior.json";
import type { BehaviorConfig } from "./types";

export async function loadBehaviorConfig(): Promise<BehaviorConfig> {
  return behaviorConfig as BehaviorConfig;
}
