import type { AnimationCatalog } from "./types";
import animationCatalog from "../config/animations.json";

export async function loadAnimationCatalog(): Promise<AnimationCatalog> {
  return animationCatalog as AnimationCatalog;
}
