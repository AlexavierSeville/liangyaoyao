"""Validate animation frame geometry against character-spec.json."""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "src/config/character-spec.json"
DEFAULT_ASSETS = (
    ROOT / "public/assets/animations/touch_head_pat.webp",
    ROOT / "public/assets/animations/touch_head_pat_start.webp",
    ROOT / "public/assets/animations/touch_head_pat_loop.webp",
    ROOT / "public/assets/animations/touch_head_pat_end.webp",
    ROOT / "public/assets/animations/touch_head_pat_push_away.webp",
)


def alpha_bbox(frame: Image.Image, threshold: int) -> tuple[int, int, int, int]:
    mask = frame.getchannel("A").point(
        lambda value: 255 if value > threshold else 0
    )
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("frame is fully transparent")
    return bbox


def character_bbox(
    frame: Image.Image,
    threshold: int,
) -> tuple[int, int, int, int]:
    pixels = frame.load()
    visited: set[tuple[int, int]] = set()
    largest: list[tuple[int, int]] = []
    for y in range(frame.height):
        for x in range(frame.width):
            red, green, blue, alpha = pixels[x, y]
            if (x, y) in visited or not (
                alpha > threshold
                and red < 140
                and green < 125
                and blue < 110
                and red - green < 35
                and green - blue < 30
            ):
                continue
            component: list[tuple[int, int]] = []
            pending = [(x, y)]
            visited.add((x, y))
            while pending:
                current_x, current_y = pending.pop()
                component.append((current_x, current_y))
                for next_x, next_y in (
                    (current_x - 1, current_y),
                    (current_x + 1, current_y),
                    (current_x, current_y - 1),
                    (current_x, current_y + 1),
                ):
                    point = (next_x, next_y)
                    if point in visited or not (
                        0 <= next_x < frame.width
                        and 0 <= next_y < frame.height
                    ):
                        continue
                    next_red, next_green, next_blue, next_alpha = pixels[point]
                    if (
                        next_alpha > threshold
                        and next_red < 140
                        and next_green < 125
                        and next_blue < 110
                        and next_red - next_green < 35
                        and next_green - next_blue < 30
                    ):
                        visited.add(point)
                        pending.append(point)
            if len(component) > len(largest):
                largest = component
    if not largest:
        raise ValueError("frame has no detectable charcoal body pixels")
    return (
        min(x for x, _ in largest),
        min(y for _, y in largest),
        max(x for x, _ in largest) + 1,
        max(y for _, y in largest) + 1,
    )


def feet_center(frame: Image.Image, threshold: int) -> float:
    """Use the stable grounded anchor for non-airborne animation clips."""
    pixels = frame.load()
    foot_points = []
    for y in range(round(frame.height * 0.75), frame.height):
        for x in range(frame.width):
            red, green, blue, alpha = pixels[x, y]
            if (
                alpha > threshold
                and red > 170
                and 50 < green < 190
                and blue < 110
            ):
                foot_points.append((x, y))
    if not foot_points:
        raise ValueError("frame has no detectable orange feet")
    return (min(x for x, _ in foot_points) + max(x for x, _ in foot_points)) / 2


def validate(
    asset: Path,
    spec_path: Path,
    allow_vertical_motion: bool = False,
    dynamic_frame_indices: set[int] | None = None,
) -> bool:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    canvas = spec["canvas"]
    validation = spec["validation"]
    threshold = spec["measurementMethod"]["alphaThreshold"]
    frame_width = canvas["widthPx"]
    frame_height = canvas["heightPx"]
    target_top = canvas["standardVisibleBoundsPx"]["top"]
    target_baseline = canvas["baseline"]["feetLastOpaqueRowPx"]
    baseline_tolerance = canvas["baseline"]["tolerancePx"]
    target_center = canvas["anchor"]["pixel"]["x"]
    center_tolerance = spec["animationConstraints"]["bodyCenterTolerancePx"]
    top_tolerance = spec["animationConstraints"]["headTopTolerancePx"]
    min_height = 194
    max_height = 202
    min_width = 140
    max_width = 165

    with Image.open(asset) as source:
        sheet = source.convert("RGBA")
        if sheet.height != frame_height or sheet.width % frame_width != 0:
            print(
                f"FAIL sheet size {sheet.size}; expected Nx{frame_width} by {frame_height}"
            )
            return False

        frame_count = sheet.width // frame_width
        print(f"asset={asset}")
        print(f"spec={spec_path}")
        print(f"frames={frame_count} frameSize={frame_width}x{frame_height}")
        print(
            "frame bbox top bottom bboxCenter bodyCenter width height "
            "bodyTop bodyHeight baseline center status"
        )

        passed = True
        for index in range(frame_count):
            frame = sheet.crop(
                (
                    index * frame_width,
                    0,
                    (index + 1) * frame_width,
                    frame_height,
                )
            )
            left, top, right, bottom = alpha_bbox(frame, threshold)
            bottom_y = bottom - 1
            bbox_center = (left + right - 1) / 2
            body_left, body_top, body_right, _ = character_bbox(frame, threshold)
            body_center = (
                (body_left + body_right - 1) / 2
                if allow_vertical_motion
                else feet_center(frame, threshold)
            )
            width = right - left
            height = bottom - top
            body_height = bottom - body_top

            baseline_ok = allow_vertical_motion or abs(bottom_y - target_baseline) <= baseline_tolerance
            center_ok = abs(body_center - target_center) <= center_tolerance
            top_ok = allow_vertical_motion or abs(body_top - target_top) <= top_tolerance
            height_ok = min_height <= body_height <= max_height
            width_ok = min_width <= width <= max_width
            dynamic_pose = (
                dynamic_frame_indices is not None
                and index in dynamic_frame_indices
            )
            hard_height_ok = height_ok or dynamic_pose
            hard_ok = baseline_ok and center_ok and top_ok and hard_height_ok
            passed = passed and hard_ok

            checks = [
                f"baseline={'motion-ok' if allow_vertical_motion else ('ok' if baseline_ok else 'FAIL')}",
                f"center={'ok' if center_ok else 'FAIL'}",
                f"top={'motion-ok' if allow_vertical_motion else ('ok' if top_ok else 'FAIL')}",
                f"height={'pose-ok' if dynamic_pose else ('ok' if height_ok else 'FAIL')}",
                f"width={'ok' if width_ok else 'warn'}",
            ]
            print(
                f"{index + 1:>5} ({left},{top},{right},{bottom}) "
                f"{top:>3} {bottom_y:>6} {bbox_center:>10.1f} "
                f"{body_center:>10.1f} {width:>5} {height:>6} "
                f"{body_top:>7} {body_height:>10} {bottom_y:>8} "
                f"{body_center:>6.1f} {' '.join(checks)}"
            )

    if passed:
        print("PASS character consistency")
    else:
        print("FAIL character consistency")
    return passed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("assets", nargs="*", type=Path, default=list(DEFAULT_ASSETS))
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument(
        "--allow-vertical-motion",
        action="store_true",
        help="Allow intentional jump offsets while still checking body height and center",
    )
    args = parser.parse_args()
    passed = True
    for asset in args.assets:
        if not asset.exists():
            print(f"FAIL missing asset: {asset}")
            passed = False
            continue
        is_jump_nip = asset.name == "touch_head_pat_nip.webp"
        allow_vertical_motion = args.allow_vertical_motion or is_jump_nip
        dynamic_frames = set(range(2, 12)) if is_jump_nip else None
        passed = validate(
            asset,
            args.spec,
            allow_vertical_motion,
            dynamic_frames,
        ) and passed
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
