import { useEffect, useState } from "react";
import { emit, listen } from "@tauri-apps/api/event";
import { getCurrentWindow } from "@tauri-apps/api/window";
import {
  disable,
  enable,
  isEnabled,
} from "@tauri-apps/plugin-autostart";
import { loadBehaviorConfig } from "./behavior/loadBehaviorConfig";
import type { BehaviorConfig } from "./behavior/types";
import "./SettingsPanel.css";

const SIZE_STORAGE_KEY = "desktop-pet.size-percent";

function SettingsPanel() {
  const [sizeConfig, setSizeConfig] = useState<BehaviorConfig["size"] | null>(null);
  const [sizePercent, setSizePercent] = useState(100);
  const [autoStart, setAutoStart] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let disposed = false;
    let removeSizeChange: (() => void) | null = null;
    let removeSizeSnapshot: (() => void) | null = null;

    const initialize = async () => {
      const [behaviorConfig, autoStartEnabled] = await Promise.all([
        loadBehaviorConfig(),
        readAutoStart(),
      ]);
      if (disposed) {
        return;
      }

      setSizeConfig(behaviorConfig.size);
      setSizePercent(readStoredSizePercent(behaviorConfig.size));
      setAutoStart(autoStartEnabled);

      const [unlistenSizeChange, unlistenSizeSnapshot] = await Promise.all([
        listen<number>("pet-size-change", ({ payload }) => {
          if (!disposed) {
            setSizePercent(normalizePercent(payload, behaviorConfig.size));
          }
        }),
        listen<number>("pet-size-snapshot", ({ payload }) => {
          if (!disposed) {
            setSizePercent(normalizePercent(payload, behaviorConfig.size));
          }
        }),
      ]);

      if (disposed) {
        unlistenSizeChange();
        unlistenSizeSnapshot();
        return;
      }

      removeSizeChange = unlistenSizeChange;
      removeSizeSnapshot = unlistenSizeSnapshot;
      await emit("pet-size-request").catch(() => undefined);
    };

    void initialize()
      .catch((reason: unknown) => {
        if (!disposed) {
          setError(reason instanceof Error ? reason.message : "读取设置失败");
        }
      })
      .finally(() => {
        if (!disposed) {
          setLoading(false);
        }
      });

    return () => {
      disposed = true;
      removeSizeChange?.();
      removeSizeSnapshot?.();
    };
  }, []);

  const handleAutoStartChange = async (enabled: boolean) => {
    setError("");
    try {
      if (enabled) {
        await enable();
      } else {
        await disable();
      }
      setAutoStart(enabled);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "更新开机启动失败");
    }
  };

  const handleSizeChange = (value: string) => {
    if (!sizeConfig) {
      return;
    }
    const next = normalizePercent(Number(value), sizeConfig);
    setSizePercent(next);
    window.localStorage.setItem(SIZE_STORAGE_KEY, String(next));
    void emit("pet-size-change", next).catch(() => undefined);
  };

  const close = () => {
    void getCurrentWindow().hide().catch(() => undefined);
  };

  if (loading || !sizeConfig) {
    return (
      <main className="settings-panel settings-panel-loading">
        <div className="settings-loader" aria-hidden="true" />
        <p className="settings-status">正在读取设置…</p>
      </main>
    );
  }

  return (
    <main className="settings-panel">
      <header className="settings-header">
        <div>
          <p className="settings-eyebrow">桌宠设置</p>
          <h1>桌宠控制面板</h1>
          <p className="settings-subtitle">调整桌宠的启动方式和显示大小</p>
        </div>
        <button
          className="settings-close"
          type="button"
          onClick={close}
          aria-label="关闭控制面板"
        >
          ×
        </button>
      </header>

      <section className="settings-card" aria-labelledby="startup-title">
        <div className="settings-card-copy">
          <div className="settings-card-icon" aria-hidden="true">↗</div>
          <div>
            <h2 id="startup-title">开机自动启动</h2>
            <p>登录 Windows 后自动显示桌宠</p>
          </div>
        </div>
        <label className="toggle">
          <span className="sr-only">开机自动启动</span>
          <input
            type="checkbox"
            checked={autoStart}
            onChange={(event) => void handleAutoStartChange(event.target.checked)}
          />
          <span className="toggle-track" aria-hidden="true" />
        </label>
      </section>

      <section className="settings-card settings-size-card" aria-labelledby="size-title">
        <div className="settings-size-heading">
          <div className="settings-card-copy">
            <div className="settings-card-icon" aria-hidden="true">◐</div>
            <div>
              <h2 id="size-title">桌宠大小</h2>
              <p>实时调整桌宠在屏幕上的显示比例</p>
            </div>
          </div>
          <strong className="size-value">{sizePercent}%</strong>
        </div>
        <input
          className="size-slider"
          type="range"
          min={sizeConfig.minPercent}
          max={sizeConfig.maxPercent}
          step={sizeConfig.stepPercent}
          value={sizePercent}
          onChange={(event) => handleSizeChange(event.target.value)}
          aria-label="桌宠大小"
        />
        <div className="size-scale" aria-hidden="true">
          <span>{sizeConfig.minPercent}%</span>
          <span>{sizeConfig.defaultPercent}% 默认</span>
          <span>{sizeConfig.maxPercent}%</span>
        </div>
        <div className="size-presets" role="group" aria-label="桌宠大小预设">
          {[50, 80, 100, 120].map((preset) => (
            <button
              key={preset}
              type="button"
              className={preset === sizePercent ? "preset active" : "preset"}
              onClick={() => handleSizeChange(String(preset))}
            >
              {preset}%
            </button>
          ))}
        </div>
      </section>

      {error ? <p className="settings-error" role="alert">{error}</p> : null}

      <footer className="settings-footer">
        <span>设置会立即生效</span>
        <button type="button" className="settings-primary" onClick={close}>
          完成
        </button>
      </footer>
    </main>
  );
}

async function readAutoStart(): Promise<boolean> {
  try {
    return await isEnabled();
  } catch {
    return false;
  }
}

function readStoredSizePercent(config: BehaviorConfig["size"]): number {
  const storedValue = window.localStorage.getItem(SIZE_STORAGE_KEY);
  const storedPercent = storedValue === null ? Number.NaN : Number(storedValue);
  return normalizePercent(
    Number.isFinite(storedPercent) ? storedPercent : config.defaultPercent,
    config,
  );
}

function normalizePercent(
  percent: number,
  config: BehaviorConfig["size"],
): number {
  if (!Number.isFinite(percent)) {
    return config.defaultPercent;
  }
  const clamped = Math.min(config.maxPercent, Math.max(config.minPercent, percent));
  const step = Math.max(1, config.stepPercent);
  const stepped =
    Math.round((clamped - config.minPercent) / step) * step + config.minPercent;
  return Math.min(config.maxPercent, Math.max(config.minPercent, stepped));
}

export default SettingsPanel;
