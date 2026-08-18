export interface CharacterConfig {
  id: string;
  name: string;
  description: string;
  canvas: {
    width: number;
    height: number;
  };
  sprite: {
    x: number;
    y: number;
    scale: number;
  };
  defaultAnimation: string;
}
