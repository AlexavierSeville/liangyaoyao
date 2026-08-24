"""Prepare canonical references and normalize generated head-pat animation sheets."""

import argparse
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "src/config/character-spec.json"
ATLAS_PATH = ROOT / "public/assets/animations/liangyaoyao-v2.webp"
IDLE_BREATHE_PATH = ROOT / "public/assets/animations/idle_breathe.webp"
IDLE_BLINK_PATH = ROOT / "public/assets/animations/idle_blink.webp"
FRAME_WIDTH = 192
FRAME_HEIGHT = 208
ALPHA_THRESHOLD = 12
MIN_COMPONENT_PIXELS = 80


def crop_frame(sheet: Image.Image, index: int) -> Image.Image:
    return sheet.crop(
        (index * FRAME_WIDTH, 0, (index + 1) * FRAME_WIDTH, FRAME_HEIGHT)
    )


def build_reference_board(output: Path) -> None:
    """Build a clean 2x2 board using only canonical, pre-head-pat assets."""
    with Image.open(ATLAS_PATH) as source:
        atlas = source.convert("RGBA")
        standard = atlas.crop((0, 0, FRAME_WIDTH, FRAME_HEIGHT))
        closed = atlas.crop((3 * FRAME_WIDTH, 0, 4 * FRAME_WIDTH, FRAME_HEIGHT))
    with Image.open(IDLE_BREATHE_PATH) as source:
        breathe = crop_frame(source.convert("RGBA"), 4)
    with Image.open(IDLE_BLINK_PATH) as source:
        blink = crop_frame(source.convert("RGBA"), 1)

    board = Image.new(
        "RGBA", (FRAME_WIDTH * 2, FRAME_HEIGHT * 2), (0, 0, 0, 0)
    )
    for index, frame in enumerate((standard, closed, breathe, blink)):
        board.alpha_composite(
            frame,
            ((index % 2) * FRAME_WIDTH, (index // 2) * FRAME_HEIGHT),
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    board.save(output, format="PNG")


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    mask = image.getchannel("A").point(
        lambda value: 255 if value > ALPHA_THRESHOLD else 0
    )
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("Panel has no visible pixels")
    return bbox


def is_charcoal(red: int, green: int, blue: int, alpha: int) -> bool:
    return (
        alpha > ALPHA_THRESHOLD
        and red < 140
        and green < 125
        and blue < 110
        and red - green < 35
        and green - blue < 30
    )


def character_bbox(panel: Image.Image) -> tuple[int, int, int, int]:
    pixels = panel.load()
    visited: set[tuple[int, int]] = set()
    largest: list[tuple[int, int]] = []
    for y in range(panel.height):
        for x in range(panel.width):
            if (x, y) in visited or not is_charcoal(*pixels[x, y]):
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
                    if (
                        0 <= next_x < panel.width
                        and 0 <= next_y < panel.height
                        and point not in visited
                        and is_charcoal(*pixels[next_x, next_y])
                    ):
                        visited.add(point)
                        pending.append(point)
            if len(component) > len(largest):
                largest = component
    if not largest:
        raise ValueError("Panel has no detectable charcoal body")
    return (
        min(x for x, _ in largest),
        min(y for _, y in largest),
        max(x for x, _ in largest) + 1,
        max(y for _, y in largest) + 1,
    )


def character_top(panel: Image.Image) -> int:
    return character_bbox(panel)[1]


def foot_bounds(panel: Image.Image) -> tuple[int, int, int, int]:
    pixels = panel.load()
    _, body_top, _, body_bottom = character_bbox(panel)
    body_height = body_bottom - body_top
    minimum_foot_y = body_top + round(body_height * 0.55)
    # Airborne/crouched reaction frames can place the feet much farther below
    # the main charcoal body component than neutral standing frames. Keep the
    # color/component checks strict, but search a taller vertical window so the
    # canonical two orange feet are still found during a jump.
    maximum_foot_y = body_bottom + round(body_height * 0.55)
    orange_points: set[tuple[int, int]] = set()
    for y in range(max(0, minimum_foot_y), min(panel.height, maximum_foot_y)):
        for x in range(panel.width):
            red, green, blue, alpha = pixels[x, y]
            if (
                alpha > 20
                and red > 170
                and 50 < green < 200
                and blue < 130
            ):
                orange_points.add((x, y))
    components: list[list[tuple[int, int]]] = []
    while orange_points:
        first = orange_points.pop()
        component = [first]
        pending = [first]
        while pending:
            current_x, current_y = pending.pop()
            for next_x, next_y in (
                (current_x - 1, current_y),
                (current_x + 1, current_y),
                (current_x, current_y - 1),
                (current_x, current_y + 1),
                (current_x - 1, current_y - 1),
                (current_x + 1, current_y - 1),
                (current_x - 1, current_y + 1),
                (current_x + 1, current_y + 1),
            ):
                point = (next_x, next_y)
                if point in orange_points:
                    orange_points.remove(point)
                    component.append(point)
                    pending.append(point)
        if len(component) >= 20:
            components.append(component)
    if len(components) < 2:
        raise ValueError("Panel has no detectable orange feet")
    components.sort(key=len, reverse=True)
    selected = components[:2]
    points = selected[0] + selected[1]
    return (
        min(x for x, _ in points),
        min(y for _, y in points),
        max(x for x, _ in points) + 1,
        max(y for _, y in points) + 1,
    )


def remove_small_components(frame: Image.Image) -> None:
    alpha = frame.getchannel("A")
    pixels = alpha.load()
    visited: set[tuple[int, int]] = set()

    for y in range(frame.height):
        for x in range(frame.width):
            if pixels[x, y] <= ALPHA_THRESHOLD or (x, y) in visited:
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
                    (current_x - 1, current_y - 1),
                    (current_x + 1, current_y - 1),
                    (current_x - 1, current_y + 1),
                    (current_x + 1, current_y + 1),
                ):
                    point = (next_x, next_y)
                    if (
                        0 <= next_x < frame.width
                        and 0 <= next_y < frame.height
                        and point not in visited
                        and pixels[next_x, next_y] > ALPHA_THRESHOLD
                    ):
                        visited.add(point)
                        pending.append(point)
            if len(component) < MIN_COMPONENT_PIXELS:
                for component_x, component_y in component:
                    frame.putpixel((component_x, component_y), (0, 0, 0, 0))


def clear_near_transparent_pixels(frame: Image.Image) -> None:
    """Remove generated hidden-RGB noise from effectively transparent pixels."""
    pixels = frame.load()
    for y in range(frame.height):
        for x in range(frame.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha <= ALPHA_THRESHOLD:
                pixels[x, y] = (0, 0, 0, 0)


def align_final_baseline(frame: Image.Image, baseline_y: int) -> Image.Image:
    _, _, _, bottom = alpha_bbox(frame)
    offset_y = baseline_y - (bottom - 1)
    if offset_y == 0:
        return frame
    aligned = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    aligned.alpha_composite(frame, (0, offset_y))
    return aligned


def normalize(
    source: Path,
    output_path: Path,
    frame_count: int,
    grid_columns: int,
    grid_rows: int,
    vertical_offsets: list[int] | None = None,
    uniform_scale: bool = False,
) -> None:
    if frame_count > grid_columns * grid_rows:
        raise ValueError("Frame count exceeds the source grid capacity")
    if vertical_offsets is not None and len(vertical_offsets) != frame_count:
        raise ValueError("Vertical offset count must match frame count")
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    target_top = spec["canvas"]["standardVisibleBoundsPx"]["top"]
    target_center_x = spec["canvas"]["anchor"]["pixel"]["x"]
    target_baseline_y = spec["canvas"]["baseline"]["feetLastOpaqueRowPx"]
    target_body_height = target_baseline_y - target_top + 1

    with Image.open(source) as original:
        image = original.convert("RGBA")
        alpha_min, _ = image.getchannel("A").getextrema()
        if alpha_min > ALPHA_THRESHOLD:
            raise ValueError(
                "Generated source has no transparent background; regenerate with alpha"
            )
        output = Image.new(
            "RGBA", (FRAME_WIDTH * frame_count, FRAME_HEIGHT), (0, 0, 0, 0)
        )
        panel_width = image.width / grid_columns
        panel_height = image.height / grid_rows
        vertical_overlap = 0 if uniform_scale else round(panel_height * 0.12)

        reference_scale: float | None = None
        if uniform_scale:
            reference_panel = image.crop(
                (0, 0, round(panel_width), round(panel_height))
            )
            reference_body_top = character_top(reference_panel)
            _, _, _, reference_foot_bottom = foot_bounds(reference_panel)
            reference_body_height = reference_foot_bottom - reference_body_top
            reference_scale = target_body_height / reference_body_height

        for index in range(frame_count):
            column = index % grid_columns
            row = index // grid_columns
            panel = image.crop(
                (
                    round(column * panel_width),
                    max(0, round(row * panel_height) - vertical_overlap),
                    round((column + 1) * panel_width),
                    min(
                        image.height,
                        round((row + 1) * panel_height) + vertical_overlap,
                    ),
                )
            )
            alpha_bbox(panel)
            body_left, body_top, body_right, _ = character_bbox(panel)
            foot_left, _, foot_right, foot_bottom = foot_bounds(panel)
            source_body_height = foot_bottom - body_top
            scale = (
                reference_scale
                if reference_scale is not None
                else target_body_height / source_body_height
            )
            source_center_x = (
                (body_left + body_right - 1) / 2
                if uniform_scale
                else (foot_left + foot_right - 1) / 2
            )
            resized = panel.resize(
                (round(panel.width * scale), round(panel.height * scale)),
                Image.Resampling.LANCZOS,
            )
            frame = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (0, 0, 0, 0))
            destination_x = round(target_center_x - source_center_x * scale)
            destination_y = round(target_baseline_y - (foot_bottom - 1) * scale)
            frame.alpha_composite(resized, (destination_x, destination_y))
            clear_near_transparent_pixels(frame)
            remove_small_components(frame)
            frame = align_final_baseline(frame, target_baseline_y)
            if vertical_offsets is not None and vertical_offsets[index] != 0:
                shifted = Image.new("RGBA", frame.size, (0, 0, 0, 0))
                shifted.alpha_composite(frame, (0, vertical_offsets[index]))
                frame = shifted
            output.alpha_composite(frame, (index * FRAME_WIDTH, 0))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output.save(output_path, format="WEBP", lossless=True, quality=100, method=6)


def compose_one_shot(start: Path, end: Path, output: Path) -> None:
    """Build the short-click clip from four start and four recovery frames."""
    with Image.open(start) as source:
        start_sheet = source.convert("RGBA")
    with Image.open(end) as source:
        end_sheet = source.convert("RGBA")
    if start_sheet.height != FRAME_HEIGHT or end_sheet.height != FRAME_HEIGHT:
        raise ValueError("Input sheets must use the canonical frame height")
    start_count = start_sheet.width // FRAME_WIDTH
    end_count = end_sheet.width // FRAME_WIDTH
    if start_count < 4 or end_count < 4:
        raise ValueError("Start and end sheets need at least four frames")

    selected = [
        crop_frame(start_sheet, index)
        for index in (0, 1, start_count - 2, start_count - 1)
    ]
    selected.extend(
        crop_frame(end_sheet, index)
        for index in (0, 1, end_count - 2, end_count - 1)
    )
    sheet = Image.new(
        "RGBA", (FRAME_WIDTH * len(selected), FRAME_HEIGHT), (0, 0, 0, 0)
    )
    for index, frame in enumerate(selected):
        sheet.alpha_composite(frame, (index * FRAME_WIDTH, 0))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="WEBP", lossless=True, quality=100, method=6)


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    reference_parser = subparsers.add_parser("reference")
    reference_parser.add_argument("output", type=Path)

    normalize_parser = subparsers.add_parser("normalize")
    normalize_parser.add_argument("source", type=Path)
    normalize_parser.add_argument("output", type=Path)
    normalize_parser.add_argument("--frames", type=int, required=True)
    normalize_parser.add_argument("--columns", type=int, required=True)
    normalize_parser.add_argument("--rows", type=int, required=True)
    normalize_parser.add_argument(
        "--vertical-offsets",
        type=lambda value: [int(item) for item in value.split(",")],
        default=None,
        help="Optional per-frame y offsets; negative values move the frame upward",
    )
    normalize_parser.add_argument(
        "--uniform-scale",
        action="store_true",
        help=(
            "Use frame 1's canonical scale for every frame so crouch/jump poses "
            "are not individually stretched back to standing height"
        ),
    )

    compose_parser = subparsers.add_parser("compose")
    compose_parser.add_argument("start", type=Path)
    compose_parser.add_argument("end", type=Path)
    compose_parser.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "reference":
        build_reference_board(args.output)
    elif args.command == "normalize":
        normalize(
            args.source,
            args.output,
            args.frames,
            args.columns,
            args.rows,
            args.vertical_offsets,
            args.uniform_scale,
        )
    else:
        compose_one_shot(args.start, args.end, args.output)


if __name__ == "__main__":
    main()
