export interface RuntimeConfig {
  renderer: {
    maxFps: number;
    minFps: number;
    resolutionCap: number;
    preference: "webgl" | "webgpu";
  };
}
