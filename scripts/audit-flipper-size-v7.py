"""Check the edited candidate without touching runtime assets."""
from pathlib import Path
import json,hashlib
from collections import deque
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'output/flipper-hold-draft-2026-09-10';OUT=RUN/'preview-v7'

def components(im):
    a=np.array(im)[:,:,3]
    mask=np.array(Image.fromarray(np.where(a>100,255,0).astype('uint8')).filter(ImageFilter.MaxFilter(3)))>0
    sizes=[]
    for yy,xx in np.argwhere(mask):
        if not mask[yy,xx]:continue
        todo=deque([(yy,xx)]);mask[yy,xx]=False;n=0
        while todo:
            y,x=todo.popleft();n+=1
            for y1,x1 in [(y-1,x),(y+1,x),(y,x-1),(y,x+1)]:
                if 0<=y1<mask.shape[0] and 0<=x1<mask.shape[1] and mask[y1,x1]:
                    mask[y1,x1]=False;todo.append((y1,x1))
        if n>40:sizes.append(n)
    return len(sizes)

checks=[]
for i in range(1,17):
    name=f'frame_{i:02d}.png';before=Image.open(RUN/'preview-v6/frames'/name);after=Image.open(OUT/'frames'/name)
    a=np.array(before);b=np.array(after);bbox=after.getbbox()
    cream=(a[:,:,0]>205)&(a[:,:,1]>195)&(a[:,:,2]>140)&(a[:,:,0].astype(int)-a[:,:,1]<55)&(a[:,:,3]==255)
    cream[:,260:]=False
    assert np.array_equal(a[cream],b[cream]),f'face/torso changed: {i}'
    assert np.array_equal(a[280:,:,:],b[280:,:,:]),f'feet changed: {i}'
    assert 0<bbox[0]<bbox[2]<420 and 0<bbox[1]<bbox[3]<360
    cb,ca=components(before),components(after)
    assert cb==ca,(i,cb,ca)
    mask=Image.fromarray(np.where(b[:,:,3]>0,255,0).astype('uint8')).copy();ImageDraw.floodfill(mask,(0,0),128)
    holes=np.argwhere(np.array(mask)==0)
    checks.append({'frame':i,'creamFaceTorsoUnchanged':True,'feetUnchanged':True,'componentCountBeforeAfter':[cb,ca],'bounds':bbox,'interiorZeroAlphaPixels':len(holes)})
gif=Image.open(OUT/'smaller-flippers.gif');total=0
for i in range(gif.n_frames):gif.seek(i);total+=gif.info['duration']
assert gif.n_frames==16 and total==3220
q=json.loads((OUT/'qa.json').read_text());q['verification']={'frameCount':gif.n_frames,'durationMs':total,'frames':checks}
q['sourceFramesSHA256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((RUN/'preview-v6/frames').glob('*.png'))}
(OUT/'qa.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':True,'frames':len(checks),'durationMs':total,'contactConnectivityUnchanged':True,'faceTorsoCreamAndFeetUnchanged':True}))
