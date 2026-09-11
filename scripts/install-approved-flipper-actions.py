"""Install the user-approved color/proportion frames with slower timing."""
from pathlib import Path
import importlib.util, json, hashlib, shutil, zipfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'output/flipper-identity-unification-2026-09-11/preview-v4-color'
OUT=ROOT/'output/flipper-identity-unification-2026-09-11/final-approved'
QA=ROOT/'docs/flipper-hold-integration-2026-09-11'
SKILL=Path.home()/'.codex/skills/hatch-pet/scripts/despill_chroma_edges.py'
spec=importlib.util.spec_from_file_location('cleanup',SKILL);cleanup=importlib.util.module_from_spec(spec);spec.loader.exec_module(cleanup)
HOLD=[290,240,210,340,240,290,240,260,240,240,290,240,240,290,260,340]
REACT=[170]*12
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
catalog_path=ROOT/'src/config/animations.json';catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
registry_path=ROOT/'src/config/animation-registry.json';registry=json.loads(registry_path.read_text(encoding='utf-8'))
reports={};allframes={}
for side in ['left','right']:
    allframes[side]={}
    for action,folder,durations in [('hold','hold-frames',HOLD),('react','frames',REACT)]:
        clip_id=f'touch_flipper_{action}_screen_{side}';dest=ROOT/'public/assets/animations/hd'/clip_id
        dest.mkdir(parents=True,exist_ok=True);source=sorted((SRC/side/folder).glob('*.png'));assert len(source)==len(durations)
        frames=[];metrics=[];final=OUT/side/action;final.mkdir(parents=True,exist_ok=True)
        for i,p in enumerate(source,1):
            im=Image.open(p).convert('RGBA')
            # Left hold has not yet had its final deterministic edge cleanup.
            edge={}
            if side=='left' and action=='hold':
                clean,edge=cleanup.decontaminate_image(im,chroma_key=(255,0,255),edge_radius=5)
                assert np.array_equal(np.array(im)[:,:,3],np.array(clean)[:,:,3]);im=clean
            im.save(final/f'frame_{i:02d}.png')
            b=im.getbbox();scale=396/280;crop=im.crop(b);size=(round(crop.width*scale),round(crop.height*scale))
            x=round(366+(b[0]-260)*scale);y=round(430+(b[1]-330)*scale)
            assert x>0 and y>0 and x+size[0]<736 and y+size[1]<456,(clip_id,i,x,y,size)
            hd=Image.new('RGBA',(736,456));hd.alpha_composite(crop.resize(size,Image.Resampling.LANCZOS),(x,y))
            hd.save(dest/f'frame_{i:02d}@2x.webp',lossless=True,exact=True);frames.append(hd)
            metrics.append({'frame':i,'sourceSHA256':hashlib.sha256(p.read_bytes()).hexdigest(),'runtimeSHA256':hashlib.sha256((dest/f'frame_{i:02d}@2x.webp').read_bytes()).hexdigest(),'bounds2x':hd.getbbox(),'durationMs':durations[i-1],'edgeCleanup':edge})
        allframes[side][action]=frames;reports[clip_id]=metrics
        clip={'id':clip_id,'sourceType':'sprite','files':[f'/assets/animations/hd/{clip_id}/frame_{i:02d}@2x.webp' for i in range(1,len(frames)+1)],'frames':len(frames),'frameWidth':368,'frameHeight':228,'fps':len(frames)*1000/sum(durations),'frameDurationsMs':durations,'loop':action=='hold','sheetRow':0,'anchor':{'x':.5,'y':220/228},'transitionMs':160}
        catalog['animations'][clip_id]=clip
        registry['animations']=[d for d in registry['animations'] if d['id']!=clip_id]
        registry['animations'].append({'id':clip_id,'action':'FlipperHold' if action=='hold' else 'FlipperReact','category':'Touch','frameCount':len(frames),'loop':action=='hold','defaultFps':clip['fps'],'trigger':'user_click','onComplete':'stay' if action=='hold' else 'return_idle','status':'active','interruptPriority':50 if action=='hold' else 60,'direction':'None','runtimeClipId':clip_id,'interactionGroup':'flipper_hold','phase':'loop' if action=='hold' else 'reaction'})
        board=Image.new('RGB',(1472,260*((len(frames)+3)//4)),'#dae4e3');d=ImageDraw.Draw(board)
        for i,im in enumerate(frames):
            small=im.resize((368,228),Image.Resampling.LANCZOS);x=i%4*368;y=i//4*260;board.paste(small,(x,y+25),small);d.text((x+10,y+3),f'{i+1:02d} · {durations[i]} ms',font=font,fill='#29443e')
        board.save(OUT/f'{clip_id}-contact-sheet.png')
alias=dict(catalog['animations']['touch_flipper_react_screen_right']);alias['id']='touch_flipper_react';catalog['animations']['touch_flipper_react']=alias
for d in registry['animations']:
    if d['id']=='touch_flipper_react':d['defaultFps']=alias['fps']
catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
registry_path.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
OUT.mkdir(parents=True,exist_ok=True)
manifest={'status':'user_approved_formal_assets','source':str(SRC),'frameCount':56,'holdDurationsMs':HOLD,'holdCycleMs':sum(HOLD),'reactionDurationsMs':REACT,'reactionDurationMs':sum(REACT),'bodyLongHoldTriggerMs':[5000,10000],'canvas2x':[736,456],'logicalBodyHeight':198,'logicalBaseline':215,'transparentGutterNote':'368px canvas preserves the 220px body hit area and fits the full extended left hand','runtimeIntegrated':True,'frames':reports}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
with zipfile.ZipFile(OUT.parent/'flipper-actions-final.zip','w',zipfile.ZIP_DEFLATED) as z:
    z.write(OUT/'manifest.json','manifest.json')
    for clip_id in reports:
        for p in sorted((ROOT/'public/assets/animations/hd'/clip_id).glob('*.webp')):z.write(p,f'hd/{clip_id}/{p.name}')
print(json.dumps({'frames':56,'holdCycleMs':sum(HOLD),'reactionDurationMs':sum(REACT),'out':str(OUT)}))
