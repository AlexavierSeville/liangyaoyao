import { LogicalSize } from "@tauri-apps/api/dpi";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import {
  Menu,
  MenuItem,
  PredefinedMenuItem,
  Submenu,
} from "@tauri-apps/api/menu";
import { getCurrentWindow } from "@tauri-apps/api/window";
import type { BehaviorConfig } from "../behavior/types";

const SIZE_STORAGE_KEY = "desktop-pet.size-percent";

export interface PointerDelta {
  dx: number;
  dy: number;
}

export interface AppliedWindowSize {
  percent: number;
  scale: number;
  width: number;
  height: number;
}

/** Isolates Tauri and Windows-specific window behavior from the pet runtime. */
export class TauriWindowService {
  private readonly windowHandle: ReturnType<typeof getCurrentWindow> | null;
  private readonly dragMoveListeners = new Set<(delta: PointerDelta) => void>();
  private readonly dragEndListeners = new Set<() => void>();
  private unlistenDragMove: (() => void) | null = null;
  private unlistenDragEnd: (() => void) | null = null;
  private dragging = false;
  private disposed = false;

  public constructor() {
    try {
      this.windowHandle = getCurrentWindow();
    } catch {
      this.windowHandle = null;
    }
  }

  public get isDragging(): boolean {
    return this.dragging;
  }

  public readStoredSizePercent(config: BehaviorConfig["size"]): number {
    const storedValue = window.localStorage.getItem(SIZE_STORAGE_KEY);
    const storedPercent = storedValue === null ? Number.NaN : Number(storedValue);
    const requestedPercent = Number.isFinite(storedPercent)
      ? storedPercent
      : config.defaultPercent;
    return this.clampPercent(requestedPercent, config);
  }

  public async initialize(): Promise<void> {
    try {
      const unlistenDragMove = await listen<PointerDelta>(
        "pet-drag-move",
        ({ payload }) => {
          if (!this.dragging) {
            return;
          }
          for (const listener of this.dragMoveListeners) {
            listener(payload);
          }
        },
      );
      const unlistenDragEnd = await listen("pet-drag-end", () => {
        if (!this.dragging) {
          return;
        }
        this.dragging = false;
        for (const listener of this.dragEndListeners) {
          listener();
        }
      });

      if (this.disposed) {
        unlistenDragMove();
        unlistenDragEnd();
      } else {
        this.unlistenDragMove = unlistenDragMove;
        this.unlistenDragEnd = unlistenDragEnd;
      }
    } catch {
      // Browser preview has no Tauri event bridge.
    }
  }

  public onDragMove(listener: (delta: PointerDelta) => void): () => void {
    this.dragMoveListeners.add(listener);
    return () => this.dragMoveListeners.delete(listener);
  }

  public onDragEnd(listener: () => void): () => void {
    this.dragEndListeners.add(listener);
    return () => this.dragEndListeners.delete(listener);
  }

  public beginDrag(): void {
    this.dragging = true;
  }

  public async startNativeDrag(): Promise<void> {
    await invoke("start_pet_drag");
  }

  public async stopNativeDrag(): Promise<void> {
    await invoke("stop_pet_drag").catch(() => undefined);
  }

  public endDrag(): void {
    this.dragging = false;
  }

  public async applySizePercent(
    requestedPercent: number,
    config: BehaviorConfig["size"],
    baseWidth: number,
    baseHeight: number,
  ): Promise<AppliedWindowSize> {
    const percent = this.clampPercent(requestedPercent, config);
    const scale = percent / 100;
    const width = Math.round(baseWidth * scale);
    const height = Math.round(baseHeight * scale);
    window.localStorage.setItem(SIZE_STORAGE_KEY, String(percent));
    await this.windowHandle
      ?.setSize(new LogicalSize(width, height))
      .catch(() => undefined);
    return { percent, scale, width, height };
  }

  public async showPetMenu(
    config: BehaviorConfig["size"],
    onSelect: (percent: number) => void,
  ): Promise<void> {
    if (!this.windowHandle) {
      return;
    }
    const optionCount =
      Math.floor((config.maxPercent - config.minPercent) / config.stepPercent) + 1;
    const sizeItems = await Promise.all(
      Array.from({ length: optionCount }, (_, index) => {
        const percent = config.minPercent + index * config.stepPercent;
        return MenuItem.new({
          id: `size-${percent}`,
          text: `${percent}%`,
          action: () => onSelect(percent),
        });
      }),
    );
    const [sizeMenu, separator, quitItem] = await Promise.all([
      Submenu.new({
        id: "size-menu",
        text: "调整大小",
        items: sizeItems,
      }),
      PredefinedMenuItem.new({ item: "Separator" }),
      MenuItem.new({
        id: "pet-menu-quit",
        text: "退出",
        action: () => {
          void invoke("quit_app").catch((error: unknown) => {
            console.error("Unable to exit desktop pet", error);
          });
        },
      }),
    ]);
    const menu = await Menu.new({ items: [sizeMenu, separator, quitItem] });
    await menu.popup(undefined, this.windowHandle);
  }

  public dispose(): void {
    this.disposed = true;
    this.endDrag();
    this.dragMoveListeners.clear();
    this.dragEndListeners.clear();
    this.unlistenDragMove?.();
    this.unlistenDragEnd?.();
    this.unlistenDragMove = null;
    this.unlistenDragEnd = null;
  }

  private clampPercent(
    percent: number,
    config: BehaviorConfig["size"],
  ): number {
    return Math.min(config.maxPercent, Math.max(config.minPercent, percent));
  }
}
