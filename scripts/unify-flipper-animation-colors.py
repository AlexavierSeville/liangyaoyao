"""Match both interaction sequences to one approved palette, without warping."""
from pathlib import Path
import hashlib, json, importlib.util
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('preview',ROOT/'scripts/shorten-unified-reaction-flippers.py')
preview=importlib.util.module_from_spec(spec); spec.loader.exec_module(preview)
RUN=preview.RUN; OLD=preview.OLD; SRC=RUN/'preview-v3'; OUT=RUN/'preview-v4-color'
M=np.array([[.4124564,.3575761,.1804375],[.2126729,.7151522,.0721750],[.0193339,.1191920,.9503041]])
WHITE=np.array([.95047,1,1.08883])


def lab(rgb):
    s=rgb/255
    linear=np.where(s<=.04045,s/12.92,((s+.055)/1.055)**2.4)
    xyz=(linear@M.T)/WHITE
    f=np.where(xyz>(6/29)**3,np.cbrt(xyz),xyz/(3*(6/29)**2)+4/29)
    return np.stack([116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])],axis=-1)


def rgb(values):
    fy=(values[...,0]+16)/116
    f=np.stack([fy+values[...,1]/500,fy,fy-values[...,2]/200],axis=-1)
    xyz=np.where(f>6/29,f**3,3*(6/29)**2*(f-4/29))*WHITE
    linear=xyz@np.linalg.inv(M).T
    s=np.where(linear<=.0031308,12.92*linear,1.055*np.maximum(linear,0)**(1/2.4)-.055)
    return np.clip(np.rint(s*255),0,255).astype('uint8')


def masks(a):
    y,x=np.mgrid[:a.shape[0],:a.shape[1]]
    r,g,b,alpha=a.astype(float).transpose(2,0,1)
    valid=(alpha>250)&(x>175)&(x<330)
    return {
        'feather':valid&(x>210)&(x<300)&(y>65)&(y<95)&(r>60)&(r<170)&(abs(r-g)<30)&(abs(g-b)<30),
        'cream':valid&(y>200)&(y<265)&(r>205)&(g>195)&(b>125)&(b<240)&(r-g<35),
        'orange':valid&(y>290)&(r>220)&(g>100)&(g<205)&(b<95),
    }


def palette(frames):
    pools={k:[] for k in ['feather','cream','orange']}
    for im in frames:
        a=np.array(im); values=lab(a[:,:,:3].astype(float))
        for k,mask in masks(a).items(): pools[k].append(values[mask])
    return {k:np.median(np.concatenate(v),axis=0) for k,v in pools.items()}


def correct(im, shifts, side):
    a=np.array(im); r,g,b,alpha=a.astype(float).transpose(2,0,1)
    y,x=np.mgrid[:a.shape[0],:a.shape[1]]; sm=preview.smooth
    values=lab(a[:,:,:3].astype(float))
    weights={
        'feather':(1-sm((r-170)/40))*(1-sm((r-g-32)/18))*sm((values[:,:,0]-10)/15),
        'cream':sm((g-170)/35)*(1-sm((r-g-30)/20))*sm((b-110)/45),
        'orange':sm((r-g-40)/35)*sm((g-b-40)/35)*(((y>280)&(x>135)&(x<380))|((y>95)&(y<175)&(x>190)&(x<335))),
    }
    # Isolate the human hand so its skin and drawn outline are unchanged.
    hand=(r>170)&(r-g>35)&(g>70)&(y>130)&(y<275)&((x<180) if side=='left' else (x>337))&(alpha>0)
    hand=np.array(Image.fromarray((hand*255).astype('uint8')).filter(ImageFilter.MaxFilter(5)))>0
    delta=np.zeros_like(values)
    for k,weight in weights.items(): delta+=weight[:,:,None]*shifts[k]
    corrected=rgb(values+delta); result=a.copy(); result[:,:,:3]=corrected
    fixed=hand|(alpha==0)|(np.max(abs(delta),axis=2)<.00001)
    result[fixed]=a[fixed]
    assert np.array_equal(result[:,:,3],a[:,:,3])
    assert np.array_equal(result[hand],a[hand])
    return Image.fromarray(result), {'alphaExact':True,'handPixelsExact':True,'geometryExact':True}


def aligned(im, shift=0):
    out=Image.new('RGBA',(520,360));out.alpha_composite(im,(shift,0));return out


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    before={}; after={}; sources={}; reports={}
    for side in ['left','right']:
        hf=OLD/('preview-left-v1' if side=='left' else 'final-right-flipper')/'frames'
        hp=sorted(hf.glob('*.png')); rp=sorted((SRC/side/'frames').glob('*.png'))
        assert len(hp)==16 and len(rp)==12
        for p in hp+rp:sources[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
        before[side]={'hold':[aligned(Image.open(p).convert('RGBA'),70 if side=='right' else 0) for p in hp],
                      'reaction':[Image.open(p).convert('RGBA') for p in rp]}
    target=palette([before['right']['hold'][0]])
    for side in before:
        after[side]={k:[None]*len(v) for k,v in before[side].items()}; reports[side]=[]
        groups=[('hold',list(range(8))+([15] if side=='left' else [])),
                ('hold',list(range(8,15 if side=='left' else 16))),('reaction',list(range(12)))]
        for action,ids in groups:
            src=palette([before[side][action][i] for i in ids]); shifts={k:target[k]-src[k] for k in target}
            for i in ids:
                after[side][action][i],checks=correct(before[side][action][i],shifts,side)
            dst=palette([after[side][action][i] for i in ids])
            reports[side].append({'action':action,'frames':[i+1 for i in ids],'LabShifts':{k:v.tolist() for k,v in shifts.items()},
                'medianDeltaE76Before':{k:float(np.linalg.norm(src[k]-target[k])) for k in target},
                'medianDeltaE76After':{k:float(np.linalg.norm(dst[k]-target[k])) for k in target},**checks})
        for action,frames in after[side].items():
            folder=OUT/side/('hold-frames' if action=='hold' else 'frames'); folder.mkdir(parents=True,exist_ok=True)
            for i,im in enumerate(frames): im.save(folder/f'frame_{i+1:02d}.png')
            cols=4; rows=(len(frames)+3)//4; board=Image.new('RGB',(2080,400*rows),preview.BG)
            for i,im in enumerate(frames):board.paste(preview.card(im,f'{i+1:02d}'),(i%4*520,i//4*400))
            board.save(OUT/side/f'{action}-contact-sheet.png')
        seq=after[side]['hold']*2+after[side]['reaction']
        preview.gif(OUT/side/'continuity.gif',[preview.card(im,'轻抚与握手' if i<32 else '持续触摸 · 不耐烦') for i,im in enumerate(seq)],preview.DURATIONS*2+[125]*12)
        oldseq=before[side]['hold']*2+before[side]['reaction']; pics=[]
        for i,(a,b) in enumerate(zip(oldseq,seq)):
            p=Image.new('RGB',(1040,400),preview.BG);state='握手' if i<32 else '不耐烦'
            p.paste(preview.card(a,'校色前 · '+state),(0,0));p.paste(preview.card(b,'统一色板后 · '+state),(520,0));pics.append(p)
        preview.gif(OUT/f'{side}-before-after.gif',pics,preview.DURATIONS*2+[125]*12)
    board=Image.new('RGB',(1560,800),preview.BG)
    for row,side in enumerate(['left','right']):
        for col,(im,label) in enumerate([(after[side]['hold'][-1],'握手末帧 · 统一色板'),(before[side]['reaction'][0],'不耐烦 · 校色前'),(after[side]['reaction'][0],'不耐烦 · 校色后')]):
            board.paste(preview.card(im,('左侧 · ' if side=='left' else '右侧 · ')+label),(col*520,row*400))
    board.save(OUT/'color-comparison.png')
    pics=[]
    for i in range(44):
        p=Image.new('RGB',(1040,400),preview.BG)
        for col,side in enumerate(['left','right']):
            seq=after[side]['hold']*2+after[side]['reaction'];state='轻抚与握手' if i<32 else '持续触摸 · 不耐烦'
            p.paste(preview.card(seq[i],('左侧 · ' if side=='left' else '右侧 · ')+state),(col*520,0))
        pics.append(p)
    preview.gif(OUT/'both-continuity.gif',pics,preview.DURATIONS*2+[125]*12)
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in sources.items())
    baseline=json.loads((OLD/'imagegen-jobs-v5.json').read_text(encoding='utf-8'))['runtimeBaseline']
    integrity={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in baseline.items()};assert all(integrity.values())
    report={'status':'pending_user_review','paletteAnchor':str(OLD/'final-right-flipper/frames/frame_01.png'),
            'method':'shared material Lab offsets per original generation batch; no per-frame histogram fitting',
            'targetLab':{k:v.tolist() for k,v in target.items()},'groups':reports,'sourceHashesUnchanged':sources,'runtimeUnchanged':integrity}
    (OUT/'qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>握手与不耐烦颜色统一审核</title>
<style>body{background:#dae4e3;color:#29443e;font:17px Microsoft YaHei;margin:24px}img{max-width:100%}a{color:#28604b}</style>
<h2>握手 → 不耐烦：统一颜色候选</h2><p>以已定稿的右侧握手第 1 帧作为共同色板，分别校正羽毛、脸肚、喙脚。两段动作同用这一色板，透明度与姿势不变。以下为素材预演，未替换正式程序。</p>
<h3>切换处颜色对照</h3><img src="color-comparison.png"><h3>左右连贯演示</h3><img src="both-continuity.gif">
<h3>左侧校色前后</h3><img src="left-before-after.gif"><h3>右侧校色前后</h3><img src="right-before-after.gif">''',encoding='utf-8')
    print(json.dumps({'out':str(OUT),'frames':56,'groups':reports},ensure_ascii=False))


if __name__=='__main__':main()
