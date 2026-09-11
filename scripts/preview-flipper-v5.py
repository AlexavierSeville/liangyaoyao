"""Review-only extraction of the two generated, user-requested animation batches."""
from pathlib import Path
import os
import json
import hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'output/flipper-hold-draft-2026-09-10'
OUT=RUN/os.environ.get('PET_FLIPPER_PREVIEW_DIR','preview-v5');OUT.mkdir(exist_ok=True)
(OUT/'frames').mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
durations=[220,180,160,260,180,220,180,200,180,180,220,180,180,220,200,260]
labels=['轻抚','低头看手','主动轻碰','缩翅逗一下','再递翅尖','掌心接住','轻轻握住','一起轻抬','握着落下','再轻抬','开心小跳（待修）','柔和落下','张手松开','追手再握（待修）','满足收翅','收翅恢复']

def cut(im):
    rgb=np.array(im.convert('RGB'),dtype=np.int16)
    r,g,b=(rgb[:,:,i] for i in range(3))
    bg=(r>150)&(b>140)&(g<125)&(r-g>70)&(b-g>70)
    rgba=np.concatenate([rgb,np.where(bg,0,255)[:,:,None]],axis=2).astype('uint8')
    rgba[bg]=0
    return Image.fromarray(rgba)

frames=[];metrics=[]
for batch in ['a','b']:
    name=os.environ.get('PET_FLIPPER_PART_B','flipper-right-v5-part-b.png') if batch=='b' else 'flipper-right-v5-part-a.png'
    src=Image.open(RUN/'decoded'/name)
    parts=[];origins=[];boxes=[]
    clean=cut(src)
    # Locate actual empty gutters: a hand can cross a nominal grid line.
    edges_by_row=[]
    for row in range(2):
        band=np.array(clean)[round(row*src.height/2):round((row+1)*src.height/2),:,3]
        empty=np.where((band>0).sum(axis=0)==0)[0]
        edges=[0]
        for col in range(1,4):
            nominal=round(col*src.width/4)
            choices=empty[(empty>nominal-30)&(empty<nominal+65)]
            if not len(choices): raise ValueError(f'No safe gutter: {batch}/{row}/{col}')
            edges.append(int(choices[np.argmin(abs(choices-nominal))]))
        edges.append(src.width);edges_by_row.append(edges)
    for i in range(8):
        row,col=divmod(i,4)
        box=(edges_by_row[row][col],round(row*src.height/2),edges_by_row[row][col+1],round((row+1)*src.height/2))
        parts.append(clean.crop(box));boxes.append(box)
        origins.append(box[0]-round(col*src.width/4))
    # One shared transform per batch. Keep actual pose compression/bounce.
    anchor=parts[0];bbox=anchor.getbbox()
    if batch=='a': reference_height=bbox[3]-bbox[1]
    scale=280/(bbox[3]-bbox[1])
    head=anchor.crop((0,bbox[1],anchor.width,bbox[1]+round((bbox[3]-bbox[1])*.30))).getbbox()
    center=(head[0]+head[2])/2
    row_offsets=[0,0]
    if os.environ.get('PET_FLIPPER_ALIGN_ROWS')=='1':
        # Correct layout displacement between source sheet rows, not motion
        # inside a row. Shared medians retain heel lifts and squash poses.
        row_floors=[float(np.median([p.getbbox()[3] for p in parts[row*4:row*4+4]])) for row in range(2)]
        row_offsets=[row_floors[0]-floor for floor in row_floors]
    # All source cells in a batch use the same center and ground reference.
    for i,part in enumerate(parts):
        out=Image.new('RGBA',(420,360))
        resized=part.resize((round(part.width*scale),round(part.height*scale)),Image.Resampling.LANCZOS)
        x=round(190+(origins[i]-center)*scale);y=round(330+(row_offsets[i//4]-bbox[3])*scale)
        out.alpha_composite(resized,(x,y))
        index=len(frames);out.save(OUT/'frames'/f'frame_{index+1:02d}.png');frames.append(out)
        b=out.getbbox(); metrics.append({'frame':index+1,'batch':batch,'sourceCell':i+1,'sourceBox':boxes[i],'batchScale':scale,'bounds':b,'durationMs':durations[index],'clipped':b[0]==0 or b[1]==0 or b[2]==420 or b[3]==360})
board=Image.new('RGB',(4*420,4*395),'#dae4e3');draw=ImageDraw.Draw(board);gif=[]
for i,im in enumerate(frames):
    x=i%4*420;y=i//4*395;board.paste(im,(x,y+28),im);draw.text((x+12,y+5),f'{i+1:02d} · {labels[i]}',font=font,fill='#29443e')
    bg=Image.new('RGB',(420,400),'#dae4e3');bg.paste(im,(0,24),im);d=ImageDraw.Draw(bg);d.text((14,7),f'{i+1:02d}/16 · {labels[i]}',font=font,fill='#29443e');gif.append(bg)
board.save(OUT/'contact-sheet.png')
gif[0].save(OUT/'playful-handshake.gif',save_all=True,append_images=gif[1:],duration=durations,loop=0,disposal=2)
(OUT/'qa.json').write_text(json.dumps({'status':'review_only','runtimeModified':False,'method':'4x2 cell extraction; magenta matte; shared registration per batch; no invented frames or crossfade','frames':metrics,'loopDurationMs':sum(durations)},ensure_ascii=False,indent=2),encoding='utf-8')
html='''<!doctype html><meta charset="utf-8"><title>轻抚与握手 · 16 帧预览</title><style>body{background:#eef2ef;color:#29443e;font:16px "Microsoft YaHei",sans-serif;margin:0;display:grid;place-items:center}main{max-width:1000px;text-align:center;padding:24px}#pet{display:block;width:420px;height:360px;margin:auto;background:#dae4e3;border-radius:16px}button,select{font:inherit;padding:8px;margin:10px;border:1px solid #bbccc5;border-radius:8px}input{width:320px}p{line-height:1.8}a{color:#386958}</style><main><h2>轻碰、逗手、握手、踮脚、追手</h2><img id="pet" src="frames/frame_01.png"><p id="label"></p><button id="play">暂停</button><select id="speed"><option value="1">正常速度</option><option value="2">半速</option></select><br><input id="seek" type="range" min="0" max="15" value="0"><p>16 帧审核预览，尚未接入正式素材。<br>可暂停或拖动逐帧检查，重点看动作丰富度、人物神态和两批衔接。</p><a href="contact-sheet.png">完整帧表</a></main><script>const names=NAMES,durations=DURATIONS;let i=0,active=true,last=0;const pet=document.querySelector('#pet'),label=document.querySelector('#label'),seek=document.querySelector('#seek'),play=document.querySelector('#play'),speed=document.querySelector('#speed');const imgs=names.map((_,n)=>{let a=new Image();a.src=`frames/frame_${String(n+1).padStart(2,'0')}.png`;return a});function show(){pet.src=imgs[i].src;label.textContent=`${i+1}/16 · ${names[i]}`;seek.value=i}play.onclick=()=>{active=!active;play.textContent=active?'暂停':'播放';last=0};seek.oninput=()=>{active=false;play.textContent='播放';i=+seek.value;show()};function tick(t){if(active&&t-last>durations[i]*+speed.value){i=(i+1)%16;show();last=t}requestAnimationFrame(tick)}show();requestAnimationFrame(tick)</script>'''.replace('NAMES',json.dumps(labels,ensure_ascii=False)).replace('DURATIONS',json.dumps(durations))
(OUT/'index.html').write_text(html,encoding='utf-8')
print(json.dumps({'out':str(OUT),'clippedFrames':[m['frame'] for m in metrics if m['clipped']],'durationMs':sum(durations)}))
