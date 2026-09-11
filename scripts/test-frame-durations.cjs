// Test actual player timing with lightweight graphics objects, no GPU required.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
class Container { addChild() {} }
class Sprite { anchor = { set() {}, copyFrom() {} }; }
const moduleObject = { exports: {} };
const source = fs.readFileSync(path.join(__dirname, '../src/animation/SpriteSheetAnimationPlayer.ts'), 'utf8');
vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText, {
  module: moduleObject, exports: moduleObject.exports,
  require: () => ({ Container, Sprite, Assets: { load: async file => ({ file }) } }),
});
const Player = moduleObject.exports.SpriteSheetAnimationPlayer;
function clip(id, durations, loop = true) {
  return { id, sourceType: 'sprite', files: durations.map((_, i) => `${id}-${i}`), frames: durations.length,
    frameWidth: 1, frameHeight: 1, fps: 10, frameDurationsMs: durations, loop, sheetRow: 0 };
}
(async () => {
  const p = new Player(false);
  const durations = [220,180,160,260,180,220,180,200,180,180,220,180,180,220,200,260];
  await p.load(clip('handshake', durations));
  let loops = 0; p.onComplete(() => loops++); p.play('handshake');
  for (let i = 0; i < durations.length; i++) {
    p.update(durations[i] - 1); assert.equal(p.sprite.texture.file, `handshake-${i}`);
    p.update(1); assert.equal(p.sprite.texture.file, `handshake-${(i + 1) % durations.length}`);
  }
  assert.equal(loops, 1);
  p.update(3220 * 2 + 400); assert.equal(loops, 3); assert.equal(p.sprite.texture.file, 'handshake-2');
  console.log('PASS per-frame durations, exact boundaries, full loops and catch-up');
  const legacy = clip('legacy', [100,100], false); delete legacy.frameDurationsMs;
  await p.load(legacy); p.play('legacy'); p.update(199); assert.equal(p.isPlaying, true);
  p.update(1); assert.equal(p.isPlaying, false); assert.equal(p.sprite.texture.file, 'legacy-1');
  console.log('PASS legacy FPS fallback and one-shot completion');
  for (const values of [[0],[-1],[NaN],[Infinity],[10,20]]) {
    const bad = clip('bad', [100]); bad.frameDurationsMs = values;
    await assert.rejects(p.load(bad), /Invalid frame durations/);
  }
  console.log('PASS invalid durations rejected before loading');
  const switching = new Player(false);
  await switching.load(clip('a', [50], false)); await switching.load(clip('b', [30,70]));
  switching.onComplete(id => { if (id === 'a') switching.play('b'); });
  switching.play('a'); switching.update(50); assert.equal(switching.currentAnimationId, 'b');
  switching.update(29); assert.equal(switching.sprite.texture.file, 'b-0');
  switching.update(1); assert.equal(switching.sprite.texture.file, 'b-1');
  console.log('PASS completion callback switches timing to the new clip');
  const catalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../src/config/animations.json'),'utf8')).animations;
  for (const side of ['left','right']) {
    const player=new Player(false);
    for (const action of ['hold','react']) {
      const config=catalog[`touch_flipper_${action}_screen_${side}`];
      await player.load(config);player.play(config.id);
      for (let i=0;i<config.frames;i++) {
        player.update(config.frameDurationsMs[i]-1);
        assert.equal(player.sprite.texture.file,config.files[i]);
        assert.equal(player.isPlaying,true);player.update(1);
      }
      assert.equal(player.isPlaying,action==='hold');
      assert.equal(player.sprite.texture.file,config.files[action==='hold'?0:config.frames-1]);
    }
  }
  console.log('PASS formal left/right hold and reaction clips render every slower frame for its full duration');
})().catch(error => { console.error(error); process.exitCode = 1; });
