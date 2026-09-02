import { Application } from "pixi.js";
import type { RuntimeConfig } from "../character/runtimeTypes";
import type { CharacterConfig } from "../character/types";
import type { AnimationCatalog, AnimationCompletionListener } from "./types";
import { SpriteSheetAnimationPlayer } from "./SpriteSheetAnimationPlayer";

/** Owns the Pixi application and exposes only pet-rendering operations. */
export class PixiPetRuntime {
  private constructor(
    private readonly app: Application,
    private readonly player: SpriteSheetAnimationPlayer,
    private readonly character: CharacterConfig,
  ) {}

  public static async create(
    host: HTMLElement,
    character: CharacterConfig,
    catalog: AnimationCatalog,
    runtime: RuntimeConfig,
    scale: number,
  ): Promise<PixiPetRuntime> {
    const app = new Application();
    try {
      await app.init({
        width: character.canvas.width * scale,
        height: character.canvas.height * scale,
        backgroundAlpha: 0,
        antialias: true,
        autoDensity: true,
        roundPixels: runtime.renderer.roundPixels,
        resolution: Math.min(
          window.devicePixelRatio || 1,
          runtime.renderer.resolutionCap,
        ),
        preference: runtime.renderer.preference,
      });

      const player = new SpriteSheetAnimationPlayer(
        runtime.renderer.roundPixels,
      );
      player.position.set(character.sprite.x * scale, character.sprite.y * scale);
      player.scale.set(character.sprite.scale * scale);
      app.stage.addChild(player);
      app.ticker.maxFPS = runtime.renderer.maxFps;
      app.ticker.minFPS = runtime.renderer.minFps;
      app.ticker.add((ticker) => player.update(ticker.deltaMS));

      await Promise.all(
        Object.values(catalog.animations).map((animation) => player.load(animation)),
      );
      host.appendChild(app.canvas);
      return new PixiPetRuntime(app, player, character);
    } catch (error) {
      app.destroy(true);
      throw error;
    }
  }

  public play(animationId: string): void {
    this.player.play(animationId);
  }

  public resize(width: number, height: number, scale: number): void {
    this.app.renderer.resize(width, height);
    this.player.position.set(
      this.character.sprite.x * scale,
      this.character.sprite.y * scale,
    );
    this.player.scale.set(this.character.sprite.scale * scale);
  }

  public onAnimationComplete(listener: AnimationCompletionListener): () => void {
    return this.player.onComplete(listener);
  }

  public dispose(): void {
    this.app.ticker.stop();
    this.player.dispose();
    this.app.destroy(true);
  }
}
