"""Record candidate provenance and verify the installed runtime stayed intact."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'output/flipper-hold-draft-2026-09-10'
base=json.loads((RUN/'imagegen-jobs-v5.json').read_text())
checks=[]
for name,expected in base['runtimeBaseline'].items():
    actual=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    checks.append({'path':name,'sha256':actual,'unchanged':actual==expected})
assert all(c['unchanged'] for c in checks)
jobs=[]
for name,prompt,refs in [
 ('flipper-right-v6-part-b-local-fixes.png','flipper-v6-part-b-local-fixes.md',['decoded/flipper-right-v5-part-b.png','references/canonical-front-enlarged.png','references/flipper-v5-part-a-last.png']),
 ('flipper-right-v6-part-b-open-fingertips.png','flipper-v6-b-open-fingertips.md',['decoded/flipper-right-v6-part-b-local-fixes.png','preview-v6-before-proportions/frames/frame_13.png','references/canonical-front-enlarged.png'])]:
    p=RUN/'decoded'/name
    jobs.append({'selectedSource':str(p.relative_to(RUN)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'prompt':'prompts/'+prompt,'references':refs,'imageSize':Image.open(p).size,'status':'generated_and_reviewed'})
holes=[]
for f in sorted((RUN/'preview-v6/frames').glob('*.png')):
    im=Image.open(f);a=np.array(im)[:,:,3]
    mask=Image.fromarray(np.where(a>0,255,0).astype('uint8')).copy()
    ImageDraw.floodfill(mask,(0,0),128)
    coords=np.argwhere(np.array(mask)==0).tolist()
    assert len(coords)<100
    holes.append({'frame':f.name,'enclosedZeroAlphaPixelsYX':coords})
gif=Image.open(RUN/'preview-v6/playful-handshake-refined.gif');total=0
for i in range(gif.n_frames):
    gif.seek(i);total+=gif.info['duration']
assert gif.n_frames==16 and total==3220
manifest={'stage':'v6_candidate_pending_user_approval','previousVersion':'v5 motion direction and timing approved by user','runtimeModified':False,'runtimeIntegrity':checks,'framesTotal':16,'side':'screen_right','jobs':jobs,'assembly':{'partA':'decoded/flipper-right-v5-part-a.png','partB':'decoded/flipper-right-v6-part-b-open-fingertips.png','scripts':['scripts/preview-flipper-v5.py','scripts/refine-flipper-proportions-v6.py'],'method':'actual gutter extraction; shared row registration; smooth proportion inverse warp; frame 11 original complete silhouette translated upward 3px to ground baseline; no transplanted feet','preview':'preview-v6/index.html','loopDurationMs':total},'limits':['Candidate only; production alpha/chroma cleanup and runtime integration follow approval.','Frontal master compared with three-quarter animation; proportions are visual approximation.']}
(RUN/'imagegen-jobs-v6.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(RUN/'preview-v6/alpha-audit.json').write_text(json.dumps(holes,indent=2),encoding='utf-8')
print(json.dumps({'runtimeUnchanged':True,'gifFrames':gif.n_frames,'durationMs':total,'alphaHoles':holes}))
