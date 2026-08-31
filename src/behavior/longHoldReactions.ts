export const LONG_HOLD_REACTIONS = [
  "touch_head_pat_push_away",
  "touch_head_pat_nip",
] as const;

export type LongHoldReaction = (typeof LONG_HOLD_REACTIONS)[number];

export function selectLongHoldReaction(randomValue: number): LongHoldReaction {
  const normalized = Number.isFinite(randomValue)
    ? Math.min(0.999999999, Math.max(0, randomValue))
    : 0;
  const index = Math.floor(normalized * LONG_HOLD_REACTIONS.length);
  return LONG_HOLD_REACTIONS[index];
}
