"""User-authorized deterministic hand replacement. Writes review assets only."""
from pathlib import Path
import json
import math
import hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'output/touch-hold-draft-2026-09-09'
OUT = RUN / 'candidate-v6-composite'
SOURCE = RUN / 'decoded/belly-hold-draft-v5-hand-local-repair.png'
BOXES = [(152,276,222,330),(414,290,480,342),(671,300,737,351),
         (928,316,994,369),(1182,333,1248,386),(1433,338,1501,392),
         (109,799,181,854),(344,799,415,854),(555,788,632,847),
         (809,763,878,821),(1071,730,1143,790),(1416,725,1488,785)]


def sample(rgb, x, y):
    h,w=rgb.shape[:2]
    x=np.clip(x,0,w-1); y=np.clip(y,0,h-1)
    x0=x.astype(int); y0=y.astype(int)
    x1=np.minimum(x0+1,w-1); y1=np.minimum(y0+1,h-1)
    fx=(x-x0)[...,None]; fy=(y-y0)[...,None]
    return (rgb[y0,x0]*(1-fx)+rgb[y0,x1]*fx)*(1-fy)+(rgb[y1,x0]*(1-fx)+rgb[y1,x1]*fx)*fy


def mask_hand(rgb, box):
    x0,y0,x1,y1=box
    r,g,b=(rgb[:,:,k] for k in range(3))
    roi=np.zeros(r.shape,bool); roi[y0:y1,x0:x1]=True
    skin=roi&(r-g>24)&(g-b>16)&(r>155)&(g>85)
    m=Image.fromarray((skin*255).astype('uint8'))
    # Close the small gaps in the rendered outline without including belly.
    m=m.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    return m


def remove_hand(rgb, mask, frame_index):
    h,w=rgb.shape[:2]; yy,xx=np.mgrid[:h,:w]
    r,g,b=(rgb[:,:,k] for k in range(3))
    cream=(r>218)&(g>205)&(b>145)&(r-g<30)
    valid=np.array(mask.filter(ImageFilter.MaxFilter(13)))==0
    centers=[]
    for y in range(h):
        xs=np.where(cream[y]&valid[y])[0]
        centers.append((xs[0]+xs[-1])/2 if len(xs)>30 else 140)
    # Infer the belly axis from intact rows; the hand must not move the axis.
    maskrows=np.where(np.array(mask).max(axis=1)>0)[0]
    lo,hi=int(maskrows.min()),int(maskrows.max())
    c0=np.median(centers[max(0,lo-15):lo-5]); c1=np.median(centers[hi+5:hi+15])
    axis=np.interp(np.arange(h),[lo,hi],[c0,c1])
    donor=sample(rgb,2*axis[:,None]-xx,yy)
    if frame_index in [6,7]:
        donor=sample(rgb,xx,yy-65)
    # Feather only the local repair boundary. The same frame supplies texture.
    blend=np.array(mask.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.GaussianBlur(1.3)),dtype=float)/255
    result=rgb*(1-blend[:,:,None])+donor*blend[:,:,None]
    # The rendered hand stays inside the original silhouette. Preserve the
    # existing dark flipper/outline and exterior instead of reflecting them.
    protected=((r<180)&(np.abs(r-g)<35)&(np.abs(g-b)<40))|((r>180)&(b>170)&(g<110))
    result[protected]=rgb[protected]
    return result,blend


def matte(rgb):
    # Magenta extraction. Recover edge RGB from neighboring interior pixels.
    r,g,b=(rgb[:,:,k] for k in range(3))
    bg=(r>180)&(b>170)&(g<110)
    a=np.where(bg,0.,255.)
    edge=Image.fromarray((~bg*255).astype('uint8')).filter(ImageFilter.MinFilter(3))
    interior=np.array(edge)>0
    contaminated=(~bg)&((r-g>75)&(b-g>55))
    repaired=rgb.copy()
    for dy,dx in [(0,-1),(0,1),(-1,0),(1,0),(-2,0),(2,0),(0,-2),(0,2)]:
        donor=np.roll(rgb,(dy,dx),(0,1)); good=np.roll(interior,(dy,dx),(0,1))&contaminated
        repaired[good]=donor[good]; contaminated[good]=False
    rgba=np.concatenate([repaired,a[:,:,None]],axis=2).clip(0,255).astype('uint8')
    rgba[bg]=0
    return Image.fromarray(rgba)


def main():
    OUT.mkdir(exist_ok=True)
    (OUT/'frames').mkdir(exist_ok=True)
    sheet=np.array(Image.open(SOURCE).convert('RGB'),dtype=float)
    # Preserve a single generated hand: no mirroring, redraw, rotation or warp.
    first=sheet[:512,:256]
    handmask=mask_hand(first,BOXES[0])
    handrgba=np.concatenate([first,np.array(handmask)[:,:,None]],axis=2).astype('uint8')
    hand=Image.fromarray(handrgba).crop(handmask.getbbox())
    hand.save(OUT/'fixed-hand.png')
    frames=[]; bare=[]; metrics=[]
    board=Image.new('RGB',(6*288,2*406),'#dae4e3')
    bareboard=board.copy()
    for i,box in enumerate(BOXES):
        row,col=divmod(i,6); xoff=col*256; yoff=row*512
        rgb=sheet[yoff:yoff+512,xoff:xoff+256].copy()
        localbox=(box[0]-xoff,box[1]-yoff,box[2]-xoff,box[3]-yoff)
        mask=mask_hand(rgb,localbox)
        clean,repair=remove_hand(rgb,mask,i)
        cleanim=matte(clean)
        # Fixed row registration, one shared scale: preserve the pose motion.
        yshift=-100 if row==0 else -38
        base=Image.new('RGBA',(288,380)); base.alpha_composite(cleanim,(16,yshift))
        bare.append(base)
        # The body center follows the original drawing, while the wrist stays
        # on screen-right for the complete clockwise circle (screen Y down).
        cx=[140,139,135,137,134,132,135,134,133,133,130,132][i]+16
        cy=232
        theta=-math.pi/2+2*math.pi*i/12
        hx=cx+8+19*math.cos(theta); hy=cy+23*math.sin(theta)
        arr=np.array(base,dtype=float); yy,xx=np.mgrid[:380,:288]
        # Local nap compression follows the fingertips, with a soft trailing
        # recovery. Sample existing fur; don't paint rings or radial marks.
        contactx=hx-17; contacty=hy+5
        fall=np.exp(-((xx-contactx)/22)**2-((yy-contacty)/17)**2)
        dx=2.8*math.cos(theta+math.pi/2)*fall
        dy=(2.5+1.1*math.sin(theta))*fall
        warped=sample(arr,xx-dx,yy-dy)
        shade=0.085*np.exp(-((xx-(contactx-3))/17)**2-((yy-(contacty-2))/12)**2)
        recovery=0.024*np.exp(-((xx-(contactx-9))/23)**2-((yy-(contacty-12))/18)**2)
        warped[:,:,:3]=warped[:,:,:3]*(1-shade[:,:,None])+255*recovery[:,:,None]
        result=Image.fromarray(np.clip(warped,0,255).astype('uint8'))
        px=round(hx-hand.width/2); py=round(hy-hand.height/2)
        result.alpha_composite(hand,(px,py))
        pixels=np.array(result)
        flood=Image.fromarray(np.where(pixels[:,:,3]>0,255,0).astype('uint8')).copy()
        ImageDraw.floodfill(flood,(0,0),128)
        holes=np.array(flood)==0
        if 0<int(holes.sum())<=4:
            for y,x in zip(*np.where(holes)):
                neighbors=pixels[max(0,y-1):y+2,max(0,x-1):x+2]
                opaque=neighbors[neighbors[:,:,3]>0]
                pixels[y,x,:3]=np.median(opaque[:,:3],axis=0); pixels[y,x,3]=255
            result=Image.fromarray(pixels)
        result.save(OUT/'frames'/f'frame_{i+1:02d}.png')
        frames.append(result)
        for target,im in [(board,result),(bareboard,base)]:
            target.paste(im,(col*288,row*406+24),im)
            ImageDraw.Draw(target).text((col*288+12,row*406+6),f'{i+1:02d}',fill='#304040')
        metrics.append({'frame':i+1,'handCenter':[round(hx,2),round(hy,2)],'clockwisePhaseDegrees':i*30,
                        'handPlacement':[px,py],'handMirrored':False,'handRotation':0,
                        'repairedPixels':int((repair>.05).sum()),'bounds':result.getbbox()})
    board.save(OUT/'contact-sheet.png'); bareboard.save(OUT/'body-repair-contact-sheet.png')
    previews=[]
    for im in frames:
        bg=Image.new('RGB',im.size,'#dae4e3'); bg.paste(im,(0,0),im); previews.append(bg)
    previews[0].save(OUT/'belly-clockwise-preview.gif',save_all=True,append_images=previews[1:],duration=140,loop=0,disposal=2)
    (OUT/'qa.json').write_text(json.dumps({'status':'candidate_pending_visual_review','runtimeModified':False,
       'source':str(SOURCE),'sourceSHA256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
       'frames':metrics,'method':'same-frame texture repair; single fixed generated hand; clockwise translation; local fur deformation'},indent=2),encoding='utf-8')
    html='''<!doctype html><meta charset="utf-8"><title>肚子顺时针抚摸 · 合成候选</title>
<style>body{margin:0;background:#edf1ef;color:#263d39;font:16px system-ui;display:grid;place-items:center;min-height:100vh}main{text-align:center;max-width:720px;padding:24px}img{display:block;margin:auto;width:288px;height:380px;background:#dae4e3;border-radius:20px}button,select{font:inherit;padding:8px 16px;margin:12px 6px;border:1px solid #c2ceca;border-radius:8px;background:white}input{width:280px}p{line-height:1.7}.note{font-size:14px;color:#62716b}</style>
<main><h2>肚子顺时针抚摸 · 合成候选</h2><img id="pet" src="frames/frame_01.png">
<button id="toggle">暂停</button><select id="speed"><option value="140">正常速度</option><option value="280">半速检查</option></select><br>
<input id="slider" type="range" min="0" max="11" value="0"><span id="count">1 / 12</span>
<p>同一只手固定朝向，沿顺时针轨迹移动。<br>保留享受表情、翅膀和脚部动作，加入局部绒毛压感。</p>
<p class="note">候选预览，尚未替换正式素材。拖动进度条可逐帧检查。</p></main>
<script>const frames=Array.from({length:12},(_,i)=>{const im=new Image;im.src=`frames/frame_${String(i+1).padStart(2,'0')}.png`;return im});let n=0,playing=true,last=0;const pet=document.querySelector('#pet'),slider=document.querySelector('#slider'),count=document.querySelector('#count'),toggle=document.querySelector('#toggle'),speed=document.querySelector('#speed');function show(){pet.src=frames[n].src;slider.value=n;count.textContent=`${n+1} / 12`}toggle.onclick=()=>{playing=!playing;toggle.textContent=playing?'暂停':'播放';last=0};slider.oninput=()=>{playing=false;toggle.textContent='播放';n=+slider.value;show()};function tick(t){if(playing&&t-last>=+speed.value){n=(n+1)%12;show();last=t}requestAnimationFrame(tick)}requestAnimationFrame(tick)</script>'''
    (OUT/'preview.html').write_text(html,encoding='utf-8')
    print(OUT)


if __name__=='__main__': main()
