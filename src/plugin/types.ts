export interface PetPluginContext {
  readonly characterId: string;
}

export interface PetPlugin {
  readonly id: string;
  activate(context: PetPluginContext): void | Promise<void>;
  deactivate?(): void | Promise<void>;
}
