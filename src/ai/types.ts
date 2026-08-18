import type { BehaviorIntent } from "../behavior/types";
import type { EmotionIntent } from "../emotion/types";

export interface AiBehaviorIntent {
  behavior?: BehaviorIntent;
  emotion?: EmotionIntent;
  message?: string;
}
