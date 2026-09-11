"""User-approved local raster proportion adjustment; candidates only.

Reads approved runtime frames and writes a separate review folder. The shared
map for each action preserves frame order and applies no per-frame fitting.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / ".codex/skills/hatch-pet/scripts"))
from extract_strip_frames import connected_components
OUT = ROOT / "docs/body-proportion-review-2026-09-09/candidate-v1"
SETTINGS = {
    "touch_belly_dislike": {"head_scale": 0.91, "belly_scale": 0.89, "beak_y": 78, "neck_y": 102, "hand_dx": -8},
    "touch_flipper_react_screen_left": {"head_scale": 0.85, "belly_scale": 0.87, "beak_y": 82.5, "neck_y": 105, "hand_dx": 8},
    "touch_flipper_react_screen_right": {"head_scale": 0.87, "belly_scale": 0.88, "beak_y": 80, "neck_y": 104, "hand_dx": -8},
}


def adjust(source, setting):
    rgba = np.array(source.convert("RGBA"), dtype=np.float32)
    h, w = rgba.shape[:2]
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    # Coordinates are logical pixels; assets are @2x. The crown and grounded
    # soles stay anchored. Face/neck and belly move upward within that extent.
    destination_y = np.array([0, 17, 74, 98, 160, 187, 215, 228], dtype=float)
    source_y = np.array([0, 17, setting["beak_y"], setting["neck_y"], 164, 192, 215, 228], dtype=float)
    map_y = np.interp(yy / 2, destination_y, source_y).astype(np.float32) * 2
    scale_x = np.interp(yy / 2,
        [0, 17, 74, 98, 120, 160, 180, 192, 228],
        [setting["head_scale"]]*4 + [setting["belly_scale"]]*2 + [0.96, 1, 1]).astype(np.float32)
    center_x = 159 * 2
    map_x = center_x + (xx - center_x) / scale_x

    # Detect the existing peach hand, preserving its construction and position.
    # Cream body and orange feet differ in red/green contrast and blue content.
    r, g, b, a = (rgba[:, :, i] for i in range(4))
    side = xx < 240 if setting["hand_dx"] > 0 else xx > 390
    skin = (a > 32) & (r > 200) & (g > 140) & (b > 110) & (b < 200) & (r-g > 25) & (g-b < 75) & side & (yy < 370)
    skin_image = Image.new("RGBA", source.size)
    skin_image.putalpha(Image.fromarray((skin*255).astype(np.uint8)))
    regions = connected_components(skin_image)
    selected_skin = np.zeros(h*w, dtype=np.uint8)
    # A real hand is a substantial peach component. Single warm texture
    # speckles on the wing/face must never be cut from the bird.
    if regions:
        largest = max(regions, key=lambda c: c["area"])
        if largest["area"] >= 300:
            selected_skin[largest["pixels"]] = 255
    hand_mask = Image.fromarray(selected_skin.reshape((h,w))).filter(ImageFilter.MaxFilter(13))
    hand_pixels = np.array(hand_mask) > 0
    hand = rgba.copy()
    hand[~hand_pixels] = 0
    rgba[hand_pixels] = 0
    # Distant background/hand space should not follow torso compression.
    distance = np.abs(xx-center_x) / 2
    outer = np.clip((distance - 86) / 32, 0, 1)
    protection = outer
    map_x = map_x * (1-protection) + xx * protection
    map_y = map_y * (1-protection) + yy * protection
    map_x = np.clip(map_x, 0, w-1)
    map_y = np.clip(map_y, 0, h-1)

    # Premultiplied interpolation avoids matte fringes and transparent seams.
    alpha = rgba[:, :, 3:4] / 255
    premult = np.concatenate((rgba[:, :, :3] * alpha, rgba[:, :, 3:4]), axis=2)
    x0 = map_x.astype(np.int32); y0 = map_y.astype(np.int32)
    x1 = np.minimum(x0+1, w-1); y1 = np.minimum(y0+1, h-1)
    wx = (map_x-x0)[:, :, None]; wy = (map_y-y0)[:, :, None]
    sampled = ((premult[y0,x0]*(1-wx)+premult[y0,x1]*wx)*(1-wy)
               +(premult[y1,x0]*(1-wx)+premult[y1,x1]*wx)*wy)
    rgb = np.divide(sampled[:, :, :3]*255, sampled[:, :, 3:4],
                    out=np.zeros_like(sampled[:, :, :3]), where=sampled[:, :, 3:4]>0)
    result = np.clip(np.rint(np.concatenate((rgb,sampled[:, :, 3:4]),axis=2)),0,255).astype(np.uint8)
    result[result[:, :, 3]==0,:3]=0
    result_image = Image.fromarray(result)
    # Keep the complete original hand as one rigid piece. An inward translation
    # follows the narrower body; the same offset applies to every frame.
    result_image.alpha_composite(Image.fromarray(hand.astype(np.uint8)),
                                 (setting["hand_dx"] * 2, -10))
    return result_image


def master_frame():
    frame=Image.open(ROOT / "docs/body-proportion-review-2026-09-09/master-front.png").convert("RGBA")
    result=Image.new("RGBA",(640,456))
    result.alpha_composite(frame.resize((384,416),Image.Resampling.LANCZOS),(128,24))
    return result


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    master=master_frame()
    comparison=Image.new("RGB",(960,3*270),'#dae2e0')
    draw=ImageDraw.Draw(comparison)
    checks={}
    for row,(clip,setting) in enumerate(SETTINGS.items()):
        directory=OUT/clip;directory.mkdir(exist_ok=True)
        frames=[]; original=[]
        for source_path in sorted((ROOT/'public/assets/animations/hd'/clip).glob('frame_*@2x.webp')):
            source=Image.open(source_path).convert('RGBA')
            result=adjust(source,setting)
            result.save(directory/(source_path.stem+'.png'))
            original.append(source);frames.append(result)
        for col,(label,im) in enumerate([('MASTER',master),('CURRENT',original[0]),('CANDIDATE v1',frames[0])]):
            small=im.resize((320,228),Image.Resampling.LANCZOS)
            comparison.paste(small,(col*320,row*270+32),small)
            draw.text((col*320+10,row*270+4),label+' / '+clip.replace('touch_',''),fill='black')
        contact=Image.new('RGB',(6*320,2*252),'#dae2e0');d=ImageDraw.Draw(contact);previews=[]
        for i,im in enumerate(frames):
            small=im.resize((320,228),Image.Resampling.LANCZOS)
            contact.paste(small,(i%6*320,i//6*252+20),small);d.text((i%6*320+8,i//6*252+3),str(i+1),fill='black')
            preview=Image.new('RGB',(320,228),'#dae2e0');preview.paste(small,(0,0),small);previews.append(preview)
        contact.save(OUT/(clip+'-contact.png'))
        previews[0].save(OUT/(clip+'-preview.gif'),save_all=True,append_images=previews[1:],duration=125,loop=0)
        checks[clip]={'frames':len(frames),'parameters':setting,'status':'candidate_pending_user_approval'}
    comparison.save(OUT/'master-current-candidate.png')
    (OUT/'manifest.json').write_text(json.dumps({'method':'user-authorized local coordinate correction, hand-protected, premultiplied sampling','runtimeModified':False,'clips':checks},indent=2),encoding='utf-8')
    print(OUT)


if __name__ == '__main__':
    main()
