"""Extract the two left-side generated batches for user review."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'output/flipper-hold-draft-2026-09-10'
OUT=RUN/'preview-left-v1';(OUT/'frames').mkdir(parents=True,exist_ok=True)
durations=[220,180,160,260,180,220,180,200,180,180,220,180,180,220,200,260]
frames=[];metrics=[]
for batch in ['a','b']:
    path=RUN/'decoded'/f'flipper-left-final-part-{batch}.png'
    if not path.exists():break
    src=Image.open(path).convert('RGB');a=np.array(src).astype(int);r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
    bg=(r>150)&(b>140)&(g<125)&(r-g>70)&(b-g>70)
    rgba=np.dstack([a,np.where(bg,0,255)]).astype('uint8');rgba[bg]=0;clean=Image.fromarray(rgba)
    w,h=src.size;parts=[];origins=[];boxes=[]
    for row in range(2):
        band=rgba[round(row*h/2):round((row+1)*h/2),:,3];empty=np.where((band>0).sum(axis=0)==0)[0];edges=[0]
        for col in range(1,4):
            nominal=round(col*w/4);choices=empty[(empty>nominal-60)&(empty<nominal+60)]
            assert len(choices)>0,(batch,row,col)
            edges.append(int(choices[np.argmin(abs(choices-nominal))]))
        edges.append(w)
        for col in range(4):
            box=(edges[col],round(row*h/2),edges[col+1],round((row+1)*h/2));boxes.append(box)
            parts.append(clean.crop(box));origins.append(box[0]-round(col*w/4))
    bb=parts[0].getbbox();scale=280/(bb[3]-bb[1]);head=parts[0].crop((0,bb[1],parts[0].width,bb[1]+round((bb[3]-bb[1])*.25))).getbbox();center=(head[0]+head[2])/2
    floors=[float(np.median([p.getbbox()[3] for p in parts[row*4:row*4+4]])) for row in range(2)]
    for i,p in enumerate(parts):
        result=Image.new('RGBA',(480,360));scaled=p.resize((round(p.width*scale),round(p.height*scale)),Image.Resampling.LANCZOS)
        x=round(260+(origins[i]-center)*scale);y=round(330+(floors[0]-floors[i//4]-bb[3])*scale)
        result.alpha_composite(scaled,(x,y));bound=result.getbbox();assert bound[0]>0 and bound[1]>0 and bound[2]<480 and bound[3]<360,(batch,i,bound)
        index=len(frames);result.save(OUT/'frames'/f'frame_{index+1:02d}.png');frames.append(result)
        metrics.append({'frame':index+1,'batch':batch,'source':str(path.relative_to(RUN)),'sourceSHA256':hashlib.sha256(path.read_bytes()).hexdigest(),'sourceCellBox':boxes[i],'batchScale':scale,'bounds':bound,'durationMs':durations[index]})
if len(frames)==16:
    # Reuse the existing resting pose to close the loop; no new invented pose.
    frames[15]=frames[0].copy();frames[15].save(OUT/'frames/frame_16.png')
    metrics[15]['assemblyOverride']='Reuse generated part A cell 1 as resting end pose'
    # Separate the existing open hand from the unchanged wing for the release.
    im=frames[12];a=np.array(im);rgb=a[:,:,:3].astype(int);yy,xx=np.mgrid[:im.height,:im.width]
    skin=((xx<145)|((rgb[:,:,0]>175)&(rgb[:,:,0]-rgb[:,:,1]>12)&(rgb[:,:,0]-rgb[:,:,2]>20)))&(xx<172)&(yy>100)&(yy<220)&(a[:,:,3]>0)
    mask=np.array(Image.fromarray((skin*255).astype('uint8')).filter(ImageFilter.MaxFilter(3)))>0
    mask&=(xx<172)&(yy>100)&(yy<220)
    hand=a.copy();hand[~mask]=0;base=a.copy();base[mask]=0
    result=Image.fromarray(base);result.alpha_composite(Image.fromarray(hand),(-15,0));frames[12]=result;result.save(OUT/'frames/frame_13.png')
    metrics[12]['assemblyOverride']='Translate extracted existing open hand 15px left for release; no redraw'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16);rows=(len(frames)+3)//4
board=Image.new('RGB',(1920,rows*385),'#dae4e3');d=ImageDraw.Draw(board);gif=[]
for i,im in enumerate(frames):
    x=i%4*480;y=i//4*385;board.paste(im,(x,y+22),im);d.text((x+10,y+3),f'{i+1:02d}',font=font,fill='#29443e')
    bg=Image.new('RGB',(480,380),'#dae4e3');bg.paste(im,(0,15),im);gif.append(bg)
board.save(OUT/'contact-sheet.png');gif[0].save(OUT/'left-handshake.gif',save_all=True,append_images=gif[1:],duration=durations[:len(frames)],loop=0,disposal=2)
html=(RUN/'final-right-flipper/index.html').read_text(encoding='utf-8').replace('16 帧定稿素材 · 单轮 3.22 秒。','左侧 16 帧初版 · 待用户审核。').replace('已完成母版比例、脚掌和透明边缘检查。','核对另一侧的手、握持姿势和动作衔接。').replace('母版／定稿','左右两侧对比').replace('master-comparison.png','side-comparison.png').replace('width:420px','width:480px')
if len(frames)==16:(OUT/'index.html').write_text(html,encoding='utf-8')
(OUT/'qa.json').write_text(json.dumps({'stage':'pending_user_review','frames':metrics,'frameCount':len(frames),'durationMs':sum(durations[:len(frames)]),'runtimeIntegrated':False},ensure_ascii=False,indent=2),encoding='utf-8')
compare=Image.new('RGB',(960,400),'#dae4e3');d=ImageDraw.Draw(compare)
for i,(label,im) in enumerate([('右侧定稿',Image.open(RUN/'final-right-flipper/frames/frame_01.png')),('左侧初版',frames[0])]):
    compare.paste(im,(i*480,30),im);d.text((i*480+12,8),label,font=font,fill='#29443e')
compare.save(OUT/'side-comparison.png');print(json.dumps({'frames':len(frames),'out':str(OUT)}))
