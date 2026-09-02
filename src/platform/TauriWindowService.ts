import { LogicalSize } from "@tauri-apps/api/dpi";
import { invoke } from "@tauri-apps/api/core";
import { emit, listen } from "@tauri-apps/api/event";
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
  private readonly sizeChangeListeners = new Set<(percent: number) => void>();
  private unlistenDragMove: (() => void) | null = null;
  private unlistenDragEnd: (() => void) | null = null;
  private unlistenSizeChange: (() => void) | null = null;
  private unlistenSizeRequest: (() => void) | null = null;
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
    return this.normalizePercent(requestedPercent, config);
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
      const unlistenSizeChange = await listen<number>(
        "pet-size-change",
        ({ payload }) => {
          for (const listener of this.sizeChangeListeners) {
            listener(payload);
          }
        },
      );
      const unlistenSizeRequest = await listen("pet-size-request", () => {
        const stored = window.localStorage.getItem(SIZE_STORAGE_KEY);
        const percent = stored === null ? Number.NaN : Number(stored);
        if (Number.isFinite(percent)) {
          void emit("pet-size-snapshot", percent);
        }
      });

      if (this.disposed) {
        unlistenDragMove();
        unlistenDragEnd();
        unlistenSizeChange();
        unlistenSizeRequest();
      } else {
        this.unlistenDragMove = unlistenDragMove;
        this.unlistenDragEnd = unlistenDragEnd;
        this.unlistenSizeChange = unlistenSizeChange;
        this.unlistenSizeRequest = unlistenSizeRequest;
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

  public onSizeChange(listener: (percent: number) => void): () => void {
    this.sizeChangeListeners.add(listener);
    return () => this.sizeChangeListeners.delete(listener);
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
    const percent = this.normalizePercent(requestedPercent, config);
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
    const [sizeMenu, settingsItem, separator, quitItem] = await Promise.all([
      Submenu.new({
        id: "size-menu",
        text: "调整大小",
        items: sizeItems,
      }),
      MenuItem.new({
        id: "pet-menu-settings",
        text: "控制面板",
        action: () => {
          void invoke("open_settings").catch((error: unknown) => {
            console.error("Unable to open pet settings", error);
          });
        },
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
    const menu = await Menu.new({
      items: [sizeMenu, settingsItem, separator, quitItem],
    });
    await menu.popup(undefined, this.windowHandle);
  }

  public dispose(): void {
    this.disposed = true;
    this.endDrag();
    this.dragMoveListeners.clear();
    this.dragEndListeners.clear();
    this.sizeChangeListeners.clear();
    this.unlistenDragMove?.();
    this.unlistenDragEnd?.();
    this.unlistenSizeChange?.();
    this.unlistenSizeRequest?.();
    this.unlistenDragMove = null;
    this.unlistenDragEnd = null;
    this.unlistenSizeChange = null;
    this.unlistenSizeRequest = null;
  }

  private clampPercent(
    percent: number,
    config: BehaviorConfig["size"],
  ): number {
    if (!Number.isFinite(percent)) {
      return config.defaultPercent;
    }
    return Math.min(config.maxPercent, Math.max(config.minPercent, percent));
  }

  private normalizePercent(
    percent: number,
    config: BehaviorConfig["size"],
  ): number {
    const clamped = this.clampPercent(percent, config);
    const step = Math.max(1, config.stepPercent);
    const stepped =
      Math.round((clamped - config.minPercent) / step) * step +
      config.minPercent;
    return Math.min(config.maxPercent, Math.max(config.minPercent, stepped));
  }
}
