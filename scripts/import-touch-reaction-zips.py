"""Import supplied 1K touch reactions, retaining sequence order and both sides.

Uses the hatch-pet component extractor for deterministic matte cleanup only.
No images are generated. Source archives are kept unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path.home() / ".codex/skills/hatch-pet/scripts"
sys.path.insert(0, str(SKILL))
from extract_strip_frames import connected_components

CLIPS = (
    ("touch_belly_dislike", "touch_belly_dislike_1k_12frames.zip", "touch_belly_dislike_"),
    ("touch_flipper_react_screen_right", "touch_flipper_react_1k_24frames.zip", "screen_right/touch_flipper_react_screen_right_"),
    ("touch_flipper_react_screen_left", "touch_flipper_react_1k_24frames.zip", "screen_left/touch_flipper_react_screen_left_"),
)
OUTPUT_SIZE = (640, 456)
LOGICAL_SIZE = (320, 228)
TARGET_BODY_HEIGHT = 396  # 198 logical px, matching the authoritative idle.
TARGET_BASELINE = 430
TARGET_HEAD_CENTER_X = 318  # Idle head center is x=159 in the 320px viewport.


def extract(image: Image.Image) -> tuple[Image.Image, tuple[int, ...], dict]:
    rgba = np.array(image.convert("RGBA"))
    rgb = rgba[:, :, :3].astype(np.int16)
    # Flood only the light exterior. Closed dark contours protect the cream
    # belly and facial highlights; do not globally key similar body colours.
    light = (rgb.min(axis=2) > 185) & (rgb.max(axis=2) - rgb.min(axis=2) < 55)
    mask = Image.fromarray(np.where(light, 0, 255).astype(np.uint8))
    padded = Image.new("L", (mask.width + 2, mask.height + 2))
    padded.paste(mask, (1, 1))
    ImageDraw.floodfill(padded, (0, 0), 128)
    mask = np.array(padded)[1:-1, 1:-1] != 128
    rgba[:, :, 3] = np.where(mask, 255, 0)
    temporary = Image.fromarray(rgba)
    components = sorted(connected_components(temporary), key=lambda c: c["area"], reverse=True)
    body = components[0]
    # Preserve substantial hand components; omit supplied tiny motion marks.
    selected = [c for c in components if c["area"] >= body["area"] * 0.015]
    keep = np.zeros(image.width * image.height, dtype=bool)
    for component in selected:
        keep[component["pixels"]] = True
    rgba[~keep.reshape(mask.shape)] = 0
    return Image.fromarray(rgba), body["bbox"], {
        "bodyBoundsSource": body["bbox"],
        "keptComponents": len(selected),
        "removedSmallComponents": len(components) - len(selected),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=ROOT.parent)
    parser.add_argument("--qa-dir", type=Path, default=ROOT / "docs/touch-recovery-2026-09-08")
    args = parser.parse_args()
    args.qa_dir.mkdir(parents=True, exist_ok=True)
    report = {"method": "exterior-flood-fill, hatch-pet components, shared sequence scale", "clips": {}}
    for clip, archive_name, prefix in CLIPS:
        archive_path = args.source_root / archive_name
        decoded = []
        with zipfile.ZipFile(archive_path) as archive:
            for index in range(1, 13):
                name = f"{prefix}{index:02d}.png"
                image = Image.open(io.BytesIO(archive.read(name))).convert("RGBA")
                result, bounds, metrics = extract(image)
                decoded.append((result, bounds, {"source": name, **metrics}))
        # One isotropic scale for the whole action, based on neutral body
        # height. Do not normalize individual frames, which would erase motion.
        first_bounds = decoded[0][1]
        scale = TARGET_BODY_HEIGHT / (first_bounds[3] - first_bounds[1])
        head_top = first_bounds[1]
        head_bottom = head_top + round((first_bounds[3] - head_top) * 0.35)
        head = decoded[0][0].crop((0, head_top, decoded[0][0].width, head_bottom))
        head_bounds = max(connected_components(head), key=lambda c: c["area"])["bbox"]
        center = (head_bounds[0] + head_bounds[2]) / 2
        baseline = first_bounds[3]
        # The bird determines scale. The viewport provides room for hands;
        # never shrink the bird to satisfy a canvas-fit constraint.
        output = ROOT / "public/assets/animations/hd" / clip
        output.mkdir(parents=True, exist_ok=True)
        frames = []
        metrics_list = []
        for index, (source, bounds, metrics) in enumerate(decoded, 1):
            # Common source transform retains the original lean, kick and
            # hand movement. Bottom offset matches the legacy idle baseline.
            cropped_bounds = source.getbbox()
            cropped = source.crop(cropped_bounds)
            size = (round(cropped.width * scale), round(cropped.height * scale))
            resized = cropped.resize(size, Image.Resampling.LANCZOS)
            x = round(TARGET_HEAD_CENTER_X + (cropped_bounds[0] - center) * scale)
            y = round(TARGET_BASELINE + (cropped_bounds[1] - baseline) * scale)
            if x < 4 or y < 4 or x + size[0] > OUTPUT_SIZE[0] - 4 or y + size[1] > OUTPUT_SIZE[1] - 4:
                raise ValueError(f"{clip} frame {index}: transformed sprite clips the canvas {(x,y,size)}")
            frame = Image.new("RGBA", OUTPUT_SIZE)
            frame.alpha_composite(resized, (x, y))
            pixels = np.array(frame)
            pixels[pixels[:, :, 3] == 0, :3] = 0
            frame = Image.fromarray(pixels)
            frame.save(output / f"frame_{index:02d}@2x.webp", lossless=True, exact=True)
            frames.append(frame)
            metrics_list.append({**metrics, "outputBounds": frame.getbbox()})
        sheet = Image.new("RGB", (6 * LOGICAL_SIZE[0], 2 * 256), "#d4dedc")
        draw = ImageDraw.Draw(sheet)
        previews = []
        for i, frame in enumerate(frames):
            small = frame.resize(LOGICAL_SIZE, Image.Resampling.LANCZOS)
            x, y = i % 6 * LOGICAL_SIZE[0], i // 6 * 256
            sheet.paste(small, (x, y + 22), small)
            draw.text((x + 8, y + 4), f"{i+1:02d}", fill="black")
            preview = Image.new("RGB", LOGICAL_SIZE, "#d4dedc")
            preview.paste(small, (0, 0), small)
            previews.append(preview)
        sheet.save(args.qa_dir / f"{clip}-contact.png")
        previews[0].save(args.qa_dir / f"{clip}-preview.gif", save_all=True, append_images=previews[1:], duration=125, loop=0)
        report["clips"][clip] = {"archive": archive_name, "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(), "frameCount": 12, "scale": scale, "neutralBodyHeightLogical": TARGET_BODY_HEIGHT / 2, "frameSize": OUTPUT_SIZE, "frames": metrics_list}
        print(f"Imported {clip}: 12 frames, shared scale {scale:.4f}", flush=True)
    (args.qa_dir / "import-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
