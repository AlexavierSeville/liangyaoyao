"""Measure actual exported bird silhouettes against idle, not canvas sizes."""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / ".codex/skills/hatch-pet/scripts"))
from extract_strip_frames import connected_components


def bird_bounds(image):
    mask = image.copy()
    mask.putalpha(image.getchannel("A").point(lambda a: 255 if a > 32 else 0))
    return max(connected_components(mask), key=lambda c: c["area"])["bbox"]


def head_center(image, bounds):
    # Resampling can connect a touching hand to the body. Measure the head
    # above the hand rather than allowing the hand to bias body registration.
    head = image.crop((0, bounds[1], image.width, bounds[1] + round((bounds[3]-bounds[1]) * 0.35)))
    box = bird_bounds(head)
    return (box[0] + box[2]) / 2


def main():
    assets = ROOT / "public/assets/animations"
    qa = ROOT / "docs/touch-recovery-2026-09-08"
    idle = Image.open(assets / "idle_breathe.webp").convert("RGBA").crop((0, 0, 192, 208))
    neutral = Image.new("RGBA", (320, 228))
    neutral.alpha_composite(idle, (64, 12))
    bounds = bird_bounds(neutral)
    height = bounds[3] - bounds[1]
    sheet = Image.new("RGB", (1280, 270), "#d4dedc")
    draw = ImageDraw.Draw(sheet)
    sheet.paste(neutral, (0, 30), neutral)
    draw.text((16, 8), f"Idle | {height}px", fill="black")
    result = {"idleBodyBounds": bounds, "clips": {}, "ok": True}
    for column, clip in enumerate([
        "touch_belly_dislike", "touch_flipper_react_screen_left", "touch_flipper_react_screen_right"
    ], 1):
        frames = sorted((assets / "hd" / clip).glob("frame_*@2x.webp"))
        assert len(frames) == 12, clip
        for path in frames:
            frame = Image.open(path).convert("RGBA")
            assert frame.size == (640, 456), path
            left, top, right, bottom = frame.getbbox()
            assert min(left, top, 640-right, 456-bottom) >= 4, f"clipping: {path}"
        image = Image.open(frames[0]).convert("RGBA").resize((320, 228), Image.Resampling.LANCZOS)
        measured = bird_bounds(image)
        body_height = measured[3] - measured[1]
        assert abs(body_height - height) <= 1, f"body size mismatch: {clip}"
        assert abs(measured[3] - bounds[3]) <= 1, f"foot baseline mismatch: {clip}"
        center = head_center(image, measured)
        assert abs(center - head_center(neutral, bounds)) <= 1, f"head center mismatch: {clip}"
        result["clips"][clip] = {"neutralForegroundBounds": measured, "neutralBodyHeight": body_height, "neutralHeadCenterX": center, "framesChecked": len(frames), "clippedFrames": 0}
        sheet.paste(image, (column * 320, 30), image)
        label = clip.replace("touch_", "").replace("react_screen_", "")
        draw.text((column * 320 + 16, 8), f"{label} | {body_height}px", fill="black")
    sheet.save(qa / "size-comparison.png")
    (qa / "size-validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
