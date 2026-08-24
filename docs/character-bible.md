# Liangyaoyao Penguin Character Bible

This document is the canonical visual contract for future desktop-pet animation frames. It is derived from the existing stable assets, not from generated touch or emote assets.

## Authority

Use these sources in this order:

1. `public/assets/animations/liangyaoyao-v2.webp`, atlas row 0 column 0 for the standard front pose.
2. `public/assets/animations/idle_breathe.webp` for stable idle proportions and baseline.
3. `public/assets/animations/idle_blink.webp` for the closed-eye facial variant.
4. Atlas row 1 column 0 and row 2 column 0 for the right- and left-walk reference poses.

Generated action assets never redefine the character. If a generated frame conflicts with this document, the generated frame is wrong and must be corrected.

The machine-readable source is `src/config/character-spec.json`.

## Canvas And Anchor

- Every runtime frame is exactly `192x208` pixels.
- The sprite anchor is `(0.5, 1.0)`, equivalent to pixel `(96, 208)`.
- The standard visible body bounds are approximately `x=21..170`, `y=5..203` using an alpha threshold of 12.
- The last opaque foot row is approximately `y=202`; preserve five transparent rows below it.
- The standard body center is approximately `x=96`.
- Keep at least 21 px left, 22 px right, 5 px top, and 5 px bottom transparent margin for the unextended body.

An action may extend above the head when its semantics require it, such as a hand touching the head, but the penguin body and feet must still obey the standard bounds and baseline.

## Proportions

The canonical front pose is round, short, and chubby. Its visible height is about 198 px and visible width about 149 px.

- The head silhouette reaches from about `y=5` to `y=97`.
- The cream belly contour is about `x=51..139`, `y=72..189`.
- Flippers are short and tapered, beginning around `y=91` and ending around `y=171`.
- Each foot is about 48 px wide and 28 px high. Foot centers are approximately `x=56` and `x=134`, with a 30 px inner gap.
- Eye centers are approximately `(70.5, 55)` and `(117, 55)`.
- The beak is a small orange oval centered near `(95, 61.5)`.

For ordinary action deformation, keep body scale within 97%-103%, body center within 3 px, head top within 4 px, and facial landmarks within 4 px. These are animation tolerances, not permission to redesign the character.

## Visual Identity

The five strongest recognition signals are:

1. A large round charcoal head and back.
2. A warm cream face and belly patch.
3. A small orange oval beak.
4. Short orange feet with fixed spacing.
5. Short tapered flippers and a wide, upright front silhouette.

The rendering is a soft illustrated 2D character with a warm paper-like texture and a dark soft outline. Do not turn it into a vector icon, glossy 3D model, realistic bird, or a newly designed mascot.

Approximate palette anchors are cream `#FDF2D1`, charcoal `#635245`, outline `#2F2923`, orange `#EEA95A`, and eye/detail dark `#2B251F`. These are reference colors; preserve the visual relationship and texture rather than applying flat fills.

## Reference Frames

| Role | Source |
| --- | --- |
| Front standard | `liangyaoyao-v2.webp`, row 0 column 0; also idle_breathe frame 1 |
| Front closed eyes | `liangyaoyao-v2.webp`, row 0 column 3; also idle_blink frames 2-3 |
| Right walk standard | `liangyaoyao-v2.webp`, row 1 column 0; runtime clip `walking-right` |
| Left walk standard | `liangyaoyao-v2.webp`, row 2 column 0; runtime clip `walking-left` |

## Generation And Review Rules

Before generating an action, provide the character spec as the invariant reference and describe the action separately. Do not ask an image model to invent a new character sheet.

For every generated frame:

- preserve `192x208`, alpha, anchor, body scale, face landmarks, belly contour, flipper length, foot size, and foot baseline;
- compare the neutral start/end frames against the front standard and idle_breathe;
- reject any frame whose neutral penguin looks shorter, taller, wider, or narrower than the canonical body;
- inspect the result on a solid background as well as transparent compositing;
- measure alpha bounds and baseline before runtime integration.

The current `touch_head_pat` asset is an action asset only. It must not be used as a character reference for later work.
