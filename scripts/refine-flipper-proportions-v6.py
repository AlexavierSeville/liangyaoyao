"""User-authorized local proportion correction, shared across the approved 16 poses."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'output/flipper-hold-draft-2026-09-10'
SOURCE=RUN/'preview-v6-before-proportions'
OUT=RUN/'preview-v6';OUT.mkdir(exist_ok=True);(OUT/'frames').mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)

def adjust(im):
    rgba=np.array(im.convert('RGBA'),dtype=np.float32);h,w=rgba.shape[:2]
    rgba[rgba[:,:,3]<16]=0
    yy,xx=np.mgrid[:h,:w].astype(np.float32)
    # Shared vertical landmarks: reduce oversized head/low neck, lengthen
    # torso to the master's distribution, restore thicker feet at same ground.
    my=np.interp(yy,[0,47,120,166,240,289,330,360],[0,47,133,182,248,295,330,360])
    sx=np.interp(yy,[0,47,120,166,200,255,285,310,360],[.87,.87,.87,.90,.95,.96,.96,.91,.91])
    mx=190+(xx-190)/sx
    outer=np.clip((np.abs(xx-190)-100)/45,0,1)
    # Use a smooth global field, avoiding local hand masks that can fold the
    # sampling map and produce duplicated contours at contact boundaries.
    protection=outer
    mx=mx*(1-protection)+xx*protection;my=my*(1-protection)+yy*protection
    mx=np.clip(mx,0,w-1);my=np.clip(my,0,h-1)
    x0=mx.astype(int);y0=my.astype(int);x1=np.minimum(x0+1,w-1);y1=np.minimum(y0+1,h-1)
    wx=(mx-x0)[:,:,None];wy=(my-y0)[:,:,None]
    premult=rgba.copy();premult[:,:,:3]*=premult[:,:,3:4]/255
    v=(premult[y0,x0]*(1-wx)+premult[y0,x1]*wx)*(1-wy)+(premult[y1,x0]*(1-wx)+premult[y1,x1]*wx)*wy
    v[:,:,:3]=np.divide(v[:,:,:3]*255,v[:,:,3:4],out=np.zeros_like(v[:,:,:3]),where=v[:,:,3:4]>0)
    v=np.clip(np.rint(v),0,255).astype('uint8');v[v[:,:,3]<16]=0
    return Image.fromarray(v)

original=[Image.open(p).convert('RGBA') for p in sorted((SOURCE/'frames').glob('*.png'))]
assert len(original)==16
frames=[adjust(im) for im in original]
# Keep the coherent generated tiptoe silhouette. Align the raised-body pose's
# toe endpoints to the neighboring ground level without grafting other feet.
tiptoe=frames[10];grounded=Image.new('RGBA',tiptoe.size)
grounded.alpha_composite(tiptoe,(0,331-tiptoe.getbbox()[3]));frames[10]=grounded
q=json.loads((SOURCE/'qa.json').read_text());durations=[f['durationMs'] for f in q['frames']]
previews=[];board=Image.new('RGB',(1680,4*385),'#dae4e3');d=ImageDraw.Draw(board)
checks=[]
for i,im in enumerate(frames):
    im.save(OUT/'frames'/f'frame_{i+1:02d}.png')
    x=i%4*420;y=i//4*385;board.paste(im,(x,y+22),im);d.text((x+10,y+3),f'{i+1:02d}',font=font,fill='#29443e')
    bg=Image.new('RGB',(420,380),'#dae4e3');bg.paste(im,(0,15),im);previews.append(bg)
    a=np.array(im)[:,:,3];mask=Image.fromarray(np.where(a>0,255,0).astype('uint8')).copy();ImageDraw.floodfill(mask,(0,0),128)
    bounds=im.getbbox();checks.append({'frame':i+1,'bounds':bounds,'interiorZeroAlphaPixels':int((np.array(mask)==0).sum()),'clipped':bounds[0]==0 or bounds[1]==0 or bounds[2]==420 or bounds[3]==360})
board.save(OUT/'contact-sheet.png');previews[0].save(OUT/'playful-handshake-refined.gif',save_all=True,append_images=previews[1:],duration=durations,loop=0,disposal=2)
master=Image.open(RUN/'references/canonical-front.png').convert('RGBA');master=master.crop(master.getbbox());master=master.resize((round(master.width*280/master.height),280),Image.Resampling.LANCZOS)
mc=Image.new('RGBA',(420,360));mc.alpha_composite(master,(190-master.width//2,50))
compare=Image.new('RGB',(1260,400),'#dae4e3');dr=ImageDraw.Draw(compare)
for i,(name,im) in enumerate([('母版',mc),('调整前 v5',Image.open(RUN/'preview-v5/frames/frame_01.png')),('调整后 v6',frames[0])]):
    compare.paste(im,(i*420,30),im);dr.text((i*420+12,8),name,font=font,fill='#29443e')
compare.save(OUT/'master-comparison.png')
html=(SOURCE/'index.html').read_text(encoding='utf-8').replace('开心小跳（待修）','落脚修订').replace('追手再握（待修）','追手接触修订').replace('16 帧审核预览，尚未接入正式素材。','16 帧身材微调审核预览，尚未接入正式素材。').replace('<a href="contact-sheet.png">完整帧表</a>','<a href="contact-sheet.png">完整帧表</a> · <a href="master-comparison.png">母版／调整前／调整后</a>')
(OUT/'index.html').write_text(html,encoding='utf-8')
(OUT/'qa.json').write_text(json.dumps({'status':'pending_visual_review','runtimeModified':False,'durationMs':sum(durations),'method':'shared smooth continuous inverse warp with outer attenuation and premultiplied interpolation','headHorizontalScale':.87,'bellyHorizontalScale':.95,'sharedVerticalLandmarks':{'destination':[47,120,166,240,289,330],'source':[47,133,182,248,295,330]},'frames':checks},indent=2),encoding='utf-8')
print(json.dumps({'out':str(OUT),'clipped':[x['frame'] for x in checks if x['clipped']],'holes':[x for x in checks if x['interiorZeroAlphaPixels']]}))
