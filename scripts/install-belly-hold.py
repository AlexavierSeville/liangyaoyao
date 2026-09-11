"""Install approved belly hold and body correction, retaining original backups."""
from pathlib import Path
import json
import shutil
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'output/touch-hold-draft-2026-09-09'
QA=ROOT/'docs/belly-hold-integration-2026-09-09'
ASSETS=ROOT/'public/assets/animations/hd'
QA.mkdir(exist_ok=True)
backup=QA/'backup'; backup.mkdir(exist_ok=True)
for name in ['animations.json','animation-registry.json']:
    if not (backup/name).exists(): shutil.copy2(ROOT/'src/config'/name,backup/name)
if not (backup/'touch_belly_dislike').exists():
    shutil.copytree(ASSETS/'touch_belly_dislike',backup/'touch_belly_dislike')

frames=[Image.open(p).convert('RGBA') for p in sorted((RUN/'candidate-v6-composite/frames').glob('*.png'))]
assert len(frames)==12
bounds=frames[0].getbbox(); scale=396/(bounds[3]-bounds[1])
head=frames[0].crop((0,bounds[1],288,bounds[1]+100)).getbbox()
head_center=(head[0]+head[2])/2
result=[]; stats=[]
target=ASSETS/'touch_belly_rub_loop'; target.mkdir(exist_ok=True)
for i,frame in enumerate(frames,1):
    b=frame.getbbox(); crop=frame.crop(b)
    size=(round(crop.width*scale),round(crop.height*scale))
    x=round(318+(b[0]-head_center)*scale); y=round(430+(b[1]-bounds[3])*scale)
    out=Image.new('RGBA',(640,456))
    out.alpha_composite(crop.resize(size,Image.Resampling.LANCZOS),(x,y))
    out.save(target/f'frame_{i:02d}@2x.webp',lossless=True,exact=True)
    result.append(out); stats.append({'frame':i,'bounds2x':out.getbbox()})
# The user approved this corrected body before the hold artwork was made.
for p in sorted((ROOT/'docs/body-proportion-review-2026-09-09/candidate-v1/touch_belly_dislike').glob('*.png')):
    Image.open(p).save(ASSETS/'touch_belly_dislike'/(p.stem+'.webp'),lossless=True,exact=True)

catalog_path=ROOT/'src/config/animations.json'; catalog=json.loads(catalog_path.read_text())
clip=dict(catalog['animations']['touch_belly_dislike'])
clip.update(id='touch_belly_rub_loop',files=[f'/assets/animations/hd/touch_belly_rub_loop/frame_{i:02d}@2x.webp' for i in range(1,13)],fps=1000/140,loop=True,transitionMs=160)
catalog['animations']['touch_belly_rub_loop']=clip
catalog['animations']['touch_belly_dislike']['transitionMs']=160
catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
registry_path=ROOT/'src/config/animation-registry.json'; registry=json.loads(registry_path.read_text())
registry['animations']=[d for d in registry['animations'] if d['id']!='touch_belly_rub_loop']
registry['animations'].append(dict(id='touch_belly_rub_loop',action='BellyRub',category='Touch',frameCount=12,loop=True,defaultFps=1000/140,trigger='user_click',onComplete='stay',status='active',interruptPriority=50,direction='None',runtimeClipId='touch_belly_rub_loop',interactionGroup='belly_hold',phase='loop'))
registry_path.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
board=Image.new('RGB',(960,260),'#dae4e3'); draw=ImageDraw.Draw(board)
master=Image.new('RGBA',(640,456))
master.alpha_composite(Image.open(ROOT/'docs/body-proportion-review-2026-09-09/master-front.png').convert('RGBA').resize((384,416)),(128,24))
dislike=Image.open(ASSETS/'touch_belly_dislike/frame_01@2x.webp')
for i,(label,im) in enumerate([('MASTER',master),('ENJOY BELLY RUB',result[0]),('EXISTING IMPATIENCE',dislike)]):
    im=im.resize((320,228),Image.Resampling.LANCZOS);board.paste(im,(i*320,25),im);draw.text((i*320+10,7),label,fill='#304040')
board.save(QA/'alignment.png')
(QA/'asset-report.json').write_text(json.dumps({'source':'approved candidate-v6-composite','sharedScale':scale,'neutralHeightLogical':198,'baselineLogical':215,'headCenterLogical':159,'frames':stats,'dislikeSource':'approved body-proportion candidate-v1'},indent=2),encoding='utf-8')
print(QA)
