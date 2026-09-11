"""Audit review assets and preserve their provenance without runtime changes."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageSequence,ImageDraw
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'output/flipper-identity-unification-2026-09-11';OLD=ROOT/'output/flipper-hold-draft-2026-09-10';OUT=RUN/'preview-v2'
baseline=json.loads((OLD/'imagegen-jobs-v5.json').read_text(encoding='utf-8'))['runtimeBaseline']
integrity={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in baseline.items()};assert all(integrity.values())
reports={};jobs=[]
for side in ['left','right']:
    source=RUN/'decoded'/f'unified-reaction-{side}-v1.png'
    refs=[RUN/'references'/f'old-reaction-{side}.png',OLD/('preview-left-v1' if side=='left' else 'final-right-flipper')/'frames/frame_01.png',OLD/('decoded/flipper-left-final-part-a.png' if side=='left' else 'references/final-right-part-a.png'),OLD/'references/canonical-front-enlarged.png']
    jobs.append({'side':side,'method':'built-in imagegen','source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'prompt':'prompts/unified-impatience.md','sideSpecification':f'hand enters screen {side}; initially faces {side}; turns away toward the opposite side in frames 11-12','references':[{'path':str(r),'sha256':hashlib.sha256(r.read_bytes()).hexdigest()} for r in refs]})
    files=sorted((OUT/side/'frames').glob('*.png'));assert len(files)==12
    checks=[]
    for p in files:
        im=Image.open(p).convert('RGBA');a=np.array(im);bb=im.getbbox();assert im.size==(520,360)
        assert 0<bb[0]<bb[2]<520 and 0<bb[1]<bb[3]<360
        assert np.all(a[a[:,:,3]==0,:3]==0)
        mask=Image.fromarray(np.where(a[:,:,3]>0,255,0).astype('uint8')).copy();ImageDraw.floodfill(mask,(0,0),128)
        coords=np.argwhere(np.array(mask)==0);checks.append({'frame':p.name,'bounds':bb,'enclosedTransparentPixelCount':len(coords),'enclosedTransparentPositionsYX':coords.tolist() if len(coords)<100 else 'inspect','sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    g=Image.open(OUT/side/'continuity.gif');total=sum(f.info['duration'] for f in ImageSequence.Iterator(g));assert g.n_frames==(43 if side=='left' else 44) and total==7880
    reports[side]={'reactionFrames':12,'continuityFrames':g.n_frames,'gifDurationMs':total,'designDurationMs':7940,'frames':checks}
(RUN/'imagegen-jobs.json').write_text(json.dumps({'stage':'unified_reaction_candidate_pending_user_review','jobs':jobs,'runtimeUnchanged':integrity,'delivered':'preview-v2/index.html'},ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'verification.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'runtimeUnchanged':all(integrity.values()),'sides':{s:{'frames':r['reactionFrames'],'gifMs':r['gifDurationMs'],'holes':[f['enclosedTransparentPixelCount'] for f in r['frames']]} for s,r in reports.items()}}))
