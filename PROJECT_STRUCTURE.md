# Project Structure

This repository contains a Windows desktop pet built with Tauri 2, React,
TypeScript, and PixiJS. Runtime behavior is split between the web frontend and
the native Tauri shell.

## Top-level layout

```text
desktop-pet/
|-- public/                  Static files copied into the frontend build
|   `-- assets/animations/  Runtime sprite sheets and animation assets
|-- scripts/                 Reproducible local asset-generation utilities
|-- src/                     React, animation, and behavior runtime
|-- src-tauri/               Rust application shell and native integration
|-- index.html               Vite entry document
|-- package.json             Frontend dependencies and npm commands
|-- package-lock.json        Locked frontend dependency graph
|-- vite.config.ts           Vite and Tauri development configuration
|-- tsconfig.json            Frontend TypeScript configuration
`-- README.md                Setup, scope, and common commands
```

Generated directories are intentionally excluded from Git:

- `node_modules/`: installed frontend dependencies
- `dist/`: Vite production output
- `src-tauri/target/`: Cargo build output

## Frontend source

```text
src/
|-- animation/   Animation catalog/registry loading and Pixi playback
|-- behavior/    Scheduler, pet state machine, and behavior types
|-- character/   Character and renderer configuration loaders/types
|-- config/      JSON runtime configuration and animation metadata
|-- platform/    Frontend bridge to Tauri window and native commands
|-- App.tsx      Application composition and input/event forwarding
|-- SettingsPanel.tsx  Standalone settings window for autostart and size
|-- App.css      Desktop-pet window and stage styling
|-- SettingsPanel.css  Settings-window-only styling
`-- main.tsx     React entry point
```

### Animation ownership

- `src/config/animations.json` describes playable runtime clips: source files,
  frame geometry, FPS, looping, and anchors.
- `src/config/animation-registry.json` assigns semantic actions, status,
  priority, completion behavior, and `runtimeClipId` mappings.
- `src/animation/SpriteSheetAnimationPlayer.ts` loads and advances frames.
- `src/animation/PixiPetRuntime.ts` owns PixiJS setup and exposes playback.

Runtime sprite sheets live in `public/assets/animations/`. The original
`liangyaoyao-v2.webp` atlas is retained for legacy clips. Dedicated Idle
assets are stored as `idle_breathe.webp` and `idle_blink.webp`.

### Behavior ownership

- `src/config/behavior.json` contains thresholds, legacy clip references,
  scheduler timing, and size constraints.
- `src/behavior/LocalBehaviorScheduler.ts` emits periodic Idle ticks.
- `src/behavior/PetStateMachine.ts` owns state transitions, priorities,
  animation selection, completion rules, and drag interruption behavior.
- `src/App.tsx` loads dependencies and forwards UI/native events; it does not
  choose actions.

## Native application

```text
src-tauri/
|-- capabilities/        Tauri permission configuration
|-- icons/               Application and installer icons
|-- src/
|   |-- app_control.rs   Application exit and settings-window commands
|   |-- app_tray.rs      System tray setup and menu handling
|   |-- lib.rs           Tauri builder, window/menu commands, native drag
|   `-- main.rs          Native executable entry point
|-- Cargo.toml           Rust dependencies and crate metadata
|-- Cargo.lock           Locked Rust dependency graph
`-- tauri.conf.json      Window, build, and bundle configuration
```

Native drag behavior and exit handling belong in `src-tauri/` and should stay
independent of animation and behavior-state changes.

## Asset workflow

`scripts/build-idle-assets.py` creates the dedicated Idle sprite sheets from
the existing legacy atlas. It requires Pillow and writes into
`public/assets/animations/` without overwriting the source atlas.

## Common commands

```powershell
npm install
npm run build
npm run tauri dev
cargo check --manifest-path src-tauri/Cargo.toml
```
