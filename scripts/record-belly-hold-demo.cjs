// Real app, real pointer gesture and renderer. Random is fixed only in QA.
const { chromium } = require(process.argv[2]);
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const out = path.resolve(__dirname, '../docs/belly-hold-integration-2026-09-09');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 480, height: 360 }, deviceScaleFactor: 2,
    recordVideo: { dir: path.join(out, 'video'), size: {width: 480, height: 360} } });
  const page = await context.newPage();
  const events = [], errors = [], failed = []; let started = 0;
  page.on('pageerror', e => errors.push(String(e)));
  page.on('response', r => { if (r.status() >= 400) failed.push(r.url()); });
  page.on('console', m => {
    if (m.text().includes('[interaction]')) events.push({ms: started ? Date.now()-started : null, message:m.text()});
  });
  await page.addInitScript(() => { Math.random = () => 0.32; localStorage.setItem('desktop-pet.size-percent','100'); });
  await page.goto('http://127.0.0.1:1421');
  await page.locator('canvas').waitFor();
  // A presentation border surrounds the unchanged 320x228 runtime surface.
  await page.addStyleTag({content: '#root{position:absolute;left:80px;top:75px;width:320px;height:228px}body:before{content:"";position:fixed;inset:0;background:#dae4e3}#demo-label{position:fixed;top:20px;left:0;width:480px;text-align:center;color:#29433d;font:20px "Microsoft YaHei",sans-serif}#demo-clock{position:fixed;bottom:18px;width:480px;left:0;text-align:center;color:#5c726a;font:14px "Microsoft YaHei",sans-serif}'});
  await page.evaluate(() => {
    for (const [id,text] of [['demo-label','长按肚子 · 享受抚摸 → 不耐烦'],['demo-clock','实际运行演示 · 本次在 6.6 秒触发']]) {
      const el=document.createElement('div');el.id=id;el.textContent=text;document.body.append(el);
    }
  });
  await page.mouse.move(240,195); await page.keyboard.press('Escape'); await page.waitForTimeout(300);
  const setLabel = (text) => page.evaluate(t => document.querySelector('#demo-label').textContent=t,text);
  const rub = page.waitForEvent('console',{predicate:m=>m.text().includes('accepted touch_belly_rub_loop')});
  const reaction = page.waitForEvent('console',{predicate:m=>m.text().includes('accepted touch_belly_dislike'),timeout:12000});
  started=Date.now(); await page.mouse.down(); await rub; await setLabel('按住肚子 · 享受顺时针抚摸');
  await page.waitForTimeout(250);
  await page.screenshot({path:path.join(out,'runtime-enjoying.png')});
  await reaction; const reactionMs=Date.now()-started;
  await setLabel('已经摸了 6.6 秒 · 开始不耐烦');
  await page.waitForTimeout(450); await page.screenshot({path:path.join(out,'runtime-impatient.png')});
  await page.waitForTimeout(1400); await page.mouse.up(); await setLabel('不耐烦动作结束 · 回到待机');
  await page.waitForTimeout(650);
  assert.ok(reactionMs>=6500 && reactionMs<7300,`reaction time ${reactionMs}`);
  assert.equal(events.filter(e=>e.message.includes('accepted touch_belly_dislike')).length,1);
  const video=page.video(); await context.close(); await video.saveAs(path.join(out,'belly-hold-runtime.webm'));
  fs.writeFileSync(path.join(out,'browser-check.json'),JSON.stringify({reactionMs,randomSample:0.32,events,errors,failedRequests:failed},null,2));
  console.log(JSON.stringify({reactionMs,errors,failedRequests:failed,video:path.join(out,'belly-hold-runtime.webm')}));
  await browser.close(); if(errors.length||failed.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exit(1)});
