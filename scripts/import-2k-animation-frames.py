"""Normalize supplied 2K animation frames into Pixi @2x runtime assets."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


LOGICAL_FRAME_SIZE = (192, 208)
OUTPUT_FRAME_SIZE = (384, 416)
LOGICAL_CANVAS_SIZE = (220, 228)
OUTPUT_CANVAS_SIZE = (440, 456)
CANVAS_OFFSET = (14, 12)
TARGET_PET_CENTER_X = 96.0
TARGET_GROUND_BASELINE = 203


@dataclass(frozen=True)
class AnimationImport:
    source_directory: str
    output_directory: str
    frame_count: int
    alpha_floor: int = 0
    preserve_vertical_frames: tuple[int, ...] = ()


ANIMATIONS = (
    AnimationImport("touch_belly_ticklish_2k", "touch_belly_tickled", 16),
    AnimationImport(
        "touch_head_pat_bite_2k",
        "touch_head_pat_nip",
        20,
        preserve_vertical_frames=tuple(range(12, 19)),
    ),
    # The supplied push-away sequence contains a low-alpha background grid.
    # Remapping its alpha removes that contamination while preserving the
    # opaque character and hand artwork.
    AnimationImport(
        "touch_head_pat_push_away_2k",
        "touch_head_pat_push_away",
        20,
        alpha_floor=64,
    ),
)


def premultiplied_resize(image: Image.Image) -> np.ndarray:
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint16)
    alpha = rgba[:, :, 3:4]
    premultiplied = np.concatenate(
        ((rgba[:, :, :3] * alpha + 127) // 255, alpha), axis=2
    ).astype(np.uint8)
    resized = np.asarray(
        Image.fromarray(premultiplied, "RGBA").resize(
            OUTPUT_FRAME_SIZE, Image.Resampling.LANCZOS
        ),
        dtype=np.uint16,
    )
    resized_alpha = resized[:, :, 3:4]
    rgb = np.where(
        resized_alpha > 0,
        np.minimum(
            255,
            (resized[:, :, :3] * 255 + resized_alpha // 2)
            // np.maximum(resized_alpha, 1),
        ),
        0,
    )
    return np.concatenate((rgb, resized_alpha), axis=2).astype(np.uint8)


def remap_alpha(rgba: np.ndarray, floor: int) -> np.ndarray:
    result = rgba.copy()
    alpha = result[:, :, 3].astype(np.uint16)
    if floor > 0:
        alpha = np.where(
            alpha <= floor,
            0,
            ((alpha - floor) * 255 + (255 - floor) // 2) // (255 - floor),
        )
    alpha = np.clip(alpha, 0, 255).astype(np.uint8)
    result[:, :, 3] = alpha
    result[alpha == 0, :3] = 0
    return result


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    result = np.zeros_like(mask, dtype=bool)
    height, width = mask.shape
    for delta_y in range(-radius, radius + 1):
        for delta_x in range(-radius, radius + 1):
            target_y0 = max(0, delta_y)
            target_y1 = min(height, height + delta_y)
            source_y0 = max(0, -delta_y)
            source_y1 = min(height, height - delta_y)
            target_x0 = max(0, delta_x)
            target_x1 = min(width, width + delta_x)
            source_x0 = max(0, -delta_x)
            source_x1 = min(width, width - delta_x)
            result[target_y0:target_y1, target_x0:target_x1] |= mask[
                source_y0:source_y1, source_x0:source_x1
            ]
    return result


def largest_component(mask: np.ndarray) -> np.ndarray:
    height, width = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    largest: list[tuple[int, int]] = []

    for start_y, start_x in zip(*np.where(mask & ~seen)):
        stack = [(int(start_y), int(start_x))]
        seen[start_y, start_x] = True
        component: list[tuple[int, int]] = []
        while stack:
            y, x = stack.pop()
            component.append((y, x))
            for next_y, next_x in (
                (y - 1, x),
                (y + 1, x),
                (y, x - 1),
                (y, x + 1),
            ):
                if (
                    0 <= next_y < height
                    and 0 <= next_x < width
                    and mask[next_y, next_x]
                    and not seen[next_y, next_x]
                ):
                    seen[next_y, next_x] = True
                    stack.append((next_y, next_x))

        if len(component) > len(largest):
            largest = component

    result = np.zeros_like(mask, dtype=bool)
    for y, x in largest:
        result[y, x] = True
    return result


def measure_pet_anchor(rgba: np.ndarray) -> tuple[float, int]:
    logical = np.asarray(
        Image.fromarray(rgba, "RGBA").resize(
            LOGICAL_FRAME_SIZE, Image.Resampling.LANCZOS
        )
    )
    red = logical[:, :, 0].astype(np.int16)
    green = logical[:, :, 1].astype(np.int16)
    blue = logical[:, :, 2].astype(np.int16)
    alpha = logical[:, :, 3]

    skin = (
        (alpha > 32)
        & (red > 195)
        & (green > 125)
        & (green < 228)
        & (blue > 90)
        & (blue < 190)
        & ((red - green) > 15)
        & ((red - blue) > 35)
        & ((green - blue) < 90)
    )
    pet_component = largest_component((alpha > 48) & ~dilate(skin, 3))
    y_values, x_values = np.where(pet_component)
    if len(x_values) < 100:
        raise ValueError("Unable to identify a stable penguin component")
    return float(x_values.mean()), int(y_values.max() + 1)


def place_on_canvas(
    rgba: np.ndarray, delta_x: float, delta_y: float
) -> np.ndarray:
    canvas = Image.new("RGBA", OUTPUT_CANVAS_SIZE, (0, 0, 0, 0))
    x = CANVAS_OFFSET[0] * 2 + round(delta_x * 2)
    y = CANVAS_OFFSET[1] * 2 + round(delta_y * 2)
    canvas.alpha_composite(Image.fromarray(rgba, "RGBA"), (x, y))
    result = np.asarray(canvas).copy()
    result[result[:, :, 3] == 0, :3] = 0
    return result


def import_animation(
    source_root: Path, output_root: Path, specification: AnimationImport
) -> dict[str, object]:
    source_directory = source_root / specification.source_directory
    output_directory = output_root / specification.output_directory
    output_directory.mkdir(parents=True, exist_ok=True)

    source_files = sorted(source_directory.glob("frame_*.png"))
    if len(source_files) != specification.frame_count:
        raise ValueError(
            f"{specification.source_directory}: expected "
            f"{specification.frame_count} frames, found {len(source_files)}"
        )

    output_files: list[str] = []
    alignment: list[dict[str, float | int]] = []
    reference_vertical_offset: float | None = None
    for index, source_path in enumerate(source_files, start=1):
        with Image.open(source_path) as source_image:
            if source_image.size != (1890, 2048):
                raise ValueError(
                    f"{source_path}: expected 1890x2048, found {source_image.size}"
                )
            normalized_frame = remap_alpha(
                premultiplied_resize(source_image), specification.alpha_floor
            )
            pet_center_x, pet_baseline = measure_pet_anchor(normalized_frame)
            delta_x = TARGET_PET_CENTER_X - pet_center_x
            if reference_vertical_offset is None:
                reference_vertical_offset = TARGET_GROUND_BASELINE - pet_baseline
            delta_y = (
                reference_vertical_offset
                if index in specification.preserve_vertical_frames
                else TARGET_GROUND_BASELINE - pet_baseline
            )
            normalized = place_on_canvas(normalized_frame, delta_x, delta_y)

        output_path = output_directory / f"frame_{index:02d}@2x.webp"
        Image.fromarray(normalized, "RGBA").save(
            output_path,
            "WEBP",
            lossless=True,
            quality=100,
            method=4,
            exact=True,
        )
        output_files.append(output_path.name)
        alignment.append(
            {
                "frame": index,
                "sourcePetCenterX": round(pet_center_x, 3),
                "sourcePetBaseline": pet_baseline,
                "translateX": round(delta_x, 3),
                "translateY": round(delta_y, 3),
            }
        )

    return {
        "animation": specification.output_directory,
        "source": specification.source_directory,
        "frameCount": specification.frame_count,
        "sourceLogicalFrameSize": list(LOGICAL_FRAME_SIZE),
        "sourcePhysicalFrameSize": list(OUTPUT_FRAME_SIZE),
        "logicalFrameSize": list(LOGICAL_CANVAS_SIZE),
        "physicalFrameSize": list(OUTPUT_CANVAS_SIZE),
        "pixelRatio": 2,
        "alphaFloor": specification.alpha_floor,
        "alignment": alignment,
        "files": output_files,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("output_root", type=Path)
    arguments = parser.parse_args()

    manifest = {
        "version": 1,
        "sourceNote": (
            "Supplied 1890x2048 frames were upscaled from 192x208 source frames."
        ),
        "animations": [
            import_animation(arguments.source_root, arguments.output_root, item)
            for item in ANIMATIONS
        ],
    }
    manifest_path = arguments.output_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(manifest_path)


if __name__ == "__main__":
    main()
