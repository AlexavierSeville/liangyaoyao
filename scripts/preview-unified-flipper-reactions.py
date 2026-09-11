"""Review-only alignment and continuity comparison of redesigned reactions."""
from pathlib import Path
import hashlib,json,os,importlib.util
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageSequence
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'output/flipper-identity-unification-2026-09-11'
OLD=ROOT/'output/flipper-hold-draft-2026-09-10';OUT=RUN/os.environ.get('PET_UNIFIED_PREVIEW','preview-v1');OUT.mkdir(exist_ok=True)
polish=None
if os.environ.get('PET_UNIFIED_POLISH')=='1':
    spec=importlib.util.spec_from_file_location('polish',ROOT/'scripts/polish-unified-reaction-identity.py');polish=importlib.util.module_from_spec(spec);spec.loader.exec_module(polish)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
durations=[220,180,160,260,180,220,180,200,180,180,220,180,180,220,200,260]
def composite(im,shift=(0,0)):
    out=Image.new('RGBA',(520,360));out.alpha_composite(im,shift);return out
def old_reaction(side):
    result=[];s=280/396
    for f in sorted((ROOT/f'public/assets/animations/hd/touch_flipper_react_screen_{side}').glob('*.webp')):
        im=Image.open(f).convert('RGBA').resize((round(640*s),round(456*s)),Image.Resampling.LANCZOS)
        result.append(composite(im,(round(260-318*s),round(330-430*s))))
    return result
def render_gif(path,seq,labels,ms):
    pics=[]
    for im,label in zip(seq,labels):
        bg=Image.new('RGB',(520,415),'#dae4e3');bg.paste(im,(0,27),im);d=ImageDraw.Draw(bg)
        d.text((12,5),label,font=font,fill='#29443e');d.text((12,389),'素材衔接预览 · 未替换正式程序',font=font,fill='#526b63');pics.append(bg)
    pics[0].save(path,save_all=True,append_images=pics[1:],duration=ms,loop=0,disposal=2)
allframes={};allmetrics={};hold={};old={}
for side in ['left','right']:
    srcpath=RUN/'decoded'/f'unified-reaction-{side}-v1.png'
    if not srcpath.exists():continue
    src=Image.open(srcpath).convert('RGB');a=np.array(src).astype(int);r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
    bg=(r>150)&(b>140)&(g<130)&(r-g>65)&(b-g>65)
    rgba=np.dstack([a,np.where(bg,0,255)]).astype('uint8');rgba[bg]=0;clean=Image.fromarray(rgba);w,h=src.size
    parts=[];origins=[];boxes=[]
    for row in range(3):
        band=rgba[round(row*h/3):round((row+1)*h/3),:,3];empty=np.where((band>0).sum(axis=0)==0)[0];edges=[0]
        for col in range(1,4):
            n=round(col*w/4);choices=empty[(empty>n-70)&(empty<n+70)];assert len(choices),(side,row,col)
            edges.append(int(choices[np.argmin(abs(choices-n))]))
        edges.append(w)
        for col in range(4):
            box=(edges[col],round(row*h/3),edges[col+1],round((row+1)*h/3));boxes.append(box)
            parts.append(clean.crop(box));origins.append(box[0]-round(col*w/4))
    bb=parts[0].getbbox();scale=280/(bb[3]-bb[1]);head=parts[0].crop((0,bb[1],parts[0].width,bb[1]+round((bb[3]-bb[1])*.25))).getbbox();cx=(head[0]+head[2])/2
    floors=[float(np.median([im.getbbox()[3] for im in parts[row*4:row*4+4]])) for row in range(3)]
    folder=OUT/side/'frames';folder.mkdir(parents=True,exist_ok=True);frames=[];metrics=[]
    for i,im in enumerate(parts):
        size=(round(im.width*scale),round(im.height*scale));x=round(260+(origins[i]-cx)*scale);y=round(330+(floors[0]-floors[i//4]-bb[3])*scale)
        result=composite(im.resize(size,Image.Resampling.LANCZOS),(x,y));bound=result.getbbox()
        assert 0<bound[0]<bound[2]<520 and 0<bound[1]<bound[3]<360,(side,i,bound)
        refinement={}
        if polish:result,refinement=polish.refine(result,side)
        result.save(folder/f'frame_{i+1:02d}.png');frames.append(result);metrics.append({'frame':i+1,'sourceCell':boxes[i],'scale':scale,'bounds':result.getbbox(),'refinement':refinement})
    allframes[side]=frames;allmetrics[side]={'sourceSHA256':hashlib.sha256(srcpath.read_bytes()).hexdigest(),'frames':metrics}
    board=Image.new('RGB',(2080,3*385),'#dae4e3');d=ImageDraw.Draw(board)
    for i,im in enumerate(frames):
        x=i%4*520;y=i//4*385;board.paste(im,(x,y+22),im);d.text((x+10,y+3),f'{i+1:02d}',font=font,fill='#29443e')
    board.save(OUT/side/'contact-sheet.png')
    render_gif(OUT/side/'reaction.gif',frames,[f'不耐烦修订 · {i+1}/12' for i in range(12)],[125]*12)
    sourcehold=OLD/('preview-left-v1' if side=='left' else 'final-right-flipper')/'frames'
    hold[side]=[composite(Image.open(f).convert('RGBA'),(0 if side=='left' else 70,0)) for f in sorted(sourcehold.glob('*.png'))];old[side]=old_reaction(side)
    seq=hold[side]*2+frames;ms=durations*2+[125]*12
    render_gif(OUT/side/'continuity.gif',seq,['轻抚与握手']*32+['持续触摸 · 统一形象后的不耐烦']*12,ms)
if len(allframes)==2:
    board=Image.new('RGB',(1560,820),'#dae4e3');d=ImageDraw.Draw(board)
    for row,side in enumerate(['left','right']):
        for col,(label,im) in enumerate([('互动企鹅',hold[side][-1]),('旧不耐烦入口',old[side][0]),('统一形象后入口',allframes[side][0])]):
            x=col*520;y=row*410;board.paste(im,(x,y+32),im);d.text((x+12,y+8),('左侧 · ' if side=='left' else '右侧 · ')+label,font=font,fill='#29443e')
    board.save(OUT/'entry-comparison.png')
    # Direct old/new transition comparison at identical time points.
    for side in ['left','right']:
        before=hold[side]*2+old[side];after=hold[side]*2+allframes[side];pics=[]
        for i,(a,b) in enumerate(zip(before,after)):
            bg=Image.new('RGB',(1040,410),'#dae4e3');bg.paste(a,(0,28),a);bg.paste(b,(520,28),b);d=ImageDraw.Draw(bg)
            d.text((12,5),'调整前',font=font,fill='#29443e');d.text((532,5),'统一形象后',font=font,fill='#29443e');d.text((12,386),'握手' if i<32 else '不耐烦 · 素材预演',font=font,fill='#29443e');pics.append(bg)
        pics[0].save(OUT/f'{side}-before-after.gif',save_all=True,append_images=pics[1:],duration=durations*2+[125]*12,loop=0,disposal=2)
    html='<!doctype html><meta charset="utf-8"><title>不耐烦形象统一审核</title><style>body{font:16px Microsoft YaHei;background:#dae4e3;color:#29443e;margin:24px}img{max-width:100%}a{color:#28604b}</style><h2>互动 → 不耐烦：形象统一初版</h2><p>只调整不耐烦素材。以下是素材预演，未修改正式配置或 exe。</p><h3>切换入口比较</h3><img src="entry-comparison.png"><h3>左侧：调整前／后</h3><img src="left-before-after.gif"><h3>右侧：调整前／后</h3><img src="right-before-after.gif"><p><a href="left/contact-sheet.png">左侧全帧</a> · <a href="right/contact-sheet.png">右侧全帧</a></p>'
    (OUT/'index.html').write_text(html,encoding='utf-8')
(OUT/'qa.json').write_text(json.dumps({'status':'candidate_pending_user_approval','runtimeModified':False,'sides':allmetrics,'originalHoldUnchanged':True,'reactionDurationsMs':[125]*12,'noCrossfade':True},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'out':str(OUT),'sides':list(allframes)}))
