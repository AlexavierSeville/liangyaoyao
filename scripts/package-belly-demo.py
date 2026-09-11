"""Package the captured runtime footage for review, without changing timing."""
from pathlib import Path
import json
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/belly-hold-integration-2026-09-09'
paths=sorted((OUT/'video-frames').glob('*.png'))
images=[Image.open(p).convert('RGB') for p in paths]
# Remove only the blank browser startup, keeping all motion and transitions.
first=next(i for i,im in enumerate(images) if np.array(im)[5,5,1]<245)
images=images[first:]
palette=images[len(images)//2].quantize(colors=240)
frames=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in images]
frames[0].save(OUT/'belly-hold-continuous-demo.gif',save_all=True,append_images=frames[1:],duration=100,loop=0,disposal=2)
(OUT/'demo-trim.json').write_text(json.dumps({'startupTrimSeconds':first/10,'durationSeconds':len(images)/10,'source':'belly-hold-runtime.webm','frameRate':10},indent=2),encoding='utf-8')
(OUT/'demo.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>肚子长按 · 连贯演示</title>
<style>body{margin:0;background:#eef2ef;color:#29433d;font:16px "Microsoft YaHei",sans-serif;display:grid;place-items:center;min-height:100vh}main{width:min(94vw,800px);text-align:center;padding:24px}video{width:min(100%,640px);border-radius:18px;background:#dae4e3}p{line-height:1.8}a{color:#326657}</style><main>
<h2>长按肚子：享受抚摸 → 不耐烦 → 待机</h2><video src="belly-hold-continuous-demo.webm" controls autoplay loop muted playsinline></video>
<p>实际应用录屏。本次在按住约 6.6 秒后触发不耐烦；正常使用时随机在 5–10 秒触发。<br>提前松手会停止抚摸并回到待机；不耐烦每次长按只触发一次。</p>
<p><a href="belly-hold-continuous-demo.gif">查看 GIF</a> · <a href="alignment.png">母版尺寸对比</a></p></main></html>''',encoding='utf-8')
print(json.dumps({'trimSeconds':first/10,'frames':len(images),'gif':str(OUT/'belly-hold-continuous-demo.gif')}))
