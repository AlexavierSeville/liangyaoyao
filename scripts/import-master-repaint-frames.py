"""Key baked checkerboards and normalize master-consistent repaint frames."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


SOURCE_SIZE = (1280, 1400)
INTERMEDIATE_SIZE = (384, 416)
OUTPUT_SIZE = (440, 456)
PIXEL_RATIO = 2
# The canonical front-facing master occupies roughly 149x198 logical pixels
# inside a 192x208 atlas cell.  The previous pass matched the old action
# references, which themselves were undersized.  Use the canonical body as a
# floor for upright action poses so replacement frames cannot silently shrink.
CANONICAL_BODY_WIDTH = 149
CANONICAL_BODY_HEIGHT = 198
COMPACT_POSE_HEIGHT_THRESHOLD = 150
COMPACT_POSE_SCALE_BIAS = 1.15
BODY_SCALE_BIAS_X = 1.02
BODY_SCALE_BIAS_Y = 1.02
OUTPUT_MARGIN = 4


@dataclass(frozen=True)
class AnimationImport:
    source_directory: str
    reference_directory: str
    output_directory: str
    frame_count: int


ANIMATIONS = (
    AnimationImport(
        "touch_belly_ticklish", "touch_belly_tickled", "touch_belly_tickled", 16
    ),
    AnimationImport(
        "touch_head_pat_bite", "touch_head_pat_nip", "touch_head_pat_nip", 20
    ),
    AnimationImport(
        "touch_head_pat_push_away",
        "touch_head_pat_push_away",
        "touch_head_pat_push_away",
        20,
    ),
)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def key_baked_checkerboard(image: Image.Image) -> np.ndarray:
    rgba = np.asarray(image.convert("RGBA")).copy()
    rgb = rgba[:, :, :3].astype(np.int16)
    alpha = rgba[:, :, 3]
    chroma = rgb.max(axis=2) - rgb.min(axis=2)

    # The supplied frames contain an opaque white/light-gray checkerboard.
    # Penguin cream, orange, brown, peach skin and dark motion marks all have
    # more chroma or lower luminance than this generated background.
    neutral_background = (rgb.min(axis=2) >= 135) & (chroma <= 12)
    foreground_core = (alpha > 0) & ~neutral_background

    # Restore tiny enclosed neutral highlights (for example eye glints) while
    # leaving the much larger checkerboard cells transparent.
    core_image = Image.fromarray(
        (foreground_core * 255).astype(np.uint8), mode="L"
    )
    closed_core = np.asarray(
        core_image.filter(ImageFilter.MaxFilter(9)).filter(
            ImageFilter.MinFilter(9)
        )
    ) > 0
    keep = foreground_core | (neutral_background & closed_core)

    rgba[~keep] = 0
    rgba[rgba[:, :, 3] == 0, :3] = 0
    return rgba


def premultiplied_resize(rgba: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    source = rgba.astype(np.uint16)
    alpha = source[:, :, 3:4]
    premultiplied = np.concatenate(
        ((source[:, :, :3] * alpha + 127) // 255, alpha), axis=2
    ).astype(np.uint8)
    resized = np.asarray(
        Image.fromarray(premultiplied, mode="RGBA").resize(
            size, Image.Resampling.LANCZOS
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
    result = np.concatenate((rgb, resized_alpha), axis=2).astype(np.uint8)
    result[result[:, :, 3] == 0, :3] = 0
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


def measure_pet_geometry(
    rgba: np.ndarray, logical_size: tuple[int, int]
) -> dict[str, float | int]:
    logical = np.asarray(
        Image.fromarray(rgba, mode="RGBA").resize(
            logical_size, Image.Resampling.LANCZOS
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
    component = largest_component((alpha > 48) & ~dilate(skin, 3))
    y_values, x_values = np.where(component)
    if len(x_values) < 100:
        raise ValueError("Unable to identify the penguin body component")
    left = int(x_values.min())
    top = int(y_values.min())
    right = int(x_values.max() + 1)
    bottom = int(y_values.max() + 1)
    return {
        "centerX": float(x_values.mean()),
        "baseline": bottom,
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": right - left,
        "height": bottom - top,
    }


def place_against_reference(
    repaint: np.ndarray, reference: np.ndarray
) -> tuple[np.ndarray, dict[str, float | int]]:
    repaint_geometry = measure_pet_geometry(repaint, (192, 208))
    reference_geometry = measure_pet_geometry(reference, (220, 228))

    # The old reference clips were generated from the same undersized pass,
    # so matching them preserved the very problem this import is meant to
    # fix.  Keep their pose-dependent width, but never let a normal upright
    # penguin be narrower than the canonical master.  For compressed/lying
    # poses preserve the deformation and only apply a modest lift instead of
    # stretching them into an upright silhouette.
    target_width = max(
        CANONICAL_BODY_WIDTH, int(reference_geometry["width"])
    )
    reference_height = int(reference_geometry["height"])
    if reference_height >= COMPACT_POSE_HEIGHT_THRESHOLD:
        target_height = CANONICAL_BODY_HEIGHT
    else:
        target_height = max(
            reference_height,
            round(reference_height * COMPACT_POSE_SCALE_BIAS),
        )

    scale_x = (
        float(target_width) / float(repaint_geometry["width"])
    ) * BODY_SCALE_BIAS_X
    scale_y = (
        float(target_height) / float(repaint_geometry["height"])
    ) * BODY_SCALE_BIAS_Y
    scaled_size = (
        max(1, round(repaint.shape[1] * scale_x)),
        max(1, round(repaint.shape[0] * scale_y)),
    )
    scaled = premultiplied_resize(repaint, scaled_size)
    # Enlarging the penguin to the canonical body size can make the raised
    # hand or motion marks exceed the 220x228 logical canvas. Fit the complete
    # processed silhouette before alignment rather than allowing hard crops.
    alpha_y, alpha_x = np.where(scaled[:, :, 3] > 32)
    if len(alpha_x) == 0:
        raise ValueError("Unable to place an empty repaint frame")
    scaled_alpha_width = int(alpha_x.max() - alpha_x.min() + 1)
    scaled_alpha_height = int(alpha_y.max() - alpha_y.min() + 1)
    fit_factor = min(
        1.0,
        float(OUTPUT_SIZE[0] - OUTPUT_MARGIN * 2) / scaled_alpha_width,
        float(OUTPUT_SIZE[1] - OUTPUT_MARGIN * 2) / scaled_alpha_height,
    )
    if fit_factor < 1.0:
        scaled = premultiplied_resize(
            scaled,
            (
                max(1, round(scaled.shape[1] * fit_factor)),
                max(1, round(scaled.shape[0] * fit_factor)),
            ),
        )
        scaled_size = (scaled.shape[1], scaled.shape[0])
    scaled_geometry = measure_pet_geometry(
        scaled, (round(scaled_size[0] / 2), round(scaled_size[1] / 2))
    )

    translate_x = round(
        (float(reference_geometry["centerX"]) - float(scaled_geometry["centerX"]))
        * PIXEL_RATIO
    )
    translate_y = round(
        (float(reference_geometry["baseline"]) - float(scaled_geometry["baseline"]))
        * PIXEL_RATIO
    )
    placed_y, placed_x = np.where(scaled[:, :, 3] > 32)
    left = int(placed_x.min() + translate_x)
    right = int(placed_x.max() + 1 + translate_x)
    top = int(placed_y.min() + translate_y)
    bottom = int(placed_y.max() + 1 + translate_y)
    if left < OUTPUT_MARGIN:
        translate_x += OUTPUT_MARGIN - left
    if right > OUTPUT_SIZE[0] - OUTPUT_MARGIN:
        translate_x -= right - (OUTPUT_SIZE[0] - OUTPUT_MARGIN)
    if top < OUTPUT_MARGIN:
        translate_y += OUTPUT_MARGIN - top
    if bottom > OUTPUT_SIZE[1] - OUTPUT_MARGIN:
        translate_y -= bottom - (OUTPUT_SIZE[1] - OUTPUT_MARGIN)
    canvas = Image.new("RGBA", OUTPUT_SIZE, (0, 0, 0, 0))
    canvas.alpha_composite(
        Image.fromarray(scaled, mode="RGBA"), (translate_x, translate_y)
    )
    result = np.asarray(canvas).copy()
    result[result[:, :, 3] == 0, :3] = 0
    return result, {
        "scaleX": round(scale_x, 5),
        "scaleY": round(scale_y, 5),
        "translateX": translate_x,
        "translateY": translate_y,
        "sourceBodyWidth": repaint_geometry["width"],
        "sourceBodyHeight": repaint_geometry["height"],
        "targetBodyWidth": target_width,
        "targetBodyHeight": target_height,
        "canonicalTargetBodyWidth": target_width,
        "canonicalTargetBodyHeight": target_height,
        "targetCenterX": round(float(reference_geometry["centerX"]), 3),
        "targetBaseline": reference_geometry["baseline"],
    }


def import_animation(
    source_root: Path,
    reference_root: Path,
    output_root: Path,
    specification: AnimationImport,
) -> dict[str, object]:
    source_directory = source_root / specification.source_directory
    reference_directory = reference_root / specification.reference_directory
    output_directory = output_root / specification.output_directory
    output_directory.mkdir(parents=True, exist_ok=True)
    source_files = sorted(source_directory.glob("frame_*.png"))
    if len(source_files) != specification.frame_count:
        raise ValueError(
            f"{source_directory}: expected {specification.frame_count} frames, "
            f"found {len(source_files)}"
        )

    records: list[dict[str, object]] = []
    for index, source_path in enumerate(source_files, start=1):
        reference_path = (
            reference_directory / f"frame_{index:02d}@2x.webp"
        )
        with Image.open(source_path) as source_image:
            if source_image.size != SOURCE_SIZE:
                raise ValueError(
                    f"{source_path}: expected {SOURCE_SIZE}, found {source_image.size}"
                )
            keyed = key_baked_checkerboard(source_image)
        normalized = premultiplied_resize(keyed, INTERMEDIATE_SIZE)
        with Image.open(reference_path) as reference_image:
            reference = np.asarray(reference_image.convert("RGBA"))
        output, alignment = place_against_reference(normalized, reference)

        output_path = output_directory / f"frame_{index:02d}@2x.webp"
        Image.fromarray(output, mode="RGBA").save(
            output_path,
            "WEBP",
            lossless=True,
            quality=100,
            method=4,
            exact=True,
        )
        records.append(
            {
                "frame": index,
                "source": source_path.name,
                "output": output_path.name,
                **alignment,
            }
        )

    return {
        "animation": specification.output_directory,
        "frameCount": specification.frame_count,
        "sourceSize": list(SOURCE_SIZE),
        "logicalOutputSize": [220, 228],
        "physicalOutputSize": list(OUTPUT_SIZE),
        "pixelRatio": PIXEL_RATIO,
        "frames": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("reference_root", type=Path)
    parser.add_argument("output_root", type=Path)
    arguments = parser.parse_args()

    manifest = {
        "version": 1,
        "source": "penguin_pet_master_consistent_repaint_1k_frames",
        "backgroundProcessing": {
            "type": "baked neutral checkerboard key",
            "minimumChannel": 135,
            "maximumChroma": 12,
            "smallHighlightClosingRadius": 4,
        },
        "bodyScaleLimits": {
            "horizontal": [0.9, 2.2],
            "vertical": [0.9, 2.2],
        },
        "bodyScaleBias": {
            "horizontal": BODY_SCALE_BIAS_X,
            "vertical": BODY_SCALE_BIAS_Y,
        },
        "canonicalBodyTarget": {
            "width": CANONICAL_BODY_WIDTH,
            "height": CANONICAL_BODY_HEIGHT,
            "compactPoseHeightThreshold": COMPACT_POSE_HEIGHT_THRESHOLD,
            "compactPoseScaleBias": COMPACT_POSE_SCALE_BIAS,
        },
        "animations": [
            import_animation(
                arguments.source_root,
                arguments.reference_root,
                arguments.output_root,
                item,
            )
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
