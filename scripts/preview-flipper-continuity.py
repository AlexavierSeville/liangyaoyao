"""Artwork-only sequence comparison, not a recording of integrated runtime."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'output/flipper-hold-draft-2026-09-10'
OUT=RUN/'preview-left-v1';font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
durations=[220,180,160,260,180,220,180,200,180,180,220,180,180,220,200,260]
def canvas(im,offset=(0,0)):
    out=Image.new('RGBA',(520,360));out.alpha_composite(im,offset);return out
master=Image.open(RUN/'references/canonical-front.png').convert('RGBA');master=master.crop(master.getbbox());master=master.resize((round(master.width*280/master.height),280),Image.Resampling.LANCZOS);idle=canvas(master,(260-master.width//2,50))
left=[canvas(Image.open(p).convert('RGBA')) for p in sorted((OUT/'frames').glob('*.png'))];assert len(left)==16
right=[canvas(Image.open(p).convert('RGBA'),(70,0)) for p in sorted((RUN/'final-right-flipper/frames').glob('*.png'))]
reactions={}
for side in ['left','right']:
    seq=[]
    for p in sorted((ROOT/f'public/assets/animations/hd/touch_flipper_react_screen_{side}').glob('*.webp')):
        im=Image.open(p).convert('RGBA');ratio=280/396;im=im.resize((round(640*ratio),round(456*ratio)),Image.Resampling.LANCZOS)
        seq.append(canvas(im,(round(260-318*ratio),round(330-430*ratio))))
    assert len(seq)==12;reactions[side]=seq
timeline=[(idle,idle,400,'按住翅膀 · 等待长按判定')]
for _ in range(2):
    timeline.extend((l,r,t,'长按中 · 轻抚与握手') for l,r,t in zip(left,right,durations))
timeline.extend((l,r,125,'按住约 6.84 秒 · 已有不耐烦动作') for l,r in zip(reactions['left'],reactions['right']))
timeline.append((idle,idle,800,'动作结束 · 回到待机'))
pics=[];times=[]
for l,r,t,label in timeline:
    bg=Image.new('RGB',(1040,445),'#dae4e3');d=ImageDraw.Draw(bg)
    d.text((20,8),'左侧初版',font=font,fill='#29443e');d.text((540,8),'右侧定稿',font=font,fill='#29443e')
    bg.paste(l,(0,30),l);bg.paste(r,(520,30),r);d.text((20,391),label,font=font,fill='#29443e')
    d.text((20,417),'素材衔接预演 · 非程序录屏 · 反应使用当前已配置素材',font=font,fill='#526b63')
    pics.append(bg);times.append(t)
pics[0].save(OUT/'continuity-preview.gif',save_all=True,append_images=pics[1:],duration=times,loop=0,disposal=2)
(OUT/'continuity-preview.json').write_text(json.dumps({'kind':'artwork_storyboard_not_runtime_recording','holdStartsMs':400,'impatienceStartsMs':6840,'durationMs':sum(times),'sourceReaction':'current public assets, unchanged','frames':len(pics)},indent=2),encoding='utf-8')
print(OUT/'continuity-preview.gif')
