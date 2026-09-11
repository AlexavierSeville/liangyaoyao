"""User-requested small foot reduction; v8 remains the immutable source."""
from pathlib import Path
from collections import deque
import hashlib,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'output/flipper-hold-draft-2026-09-10'
SRC=RUN/'preview-v8';OUT=RUN/'preview-v9';(OUT/'frames').mkdir(parents=True,exist_ok=True)

def sample(a,x,y):
    h,w=a.shape[:2];x=np.clip(x,0,w-1);y=np.clip(y,0,h-1)
    x0=x.astype(int);y0=y.astype(int);x1=np.minimum(x0+1,w-1);y1=np.minimum(y0+1,h-1)
    fx=(x-x0)[...,None];fy=(y-y0)[...,None]
    return (a[y0,x0]*(1-fx)+a[y0,x1]*fx)*(1-fy)+(a[y1,x0]*(1-fx)+a[y1,x1]*fx)*fy

def foot_groups(mask):
    mask=mask.copy();groups=[]
    for yy,xx in np.argwhere(mask):
        if not mask[yy,xx]:continue
        todo=deque([(yy,xx)]);mask[yy,xx]=False;points=[]
        while todo:
            y,x=todo.popleft();points.append((y,x))
            for y1,x1 in [(y-1,x),(y+1,x),(y,x-1),(y,x+1)]:
                if 0<=y1<mask.shape[0] and 0<=x1<mask.shape[1] and mask[y1,x1]:
                    mask[y1,x1]=False;todo.append((y1,x1))
        if len(points)>100:groups.append(np.array(points))
    assert len(groups)==2,len(groups)
    return sorted(groups,key=lambda g:g[:,1].mean())

def refine(im):
    a=np.array(im).astype(float);h,w=a.shape[:2];yy,xx=np.mgrid[:h,:w].astype(float)
    orange=(a[:,:,0]>160)&(a[:,:,0]-a[:,:,1]>35)&(a[:,:,2]<140)&(a[:,:,3]>100)&(yy>260)
    groups=foot_groups(orange)
    cream=(a[:,:,0]>185)&(a[:,:,1]>175)&(a[:,:,2]>125)&(a[:,:,0]-a[:,:,1]<55)&(a[:,:,3]>100)
    protect=Image.fromarray((cream*255).astype('uint8')).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(2))
    protect=np.array(protect)/255;protect[cream]=1
    dx=np.zeros_like(xx);dy=np.zeros_like(yy);boxes=[]
    for g in groups:
        y0,x0=g.min(axis=0);y1,x1=g.max(axis=0);cx=(x0+x1)/2
        seed=np.zeros((h,w),dtype='uint8');seed[g[:,0],g[:,1]]=255
        mask=Image.fromarray(seed).filter(ImageFilter.MaxFilter(17)).filter(ImageFilter.GaussianBlur(4))
        ramp=np.clip((yy-260)/12,0,1);ramp=ramp*ramp*(3-2*ramp)
        weight=np.array(mask)/255*(1-protect)*ramp
        # Ground-anchored compression: width -10%, height up to -8%, smoothly
        # attenuated at the attachment so the foot stays joined to the body.
        ground=y1+2
        dx+=-.10*(xx-cx)*weight;dy+=.08*(ground-yy)*weight
        boxes.append({'orangeBounds':[int(x0),int(y0),int(x1+1),int(y1+1)],'groundAnchor':int(ground)})
    field=np.stack([dx,dy],axis=2);mx=xx.copy();my=yy.copy()
    for _ in range(16):
        delta=sample(field,mx,my);mx=.3*mx+.7*(xx-delta[:,:,0]);my=.3*my+.7*(yy-delta[:,:,1])
    p=a.copy();p[:,:,:3]*=p[:,:,3:4]/255;v=sample(p,mx,my)
    v[:,:,:3]=np.divide(v[:,:,:3]*255,v[:,:,3:4],out=np.zeros_like(v[:,:,:3]),where=v[:,:,3:4]>0)
    v=np.clip(np.rint(v),0,255).astype('uint8');v[v[:,:,3]==0]=0
    fixed=((np.abs(mx-xx)<1e-8)&(np.abs(my-yy)<1e-8))|cream
    v[fixed]=a.astype('uint8')[fixed]
    gyx,gxx=np.gradient(mx);gyy,gxy=np.gradient(my);jac=gxx*gyy-gyx*gxy
    assert jac.min()>.6,float(jac.min())
    assert np.array_equal(v[:260],a.astype('uint8')[:260])
    out=Image.fromarray(v);bb=out.getbbox();assert 0<bb[0]<bb[2]<w and 0<bb[1]<bb[3]<h
    return out,{'feet':boxes,'minimumInverseJacobian':float(jac.min()),'aboveY260Unchanged':True,'creamBodyUnchanged':True,'bounds':bb}

original=[Image.open(p).convert('RGBA') for p in sorted((SRC/'frames').glob('*.png'))];assert len(original)==16
frames=[];checks=[]
for i,im in enumerate(original):
    out,check=refine(im);out.save(OUT/'frames'/f'frame_{i+1:02d}.png');frames.append(out);checks.append({'frame':i+1,**check})
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
durations=[220,180,160,260,180,220,180,200,180,180,220,180,180,220,200,260]
board=Image.new('RGB',(1680,1540),'#dae4e3');d=ImageDraw.Draw(board);gif=[]
for i,im in enumerate(frames):
    x=i%4*420;y=i//4*385;board.paste(im,(x,y+22),im);d.text((x+10,y+3),f'{i+1:02d}',font=font,fill='#29443e')
    bg=Image.new('RGB',(420,380),'#dae4e3');bg.paste(im,(0,15),im);gif.append(bg)
board.save(OUT/'contact-sheet.png');gif[0].save(OUT/'smaller-feet.gif',save_all=True,append_images=gif[1:],duration=durations,loop=0,disposal=2)
master=Image.open(RUN/'references/canonical-front.png').convert('RGBA');master=master.crop(master.getbbox());master=master.resize((round(master.width*280/master.height),280),Image.Resampling.LANCZOS)
mc=Image.new('RGBA',(420,360));mc.alpha_composite(master,(190-master.width//2,50))
compare=Image.new('RGB',(1260,400),'#dae4e3');d=ImageDraw.Draw(compare)
for i,(label,im) in enumerate([('母版',mc),('脚掌调整前 v8',original[0]),('脚掌缩小后 v9',frames[0])]):
    compare.paste(im,(i*420,30),im);d.text((i*420+12,8),label,font=font,fill='#29443e')
compare.save(OUT/'master-comparison.png')
html=(SRC/'index.html').read_text(encoding='utf-8').replace('16 帧身体与脸部微调审核预览','16 帧脚掌微调审核预览')
(OUT/'index.html').write_text(html,encoding='utf-8')
baseline=json.loads((RUN/'imagegen-jobs-v5.json').read_text())['runtimeBaseline']
integrity={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in baseline.items()};assert all(integrity.values())
g=Image.open(OUT/'smaller-feet.gif');total=0
for i in range(g.n_frames):g.seek(i);total+=g.info['duration']
assert g.n_frames==16 and total==3220
(OUT/'qa.json').write_text(json.dumps({'stage':'pending_user_review','source':'preview-v8/frames','method':'separate local foot contraction: width -10%, height up to -8%, ground anchored, body attachment protected','frameCount':16,'durationMs':total,'runtimeUnchanged':integrity,'sourceSHA256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((SRC/'frames').glob('*.png'))},'frames':checks},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'out':str(OUT),'frames':16,'durationMs':total,'runtimeUnchanged':all(integrity.values())}))
