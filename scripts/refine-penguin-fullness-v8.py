"""User-requested slight body and face enlargement of v7, review only."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'output/flipper-hold-draft-2026-09-10'
SRC=RUN/'preview-v7';OUT=RUN/'preview-v8';(OUT/'frames').mkdir(parents=True,exist_ok=True)

def smooth(a):
    a=np.clip(a,0,1);return a*a*(3-2*a)

def sample(a,x,y):
    h,w=a.shape[:2];x=np.clip(x,0,w-1);y=np.clip(y,0,h-1)
    x0=x.astype(int);y0=y.astype(int);x1=np.minimum(x0+1,w-1);y1=np.minimum(y0+1,h-1)
    fx=(x-x0)[...,None];fy=(y-y0)[...,None]
    return (a[y0,x0]*(1-fx)+a[y0,x1]*fx)*(1-fy)+(a[y1,x0]*(1-fx)+a[y1,x1]*fx)*fy

def refine(im):
    a=np.array(im).astype(float);h,w=a.shape[:2];yy,xx=np.mgrid[:h,:w].astype(float)
    top=im.getbbox()[1]
    head=(a[:,:,3]>160)&(yy<top+55)
    hx=(np.where(head)[1].min()+np.where(head)[1].max())/2;hy=top+65
    cream=(a[:,:,0]>200)&(a[:,:,1]>185)&(a[:,:,2]>125)&(a[:,:,0]-a[:,:,1]<55)&(a[:,:,3]>180)&(xx<250)&(yy>195)&(yy<275)
    bx=(np.where(cream)[1].min()+np.where(cream)[1].max())/2
    # Enlarge the head/face very slightly; fade into the original shoulder.
    hw=(1-smooth((yy-top-94)/35))*(1-smooth((np.abs(xx-hx)-75)/24))
    # Add fullness across the torso, fading before the feet and outer wings.
    bw=smooth((yy-top-106)/40)*(1-smooth((yy-270)/20))*(1-smooth((np.abs(xx-bx)-70)/35))
    dx=.025*(xx-hx)*hw+.04*(xx-bx)*bw
    dy=.02*(yy-hy)*hw
    # Hands stay in place; the original small wings blend at their attachment.
    keep=1-smooth((xx-247)/13);dx*=keep;dy*=keep
    field=np.stack([dx,dy],axis=2);mx=xx.copy();my=yy.copy()
    for _ in range(12):
        delta=sample(field,mx,my);mx=xx-delta[:,:,0];my=yy-delta[:,:,1]
    p=a.copy();p[:,:,:3]*=p[:,:,3:4]/255;v=sample(p,mx,my)
    v[:,:,:3]=np.divide(v[:,:,:3]*255,v[:,:,3:4],out=np.zeros_like(v[:,:,:3]),where=v[:,:,3:4]>0)
    v=np.clip(np.rint(v),0,255).astype('uint8');v[v[:,:,3]==0]=0
    fixed=(np.abs(mx-xx)<1e-9)&(np.abs(my-yy)<1e-9);v[fixed]=a.astype('uint8')[fixed]
    gyx,gxx=np.gradient(mx);gyy,gxy=np.gradient(my);jac=gxx*gyy-gyx*gxy
    assert jac.min()>.7
    assert np.array_equal(v[290:],a.astype('uint8')[290:])
    assert np.array_equal(v[:,260:],a.astype('uint8')[:,260:])
    out=Image.fromarray(v);bb=out.getbbox();assert 0<bb[0]<bb[2]<w and 0<bb[1]<bb[3]<h
    return out,{'headCenter':[float(hx),float(hy)],'bodyCenterX':float(bx),'minimumInverseJacobian':float(jac.min()),'feetAndOuterHandPixelsUnchanged':True,'bounds':bb}

original=[Image.open(p).convert('RGBA') for p in sorted((SRC/'frames').glob('*.png'))]
assert len(original)==16
frames=[];checks=[]
for i,im in enumerate(original):
    out,check=refine(im);out.save(OUT/'frames'/f'frame_{i+1:02d}.png');frames.append(out);checks.append({'frame':i+1,**check})
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
durations=[220,180,160,260,180,220,180,200,180,180,220,180,180,220,200,260]
board=Image.new('RGB',(1680,1540),'#dae4e3');d=ImageDraw.Draw(board);gif=[]
for i,im in enumerate(frames):
    x=i%4*420;y=i//4*385;board.paste(im,(x,y+22),im);d.text((x+10,y+3),f'{i+1:02d}',font=font,fill='#29443e')
    bg=Image.new('RGB',(420,380),'#dae4e3');bg.paste(im,(0,15),im);gif.append(bg)
board.save(OUT/'contact-sheet.png');gif[0].save(OUT/'fuller-body-face.gif',save_all=True,append_images=gif[1:],duration=durations,loop=0,disposal=2)
master=Image.open(RUN/'references/canonical-front.png').convert('RGBA');master=master.crop(master.getbbox());master=master.resize((round(master.width*280/master.height),280),Image.Resampling.LANCZOS)
mc=Image.new('RGBA',(420,360));mc.alpha_composite(master,(190-master.width//2,50))
compare=Image.new('RGB',(1260,400),'#dae4e3');d=ImageDraw.Draw(compare)
for i,(label,im) in enumerate([('母版',mc),('微调前 v7',original[0]),('身体、脸微调后 v8',frames[0])]):
    compare.paste(im,(i*420,30),im);d.text((i*420+12,8),label,font=font,fill='#29443e')
compare.save(OUT/'master-comparison.png')
html=(SRC/'index.html').read_text(encoding='utf-8').replace('16 帧翅膀微调审核预览','16 帧身体与脸部微调审核预览').replace('wing-comparison.png','master-comparison.png').replace('翅膀调整前后','母版／微调前／微调后')
(OUT/'index.html').write_text(html,encoding='utf-8')
baseline=json.loads((RUN/'imagegen-jobs-v5.json').read_text())['runtimeBaseline']
integrity={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in baseline.items()};assert all(integrity.values())
g=Image.open(OUT/'fuller-body-face.gif');total=0
for i in range(g.n_frames):g.seek(i);total+=g.info['duration']
assert g.n_frames==16 and total==3220
q={'stage':'pending_user_review','source':'preview-v7/frames','method':'continuous local inverse warp; torso horizontal +4%, head/face horizontal +2.5%, vertical +2%, with smooth shoulder/feet/outer-wing attenuation','frameCount':len(frames),'durationMs':total,'runtimeUnchanged':integrity,'sourceSHA256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((SRC/'frames').glob('*.png'))},'frames':checks}
(OUT/'qa.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'out':str(OUT),'frames':len(frames),'durationMs':total,'runtimeUnchanged':all(integrity.values())}))
