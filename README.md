# Desktop Pet V0.1

Windows independent desktop-pet runtime built with Tauri 2, React, TypeScript,
and PixiJS.

## Current scope

- transparent, borderless, fixed-size, always-on-top window
- pointer-drag window movement
- configuration-driven Sprite and SpriteSheet loading
- reusable animation player with frame count, frame size, FPS, loop control,
  and completion listeners
- registry-driven breathing Idle and random blink behavior
- belly stroking and left/right flipper stroking with handshake loops
- body impatience reactions after a continuous 5–10 second hold
- per-frame timing, touch-loop cancellation, and priority-safe reactions

The approved flipper artwork uses a shared palette and proportions. Handshake
loops take 4.25 seconds; impatience takes 2.04 seconds. The 368×228 transparent
canvas accommodates the hand while preserving the 220×228 body interaction area.

See the [September 11 work summary](docs/work-summary-2026-09-11.md),
[flipper runtime demo](docs/flipper-hold-integration-2026-09-11/demo.html), and
[belly runtime demo](docs/belly-hold-integration-2026-09-09/demo.html).

AI, dialogue, memory, plugins, outfit logic, databases, weather, Git, and IDE
integration are intentionally not implemented in V0.1.

## Asset provenance

`public/assets/animations/liangyaoyao-v2.webp` is an unchanged copy of the
validated legacy asset archived at:

`E:\pet\origin\authoritative\liangyaoyao-lively-v2-package.webp`

Dedicated `idle_breathe.webp` and `idle_blink.webp` sprite sheets are derived
from the existing atlas without overwriting it. The animation registry maps
them to active eight-frame breathing and four-frame blink actions.

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for directory ownership and
the asset/runtime architecture.

For the character identity reference, see
[docs/character-bible.md](docs/character-bible.md).

## Commands

```powershell
cd E:\pet\desktop-pet
npm.cmd install
npm.cmd run build
node scripts/test-touch-reactions.cjs
node scripts/test-frame-durations.cjs
npm.cmd run tauri dev
```

Create the Windows desktop executable and NSIS installer:

```powershell
npm.cmd run build:windows
```

The standalone executable is written to `src-tauri/target/release/desktop-pet.exe`.
The installable `.exe` is written to
`src-tauri/target/release/bundle/nsis/desktop-pet_0.1.0_x64-setup.exe`.

Stop the development runtime with `Ctrl+C` in its terminal.
