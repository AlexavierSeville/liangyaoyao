"""Review-only local wing shortening of the approved identity direction.

No generation, runtime edits, or edits to the accepted handshake frames.
Landmarks refer to the 520 x 360 preview-v2 canvases (screen left/right).
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'output/flipper-identity-unification-2026-09-11'
OLD = ROOT / 'output/flipper-hold-draft-2026-09-10'
SRC = RUN / 'preview-v2'
OUT = RUN / 'preview-v3'
FONT = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 17)
BG = '#dae4e3'
DURATIONS = [220,180,160,260,180,220,180,200,180,180,220,180,180,220,200,260]
# Per frame: left shoulder/tip, right shoulder/tip.
POSES = {
    'left': [
        ((207,160),(149,253),(302,163),(349,251)),
        ((206,163),(149,251),(302,166),(347,252)),
        ((207,173),(149,128),(309,170),(348,245)),
        ((195,162),(150,95),(298,171),(353,232)),
        ((215,161),(158,239),(310,164),(356,245)),
        ((208,163),(164,253),(310,165),(352,246)),
        ((207,164),(164,251),(310,164),(352,248)),
        ((208,167),(180,218),(306,166),(350,249)),
        ((196,165),(171,246),(298,166),(339,245)),
        ((213,166),(177,246),(309,169),(347,246)),
        ((210,166),(168,243),(312,169),(335,248)),
        ((210,166),(166,243),(313,169),(336,248)),
    ],
    'right': [
        ((213,164),(170,261),(311,164),(365,245)),
        ((211,166),(165,261),(310,167),(360,245)),
        ((213,176),(182,266),(310,161),(352,115)),
        ((200,164),(132,224),(306,158),(336,99)),
        ((210,170),(177,268),(307,165),(353,251)),
        ((209,171),(178,267),(310,168),(349,256)),
        ((209,171),(178,266),(310,168),(349,256)),
        ((205,171),(166,264),(300,173),(290,239)),
        ((222,165),(195,252),(322,166),(316,228)),
        ((211,165),(182,254),(310,163),(308,228)),
        ((207,168),(185,249),(320,169),(315,228)),
        ((210,168),(188,249),(320,169),(315,228)),
    ],
}


def smooth(v):
    v = np.clip(v, 0, 1)
    return v*v*(3-2*v)


def sample(a, x, y):
    h,w = a.shape[:2]
    x = np.clip(x, 0, w-1); y = np.clip(y, 0, h-1)
    x0=x.astype(int); y0=y.astype(int)
    x1=np.minimum(x0+1,w-1); y1=np.minimum(y0+1,h-1)
    fx=(x-x0)[...,None]; fy=(y-y0)[...,None]
    return (a[y0,x0]*(1-fx)+a[y0,x1]*fx)*(1-fy)+(a[y1,x0]*(1-fx)+a[y1,x1]*fx)*fy


def shorten(im, side, index):
    a=np.array(im); h,w=a.shape[:2]; yy,xx=np.mgrid[:h,:w].astype(float)
    pose=POSES[side][index]
    # The whole head and feet remain fixed, including their dark outline.
    head_radius=np.sqrt(((xx-260)/83)**2+((yy-106)/66)**2)
    head=1-smooth((head_radius-1.0)/.17)
    head=np.maximum(head,1-smooth((yy-70)/15))
    feet=smooth((yy-275)/12)
    cream=(a[:,:,0]>183)&(a[:,:,1]>170)&(a[:,:,2]>105)&(a[:,:,0].astype(float)-a[:,:,1]<55)&(a[:,:,3]>100)
    cream=np.array(Image.fromarray((cream*255).astype('uint8')).filter(ImageFilter.MaxFilter(21)).filter(ImageFilter.GaussianBlur(4)))/255
    dx=np.zeros_like(xx); dy=np.zeros_like(yy)
    for j in range(2):
        root=np.array(pose[j*2]); tip=np.array(pose[j*2+1]); v=tip-root
        length=np.linalg.norm(v); u=v/length
        px=xx-root[0]; py=yy-root[1]
        s=px*u[0]+py*u[1]; t=-px*u[1]+py*u[0]
        folded=index>=7 and j==(0 if side=='left' else 1)
        amount=.14 if folded else .18
        weight=smooth((s+4)/25)*(1-smooth((s-length-6)/40))*(1-smooth((abs(t)-25)/24))
        protect=np.maximum(head,feet)
        if not folded:
            protect=np.maximum(protect,cream)
        # Contract length; retain the existing rounded wing thickness.
        weight*=1-protect
        dx-=amount*s*u[0]*weight
        dy-=amount*s*u[1]*weight
    # Hands retain their shape. Contact poses follow the newly shortened tip.
    hand=(a[:,:,0]>185)&(a[:,:,1]>100)&(a[:,:,2]<200)&(a[:,:,0].astype(float)-a[:,:,1]>35)&(a[:,:,3]>100)&(yy>130)&(yy<275)
    hand &= (xx<160) if side=='left' else (xx>355)
    shift=np.zeros(2)
    if hand.any():
        hy,hx=np.where(hand)
        hw=smooth((xx-hx.min()+33)/30)*(1-smooth((xx-hx.max()-3)/30))*smooth((yy-hy.min()+33)/30)*(1-smooth((yy-hy.max()-3)/30))
        if index in ([0,1,4] if side=='left' else [0,1]):
            j=0 if side=='left' else 2
            shift=-.18*(np.array(pose[j+1])-np.array(pose[j]))
        dx=dx*(1-hw)+shift[0]*hw; dy=dy*(1-hw)+shift[1]*hw
    # Smooth the displacement (not the artwork) to avoid steep local folds.
    def blur_field(v):
        offsets=np.arange(-18,19,dtype=float)
        kernel=np.exp(-.5*(offsets/6)**2); kernel/=kernel.sum()
        v=np.apply_along_axis(lambda row:np.convolve(row,kernel,mode='same'),0,v)
        return np.apply_along_axis(lambda row:np.convolve(row,kernel,mode='same'),1,v)
    anchors=1-np.maximum(head,feet)
    dx=blur_field(dx)*anchors; dy=blur_field(dy)*anchors
    field=np.stack([dx,dy],axis=2)
    mx=xx.copy(); my=yy.copy()
    for _ in range(40):
        delta=sample(field,mx,my)
        mx=.4*mx+.6*(xx-delta[:,:,0]); my=.4*my+.6*(yy-delta[:,:,1])
    pre=a.astype(float); pre[:,:,:3]*=pre[:,:,3:4]/255
    out=sample(pre,mx,my)
    out[:,:,:3]=np.divide(out[:,:,:3]*255,out[:,:,3:4],out=np.zeros_like(out[:,:,:3]),where=out[:,:,3:4]>0)
    out=np.clip(np.rint(out),0,255).astype('uint8'); out[out[:,:,3]==0]=0
    fixed=(head==1)|(feet==1)
    out[fixed]=a[fixed]
    gyx,gxx=np.gradient(mx); gyy,gxy=np.gradient(my); jac=gxx*gyy-gyx*gxy
    assert jac.min()>.25,(side,index,float(jac.min()),np.unravel_index(np.argmin(jac),jac.shape))
    assert np.array_equal(out[fixed],a[fixed])
    result=Image.fromarray(out); box=result.getbbox()
    assert box[0]>0 and box[1]>0 and box[2]<w and box[3]<h
    return result, {'frame':index+1,'minimumInverseJacobian':float(jac.min()),'headAndFeetExact':True,'handShiftXY':shift.tolist(),'bounds':box}


def card(im, label, size=(520,400)):
    out=Image.new('RGB',size,BG); out.paste(im,(0,30),im)
    ImageDraw.Draw(out).text((12,5),label,font=FONT,fill='#29443e')
    return out


def gif(path, pics, durations):
    pics[0].save(path,save_all=True,append_images=pics[1:],duration=durations,loop=0,disposal=2)


def main():
    checks={}; allframes={}; before={}; holds={}
    protected_paths=list((OLD/'final-right-flipper'/'frames').glob('*.png'))+list((OLD/'preview-left-v1'/'frames').glob('*.png'))
    protected_paths += [ROOT/'src/config/animations.json', ROOT/'src/config/animation-registry.json', ROOT/'src/behavior/PetInteractionController.ts']
    protected_paths=[p for p in protected_paths if p.exists()]
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected_paths}
    for side in ['left','right']:
        dest=OUT/side/'frames'; dest.mkdir(parents=True,exist_ok=True)
        source=[Image.open(p).convert('RGBA') for p in sorted((SRC/side/'frames').glob('*.png'))]
        assert len(source)==12
        frames=[]; metrics=[]
        for i,im in enumerate(source):
            result,metric=shorten(im,side,i); result.save(dest/f'frame_{i+1:02d}.png')
            frames.append(result); metrics.append(metric)
        before[side]=source; allframes[side]=frames; checks[side]=metrics
        board=Image.new('RGB',(2080,1200),BG)
        for i,im in enumerate(frames): board.paste(card(im,f'{i+1:02d}'),(i%4*520,i//4*400))
        board.save(OUT/side/'contact-sheet.png')
        gif(OUT/side/'reaction.gif',[card(im,'不耐烦 · 翅膀收短后') for im in frames],[125]*12)
        comparisons=[]
        for a,b in zip(source,frames):
            c=Image.new('RGB',(1040,400),BG); c.paste(card(a,'调整前'),(0,0)); c.paste(card(b,'翅膀收短后'),(520,0)); comparisons.append(c)
        gif(OUT/f'{side}-wing-comparison.gif',comparisons,[250]*12)
        folder=OLD/('preview-left-v1' if side=='left' else 'final-right-flipper')/'frames'
        hold=[]
        for p in sorted(folder.glob('*.png')):
            im=Image.new('RGBA',(520,360)); im.alpha_composite(Image.open(p).convert('RGBA'),(0 if side=='left' else 70,0)); hold.append(im)
        assert len(hold)==16
        holds[side]=hold
        gif(OUT/side/'continuity.gif',[card(im,'轻抚与握手') for im in hold]*2+[card(im,'持续触摸 · 不耐烦') for im in frames],DURATIONS*2+[125]*12)
    # At matched body height: the master, previous reaction and shortened result.
    master=Image.open(OLD/'references/canonical-front.png').convert('RGBA'); box=master.getbbox(); master=master.crop(box)
    master=master.resize((round(master.width*280/master.height),280),Image.Resampling.LANCZOS)
    m=Image.new('RGBA',(520,360)); m.alpha_composite(master,(260-master.width//2,50))
    comparison=Image.new('RGB',(1560,1600),BG)
    for row,(side,i) in enumerate([('left',0),('right',0),('left',3),('right',7)]):
        for col,(im,label) in enumerate([(m,'母版 · 同身高对照'),(before[side][i],f'{side} {i+1:02d} · 调整前'),(allframes[side][i],'翅膀收短后')]):
            comparison.paste(card(im,label),(col*520,row*400))
    comparison.save(OUT/'master-wing-comparison.png')
    seq={side:holds[side]*2+allframes[side] for side in holds}; pics=[]
    for i,(l,r) in enumerate(zip(seq['left'],seq['right'])):
        p=Image.new('RGB',(1040,400),BG)
        state='轻抚与握手' if i<32 else '持续触摸 · 不耐烦'
        p.paste(card(l,'左侧 · '+state),(0,0)); p.paste(card(r,'右侧 · '+state),(520,0)); pics.append(p)
    gif(OUT/'both-continuity.gif',pics,DURATIONS*2+[125]*12)
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
    (OUT/'qa.json').write_text(json.dumps({'status':'candidate_pending_user_review','source':'preview-v2','method':'wing-axis contraction: 18% extended, 14% folded; stationary head and feet; rigid hand follow on contact','runtimeEdited':False,'acceptedHoldHashes':hashes,'checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>翅膀长度微调审核</title>
<style>body{background:#dae4e3;color:#29443e;font:17px Microsoft YaHei;margin:24px}img{max-width:100%}a{color:#28604b}</style>
<h2>翅膀收短 · 审核候选</h2><p>左右各 12 帧；垂翅和抬翅局部收短，抱翅轻收。保留头脸、脚和动作节奏。素材预演，尚未替换正式程序。</p>
<h3>轻抚与握手 → 不耐烦</h3><img src="both-continuity.gif">
<h3>母版与调整前后（同身高）</h3><img src="master-wing-comparison.png">
<h3>左侧全动作比较</h3><img src="left-wing-comparison.gif"><h3>右侧全动作比较</h3><img src="right-wing-comparison.gif">
<p><a href="left/contact-sheet.png">左侧逐帧</a> · <a href="right/contact-sheet.png">右侧逐帧</a></p>''',encoding='utf-8')
    print(json.dumps({'out':str(OUT),'frames':24,'minimumInverseJacobian':min(c['minimumInverseJacobian'] for cc in checks.values() for c in cc)}))


if __name__=='__main__':
    main()
