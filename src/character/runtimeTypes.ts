export interface RuntimeConfig {
  animationTestKeys: {
    enabled: boolean;
  };
  renderer: {
    maxFps: number;
    minFps: number;
    resolutionCap: number;
    roundPixels: boolean;
    preference: "webgl" | "webgpu";
  };
}
