from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/assets/animations/liangyaoyao-v2.webp"
OUTPUT_DIR = ROOT / "public/assets/animations"
FRAME_WIDTH = 192
FRAME_HEIGHT = 208


def crop_frame(sheet: Image.Image, index: int) -> Image.Image:
    left = index * FRAME_WIDTH
    return sheet.crop((left, 0, left + FRAME_WIDTH, FRAME_HEIGHT))


def make_sheet(frames: list[Image.Image], path: Path) -> None:
    sheet = Image.new("RGBA", (FRAME_WIDTH * len(frames), FRAME_HEIGHT), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        sheet.alpha_composite(frame.convert("RGBA"), (index * FRAME_WIDTH, 0))
    sheet.save(path, format="WEBP", lossless=True, quality=100, method=6)


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    with Image.open(SOURCE) as source:
        if source.width < FRAME_WIDTH * 8 or source.height < FRAME_HEIGHT:
            raise ValueError("The source atlas is smaller than the expected first row")
        row = [crop_frame(source, index) for index in range(7)]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Exclude the closed-eye pose and order the remaining subtle body variants
    # into an 8-frame loop without introducing the source row's blank cell.
    breathe = [row[0], row[1], row[2], row[4], row[5], row[6], row[1], row[0]]
    make_sheet(breathe, OUTPUT_DIR / "idle_breathe.webp")
    # Open -> closed -> hold closed -> open, using the existing front-facing atlas frames.
    make_sheet([row[0], row[3], row[3], row[4]], OUTPUT_DIR / "idle_blink.webp")


if __name__ == "__main__":
    main()
