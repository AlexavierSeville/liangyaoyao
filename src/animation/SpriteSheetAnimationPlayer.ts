import { Assets, Container, Rectangle, Sprite, Texture } from "pixi.js";
import type {
  AnimationCompletionListener,
  AnimationConfig,
} from "./types";

interface LoadedAnimation {
  config: AnimationConfig;
  frames: Texture[];
  ownsFrames: boolean;
}

/** Plays any configured row in a sprite sheet without knowing the character's actions. */
export class SpriteSheetAnimationPlayer extends Container {
  private readonly sprite = new Sprite();
  private readonly loadedAnimations = new Map<string, LoadedAnimation>();
  private readonly completionListeners = new Set<AnimationCompletionListener>();
  private current: LoadedAnimation | null = null;
  private currentFrame = 0;
  private elapsedMs = 0;
  private playing = false;

  public constructor() {
    super();
    this.addChild(this.sprite);
  }

  public async load(config: AnimationConfig): Promise<void> {
    if (config.sourceType === "sprite") {
      if (!config.files || config.files.length !== config.frames) {
        throw new Error(`Sprite frame list does not match frame count: ${config.id}`);
      }
      const frames = await Promise.all(
        config.files.map((file) => Assets.load<Texture>(file)),
      );
      this.loadedAnimations.set(config.id, {
        config,
        frames,
        ownsFrames: false,
      });
      return;
    }

    if (!config.file) {
      throw new Error(`Sprite sheet file is missing: ${config.id}`);
    }

    const sourceTexture = await Assets.load<Texture>(config.file);
    const columns =
      config.sheetColumns ?? Math.floor(sourceTexture.width / config.frameWidth);
    const startFrame = config.startFrame ?? 0;

    if (columns < 1 || config.frames < 1 || config.fps <= 0) {
      throw new Error(`Invalid animation configuration: ${config.id}`);
    }

    const frames: Texture[] = [];
    for (let index = 0; index < config.frames; index += 1) {
      const absoluteFrame = startFrame + index;
      const column = absoluteFrame % columns;
      const row = config.sheetRow + Math.floor(absoluteFrame / columns);
      const frame = new Rectangle(
        column * config.frameWidth,
        row * config.frameHeight,
        config.frameWidth,
        config.frameHeight,
      );
      frames.push(new Texture({ source: sourceTexture.source, frame }));
    }

    this.loadedAnimations.set(config.id, { config, frames, ownsFrames: true });
  }

  public play(animationId: string): void {
    const animation = this.loadedAnimations.get(animationId);
    if (!animation) {
      throw new Error(`Animation is not loaded: ${animationId}`);
    }

    this.current = animation;
    this.currentFrame = 0;
    this.elapsedMs = 0;
    this.playing = true;
    this.sprite.anchor.set(animation.config.anchor?.x ?? 0.5, animation.config.anchor?.y ?? 1);
    this.sprite.texture = animation.frames[0];
  }

  public stop(): void {
    this.playing = false;
  }

  public get currentAnimationId(): string | null {
    return this.current?.config.id ?? null;
  }

  public get isPlaying(): boolean {
    return this.playing;
  }

  public update(deltaMs: number): void {
    if (!this.playing || !this.current) {
      return;
    }

    const frameDuration = 1000 / this.current.config.fps;
    this.elapsedMs += Math.max(0, deltaMs);

    while (this.elapsedMs >= frameDuration && this.playing) {
      this.elapsedMs -= frameDuration;
      const nextFrame = this.currentFrame + 1;

      if (nextFrame < this.current.frames.length) {
        this.currentFrame = nextFrame;
        this.sprite.texture = this.current.frames[this.currentFrame];
        continue;
      }

      const completedAnimation: LoadedAnimation = this.current;
      for (const listener of this.completionListeners) {
        listener(completedAnimation.config.id);
      }

      if (this.current !== completedAnimation) {
        continue;
      }

      if (completedAnimation.config.loop) {
        this.currentFrame = 0;
        this.sprite.texture = completedAnimation.frames[0];
      } else {
        this.currentFrame = completedAnimation.frames.length - 1;
        this.playing = false;
      }
    }
  }

  public onComplete(listener: AnimationCompletionListener): () => void {
    this.completionListeners.add(listener);
    return () => this.completionListeners.delete(listener);
  }

  public dispose(): void {
    for (const animation of this.loadedAnimations.values()) {
      if (animation.ownsFrames) {
        for (const frame of animation.frames) {
          frame.destroy(false);
        }
      }
    }
    this.loadedAnimations.clear();
    this.completionListeners.clear();
  }
}
