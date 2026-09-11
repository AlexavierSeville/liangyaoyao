"""Finalize the user-approved right-flipper artwork, without runtime mutation."""
from pathlib import Path
import importlib.util,json,hashlib,zipfile
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageSequence
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'output/flipper-hold-draft-2026-09-10'
SRC=RUN/'preview-v9';OUT=RUN/'final-right-flipper'
for part in ['frames','hd','qa']:(OUT/part).mkdir(parents=True,exist_ok=True)
skill=Path('C:/Users/研发04/.codex/skills/hatch-pet/scripts/despill_chroma_edges.py')
spec=importlib.util.spec_from_file_location('pet_despill',skill);cleanup=importlib.util.module_from_spec(spec);spec.loader.exec_module(cleanup)
durations=[220,180,160,260,180,220,180,200,180,180,220,180,180,220,200,260]
source=sorted((SRC/'frames').glob('*.png'));assert len(source)==16
frames=[];reports=[]
for i,p in enumerate(source,1):
    im=Image.open(p).convert('RGBA')
    result,report=cleanup.decontaminate_image(im,chroma_key=(255,0,255),edge_radius=5)
    assert np.array_equal(np.array(im)[:,:,3],np.array(result)[:,:,3])
    result.save(OUT/'frames'/p.name);frames.append(result)
    a=np.array(result);rgb=a[:,:,:3].astype(int);alpha=a[:,:,3]
    suspect=(rgb[:,:,0]-rgb[:,:,1]>45)&(rgb[:,:,2]-rgb[:,:,1]>35)&(rgb[:,:,2]>.9*rgb[:,:,0])&(alpha>32)
    assert suspect.sum()==0,(i,int(suspect.sum()))
    bb=result.getbbox();assert bb[0]>0 and bb[1]>0 and bb[2]<420 and bb[3]<360
    reports.append({'frame':i,'sourceSHA256':hashlib.sha256(p.read_bytes()).hexdigest(),'outputSHA256':hashlib.sha256((OUT/'frames'/p.name).read_bytes()).hexdigest(),'bounds':bb,'remainingMagentaPixels':int(suspect.sum()),**report})

# A shared registration for all 16 poses, preserving actual lift/squash.
bb=frames[0].getbbox();scale=396/(bb[3]-bb[1]);head=frames[0].crop((0,bb[1],270,bb[1]+65)).getbbox();cx=(head[0]+head[2])/2
hdstats=[]
for i,im in enumerate(frames,1):
    b=im.getbbox();crop=im.crop(b);size=(round(crop.width*scale),round(crop.height*scale))
    x=round(318+(b[0]-cx)*scale);y=round(430+(b[1]-bb[3])*scale)
    assert x>0 and y>0 and x+size[0]<640 and y+size[1]<456,(i,x,y,size)
    out=Image.new('RGBA',(640,456));out.alpha_composite(crop.resize(size,Image.Resampling.LANCZOS),(x,y))
    out.save(OUT/'hd'/f'frame_{i:02d}@2x.webp',lossless=True,exact=True)
    hdstats.append({'frame':i,'bounds':out.getbbox(),'durationMs':durations[i-1]})

font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
board=Image.new('RGB',(1680,1540),'#dae4e3');d=ImageDraw.Draw(board);gif=[];atlas=Image.new('RGBA',(1680,1440))
for i,im in enumerate(frames):
    x=i%4*420;y=i//4*385;board.paste(im,(x,y+22),im);d.text((x+10,y+3),f'{i+1:02d}',font=font,fill='#29443e')
    atlas.alpha_composite(im,(i%4*420,i//4*360))
    bg=Image.new('RGB',(420,380),'#dae4e3');bg.paste(im,(0,15),im);gif.append(bg)
board.save(OUT/'contact-sheet.png');atlas.save(OUT/'spritesheet.png')
gif[0].save(OUT/'final-handshake.gif',save_all=True,append_images=gif[1:],duration=durations,loop=0,disposal=2)
master=Image.open(RUN/'references/canonical-front.png').convert('RGBA');master=master.crop(master.getbbox());master=master.resize((round(master.width*280/master.height),280),Image.Resampling.LANCZOS)
mc=Image.new('RGBA',(420,360));mc.alpha_composite(master,(190-master.width//2,50))
compare=Image.new('RGB',(840,400),'#dae4e3');d=ImageDraw.Draw(compare)
for i,(label,im) in enumerate([('母版',mc),('摸翅膀 · 定稿',frames[0])]):
    compare.paste(im,(i*420,30),im);d.text((i*420+12,8),label,font=font,fill='#29443e')
compare.save(OUT/'master-comparison.png')
# Multi-background edge and toe review board at original scale.
edge=Image.new('RGB',(1260,720));ed=ImageDraw.Draw(edge)
for row,idx in enumerate([0,10]):
    for col,bg in enumerate(['#ffffff','#20252b','#dae4e3']):
        cell=Image.new('RGB',(420,360),bg);cell.paste(frames[idx],(0,0),frames[idx]);edge.paste(cell,(col*420,row*360))
edge.save(OUT/'qa/edges-and-tiptoe.png')
html=(SRC/'index.html').read_text(encoding='utf-8').replace('16 帧脚掌微调审核预览，尚未接入正式素材。','16 帧定稿素材 · 单轮 3.22 秒。').replace('重点看动作丰富度、人物神态和两批衔接。','已完成母版比例、脚掌和透明边缘检查。').replace('母版／微调前／微调后','母版／定稿')
(OUT/'index.html').write_text(html,encoding='utf-8')
baseline=json.loads((RUN/'imagegen-jobs-v5.json').read_text())['runtimeBaseline'];integrity={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in baseline.items()};assert all(integrity.values())
g=Image.open(OUT/'final-handshake.gif');total=sum(f.info['duration'] for f in ImageSequence.Iterator(g));assert g.n_frames==16 and total==3220
manifest={'status':'final_artwork_authorized_by_user','scope':'screen-right flipper stroking and handshake artwork','source':'preview-v9','frameCount':16,'durationMs':total,'frameDurationsMs':durations,'loop':True,'canvas':[420,360],'spritesheet':{'file':'spritesheet.png','columns':4,'rows':4,'cell':[420,360]},'hdExport':{'canvas':[640,456],'sharedScale':scale,'neutralHeightLogical':198,'baselineLogical':215,'headCenterLogical':159,'frames':hdstats},'provenance':['imagegen-jobs-v5.json','imagegen-jobs-v6.json','preview-v7/qa.json','preview-v8/qa.json','preview-v9/qa.json'],'runtimeIntegrated':False,'runtimeUnchanged':integrity}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'qa/edge-cleanup.json').write_text(json.dumps({'ok':True,'skillScript':str(skill),'alphaPreservedAllFrames':True,'reports':reports},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'folder':str(OUT),'frames':len(frames),'durationMs':total,'magentaPixels':sum(r['remainingMagentaPixels'] for r in reports),'runtimeUnchanged':all(integrity.values())}))
