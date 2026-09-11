// Browser runtime verification: real controller, pointer input, asset loader and Pixi renderer.
const { chromium }=require(process.argv[2]);
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
const out=path.resolve(__dirname,'../docs/flipper-hold-integration-2026-09-11');
(async()=>{
  const browser=await chromium.launch({headless:true});const reports={};
  for(const side of ['left','right']){
    const context=await browser.newContext({viewport:{width:480,height:360},deviceScaleFactor:2,recordVideo:{dir:path.join(out,'video'),size:{width:480,height:360}}});
    const page=await context.newPage();const errors=[],failed=[],events=[];let start=0;
    page.on('pageerror',e=>errors.push(String(e)));page.on('response',r=>{if(r.status()>=400)failed.push(r.url());});
    page.on('console',m=>{if(m.text().includes('[interaction]'))events.push({ms:start?Date.now()-start:null,message:m.text()});});
    await page.addInitScript(()=>{Math.random=()=>.7;localStorage.setItem('desktop-pet.size-percent','100');});
    await page.goto('http://127.0.0.1:1431');await page.locator('canvas').waitFor();
    await page.addStyleTag({content:'#root{position:absolute;left:56px;top:75px;width:368px;height:228px}body:before{content:"";position:fixed;inset:0;background:#dae4e3}#demo-label{position:fixed;top:20px;left:0;width:480px;text-align:center;color:#29433d;font:20px "Microsoft YaHei",sans-serif}#demo-clock{position:fixed;bottom:18px;width:480px;left:0;text-align:center;color:#5c726a;font:14px "Microsoft YaHei",sans-serif}'});
    await page.evaluate(side=>{for(const [id,text] of [['demo-label',(side==='left'?'左':'右')+'侧翅膀 · 放慢后的正式动作'],['demo-clock','程序前端实际运行 · 本次长按 8.5 秒触发']]){const el=document.createElement('div');el.id=id;el.textContent=text;document.body.append(el);}},side);
    const x=side==='left'?150:330;await page.mouse.move(x,195);await page.keyboard.press('Escape');await page.waitForTimeout(400);
    const hold=page.waitForEvent('console',{predicate:m=>m.text().includes(`accepted touch_flipper_hold_screen_${side}`),timeout:5000});
    const reaction=page.waitForEvent('console',{predicate:m=>m.text().includes(`accepted touch_flipper_react_screen_${side}`),timeout:15000});
    start=Date.now();await page.mouse.down();await hold;await page.waitForTimeout(1000);
    await page.screenshot({path:path.join(out,`${side}-runtime-hold.png`)});
    await reaction;const reactionMs=Date.now()-start;
    await page.evaluate(()=>document.querySelector('#demo-label').textContent='持续触摸 · 开始不耐烦');
    await page.waitForTimeout(450);await page.screenshot({path:path.join(out,`${side}-runtime-reaction.png`)});
    // Release during the one-shot: it must finish rather than restart the hold.
    await page.mouse.up();await page.waitForTimeout(1900);
    await page.evaluate(()=>document.querySelector('#demo-label').textContent='动作播放完成 · 回到待机');
    await page.screenshot({path:path.join(out,`${side}-runtime-idle.png`)});await page.waitForTimeout(600);
    assert.ok(reactionMs>=8400&&reactionMs<9500,`reaction at ${reactionMs}`);
    assert.equal(events.filter(e=>e.message.includes(`accepted touch_flipper_react_screen_${side}`)).length,1);
    assert.equal(events.filter(e=>e.message.includes(`accepted touch_flipper_hold_screen_${side}`)).length,1);
    assert.deepEqual(errors,[]);assert.deepEqual(failed,[]);
    const video=page.video();await context.close();await video.saveAs(path.join(out,`${side}-flipper-runtime.webm`));
    reports[side]={reactionMs,errors,failedRequests:failed,events};
  }
  fs.writeFileSync(path.join(out,'browser-check.json'),JSON.stringify(reports,null,2));await browser.close();
  console.log(JSON.stringify(reports));
})().catch(e=>{console.error(e);process.exit(1)});
