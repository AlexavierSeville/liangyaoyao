import type { CharacterConfig } from "./types";
import characterConfig from "../config/character.json";

export async function loadCharacterConfig(): Promise<CharacterConfig> {
  return characterConfig as CharacterConfig;
}
