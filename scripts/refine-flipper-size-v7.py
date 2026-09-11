"""Small, user-requested flipper reduction of the approved v6 frames."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont
ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'output/flipper-hold-draft-2026-09-10'
SRC=RUN/'preview-v6';OUT=RUN/'preview-v7';(OUT/'frames').mkdir(parents=True,exist_ok=True)
# Shoulder and tip landmarks, in the existing 420 x 360 review coordinate space.
POSES=[
 ((141,159),(80,240),(239,164),(293,249)),
 ((153,147),(70,218),(251,181),(286,245)),
 ((153,159),(54,192),(240,181),(301,199)),
 ((135,169),(81,255),(231,166),(239,211)),
 ((148,155),(44,195),(237,177),(299,200)),
 ((145,164),(70,239),(238,164),(286,211)),
 ((139,169),(63,212),(234,171),(297,214)),
 ((132,163),(43,222),(229,158),(300,179)),
 ((142,166),(67,231),(239,176),(297,220)),
 ((144,160),(44,184),(238,175),(296,222)),
 ((139,151),(41,181),(235,158),(298,190)),
 ((147,175),(46,239),(245,178),(292,218)),
 ((144,168),(36,207),(232,180),(284,213)),
 ((143,163),(35,208),(230,169),(300,162)),
 ((140,165),(65,236),(233,171),(287,231)),
 ((142,168),(71,231),(238,172),(288,221))]

def smooth(v):
    v=np.clip(v,0,1);return v*v*(3-2*v)

def sample(a,x,y):
    h,w=a.shape[:2];x=np.clip(x,0,w-1);y=np.clip(y,0,h-1)
    x0=x.astype(int);y0=y.astype(int);x1=np.minimum(x0+1,w-1);y1=np.minimum(y0+1,h-1)
    fx=(x-x0)[...,None];fy=(y-y0)[...,None]
    return (a[y0,x0]*(1-fx)+a[y0,x1]*fx)*(1-fy)+(a[y1,x0]*(1-fx)+a[y1,x1]*fx)*fy

def shrink(im,pose,index):
    a=np.array(im).astype(float);h,w=a.shape[:2];yy,xx=np.mgrid[:h,:w].astype(float)
    # Preserve the cream face/torso and their surrounding original outlines.
    cream=(a[:,:,0]>185)&(a[:,:,1]>175)&(a[:,:,2]>105)&(a[:,:,0]-a[:,:,1]<55)&(a[:,:,3]>100)&(xx<260)
    protect=Image.fromarray((cream*255).astype('uint8')).filter(ImageFilter.MaxFilter(33)).filter(ImageFilter.GaussianBlur(7))
    protect=np.array(protect)/255
    protect=np.maximum(protect,1-smooth((yy-120)/25))
    protect=np.maximum(protect,smooth((yy-264)/15))
    hand=(a[:,:,0]>180)&(a[:,:,1]>100)&(a[:,:,2]<190)&(a[:,:,0]-a[:,:,1]>35)&(a[:,:,3]>150)&(xx>255)&(yy>125)&(yy<270)
    ys,xs=np.where(hand);handleft=int(xs.min());handtop=int(ys.min());handbottom=int(ys.max())
    right_delta=-.10*(np.array(pose[3])-np.array(pose[2]))
    # Release poses move the hand with the same small shift, preserving gaps.
    def displacement(x,y):
        dx=np.zeros_like(x);dy=np.zeros_like(y)
        for root,tip in [(pose[0],pose[1]),(pose[2],pose[3])]:
            root=np.array(root);v=np.array(tip)-root;length=np.linalg.norm(v);u=v/length
            px=x-root[0];py=y-root[1];s=px*u[0]+py*u[1];t=-px*u[1]+py*u[0]
            weight=smooth((s+3)/24)*(1-smooth((s-length-5)/35))*(1-smooth((np.abs(t)-22)/25))
            dx+=-.10*px*weight;dy+=-.10*py*weight
        handweight=smooth((x-handleft+28)/32)*smooth((y-handtop+40)/32)*(1-smooth((y-handbottom-8)/32))
        dx=dx*(1-handweight)+right_delta[0]*handweight
        dy=dy*(1-handweight)+right_delta[1]*handweight
        p=sample(protect[:,:,None],x,y)[:,:,0]
        return dx*(1-p),dy*(1-p)
    dx,dy=displacement(xx,yy);field=np.stack([dx,dy],axis=2)
    mx=xx.copy();my=yy.copy()
    for _ in range(36):
        delta=sample(field,mx,my)
        mx=.4*mx+.6*(xx-delta[:,:,0]);my=.4*my+.6*(yy-delta[:,:,1])
    premult=a.copy();premult[:,:,:3]*=premult[:,:,3:4]/255
    result=sample(premult,mx,my)
    result[:,:,:3]=np.divide(result[:,:,:3]*255,result[:,:,3:4],out=np.zeros_like(result[:,:,:3]),where=result[:,:,3:4]>0)
    result=np.clip(np.rint(result),0,255).astype('uint8');result[result[:,:,3]==0]=0
    fixed=(protect==1)|cream;result[fixed]=a.astype('uint8')[fixed]
    # Positive Jacobian is necessary to prevent folds/duplicated contours.
    gyx,gxx=np.gradient(mx);gyy,gxy=np.gradient(my);jac=gxx*gyy-gyx*gxy
    assert jac.min()>.35,(index,float(jac.min()),np.unravel_index(np.argmin(jac),jac.shape))
    return Image.fromarray(result),{'frame':index,'minimumInverseJacobian':float(jac.min()),'protectedPixelsUnchanged':bool(np.array_equal(result[fixed],a.astype('uint8')[fixed])),'handShiftXY':right_delta.tolist()}

original=[Image.open(p).convert('RGBA') for p in sorted((SRC/'frames').glob('*.png'))]
frames=[];checks=[]
for i,(im,pose) in enumerate(zip(original,POSES)):
    out,check=shrink(im,pose,i+1);out.save(OUT/'frames'/f'frame_{i+1:02d}.png');frames.append(out);checks.append(check)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
durations=[220,180,160,260,180,220,180,200,180,180,220,180,180,220,200,260]
board=Image.new('RGB',(1680,1540),'#dae4e3');d=ImageDraw.Draw(board);gif=[]
for i,im in enumerate(frames):
    x=i%4*420;y=i//4*385;board.paste(im,(x,y+22),im);d.text((x+10,y+3),f'{i+1:02d}',font=font,fill='#29443e')
    bg=Image.new('RGB',(420,380),'#dae4e3');bg.paste(im,(0,15),im);gif.append(bg)
board.save(OUT/'contact-sheet.png');gif[0].save(OUT/'smaller-flippers.gif',save_all=True,append_images=gif[1:],duration=durations,loop=0,disposal=2)
compare=Image.new('RGB',(840,800),'#dae4e3');d=ImageDraw.Draw(compare)
for row,index in enumerate([0,7]):
    for col,(label,im) in enumerate([('调整前',original[index]),('翅膀缩小后',frames[index])]):
        compare.paste(im,(col*420,row*400+30),im);d.text((col*420+12,row*400+8),label,font=font,fill='#29443e')
compare.save(OUT/'wing-comparison.png')
html=(SRC/'index.html').read_text(encoding='utf-8').replace('16 帧身材微调审核预览','16 帧翅膀微调审核预览').replace('master-comparison.png','wing-comparison.png').replace('母版／调整前／调整后','翅膀调整前后').replace('落脚修订','开心踮脚').replace('追手接触修订','追手轻碰')
(OUT/'index.html').write_text(html,encoding='utf-8')
baseline=json.loads((RUN/'imagegen-jobs-v5.json').read_text())['runtimeBaseline']
integrity={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in baseline.items()}
assert all(integrity.values())
(OUT/'qa.json').write_text(json.dumps({'stage':'pending_user_review','source':'preview-v6/frames','method':'local continuous 10% wing contraction with protected face/torso/feet; small matching hand translation','durationMs':sum(durations),'frameCount':len(frames),'runtimeUnchanged':integrity,'frames':checks},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'out':str(OUT),'frames':len(frames),'minimumJacobian':min(c['minimumInverseJacobian'] for c in checks),'runtimeUnchanged':all(integrity.values())}))
