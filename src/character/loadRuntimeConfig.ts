import runtimeConfig from "../config/runtime.json";
import type { RuntimeConfig } from "./runtimeTypes";

export async function loadRuntimeConfig(): Promise<RuntimeConfig> {
  return runtimeConfig as RuntimeConfig;
}
