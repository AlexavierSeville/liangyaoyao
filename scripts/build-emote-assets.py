from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/assets/animations/liangyaoyao-v2.webp"
OUTPUT_DIR = ROOT / "public/assets/animations"
FRAME_WIDTH = 192
FRAME_HEIGHT = 208


def crop_cell(sheet: Image.Image, row: int, column: int) -> Image.Image:
    left = column * FRAME_WIDTH
    top = row * FRAME_HEIGHT
    return sheet.crop((left, top, left + FRAME_WIDTH, top + FRAME_HEIGHT))


def make_sheet(frames: list[Image.Image], path: Path) -> None:
    sheet = Image.new(
        "RGBA",
        (FRAME_WIDTH * len(frames), FRAME_HEIGHT),
        (0, 0, 0, 0),
    )
    for index, frame in enumerate(frames):
        sheet.alpha_composite(frame.convert("RGBA"), (index * FRAME_WIDTH, 0))
    sheet.save(path, format="WEBP", lossless=True, quality=100, method=6)


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    with Image.open(SOURCE) as source:
        if source.width < FRAME_WIDTH * 8 or source.height < FRAME_HEIGHT * 9:
            raise ValueError("The source atlas is smaller than the expected emote cells")

        tilt_cells = [(8, 5), (8, 1), (8, 0), (8, 5)]
        puff_cells = [(7, 5), (7, 1), (7, 2), (7, 3), (7, 4), (7, 5)]
        make_sheet(
            [crop_cell(source, row, column) for row, column in tilt_cells],
            OUTPUT_DIR / "emote_tilt_head.webp",
        )
        make_sheet(
            [crop_cell(source, row, column) for row, column in puff_cells],
            OUTPUT_DIR / "emote_puff_angry.webp",
        )


if __name__ == "__main__":
    main()
