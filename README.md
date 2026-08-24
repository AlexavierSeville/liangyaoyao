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
- contracts reserved for behavior, emotion, outfit, AI intent, and plugins

AI, dialogue, memory, plugins, outfit logic, databases, weather, Git, and IDE
integration are intentionally not implemented in V0.1.

## Asset provenance

`public/assets/animations/liangyaoyao-v2.webp` is an unchanged copy of the
validated legacy asset at:

`E:\pet\old_assets\liangyaoyao-lively-v2\package\spritesheet.webp`

Dedicated `idle_breathe.webp` and `idle_blink.webp` sprite sheets are derived
from the existing atlas without overwriting it. The animation registry maps
them to active eight-frame breathing and four-frame blink actions.

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for directory ownership and
the asset/runtime architecture.

For the current feature set, animation workflow, runtime controls, and design
constraints, see [PROJECT_DESCRIPTION.md](PROJECT_DESCRIPTION.md).

## Commands

```powershell
cd E:\pet\desktop-pet
npm.cmd install
npm.cmd run build
npm.cmd run tauri dev
```

Stop the development runtime with `Ctrl+C` in its terminal.
