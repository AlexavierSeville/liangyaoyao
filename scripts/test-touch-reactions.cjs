// Exercise real pointer gestures, timers, registry resolution and completion.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');
let time = 0;
let nextTimer = 1;
const timers = new Map();
class Element extends EventTarget {
  scale = 1;
  closest() { return null; }
  getBoundingClientRect() { return { left: 0, top: 0, width: 368 * this.scale, height: 228 * this.scale }; }
}
const modules = new Map();
function load(file) {
  if (file.endsWith('.json')) return JSON.parse(fs.readFileSync(file, 'utf8'));
  if (!path.extname(file)) file += '.ts';
  if (modules.has(file)) return modules.get(file).exports;
  const module = { exports: {} };
  modules.set(file, module);
  const source = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
  }).outputText;
  vm.runInNewContext(source, {
    module, exports: module.exports,
    require: name => load(path.resolve(path.dirname(file), name)),
    console: { debug() {}, warn() {} }, Element, HTMLElement: Element,
    setTimeout: (fn, delay) => { const id = nextTimer++; timers.set(id, { fn, at: time + delay }); return id; },
    clearTimeout: id => timers.delete(id),
  }, { filename: file });
  return module.exports;
}
const { PetInteractionController } = load(path.join(root, 'src/behavior/PetInteractionController.ts'));
const { PetStateMachine } = load(path.join(root, 'src/behavior/PetStateMachine.ts'));
const { AnimationRegistry } = load(path.join(root, 'src/animation/loadAnimationRegistry.ts'));
const definitions = load(path.join(root, 'src/config/animation-registry.json')).animations;
const catalog = load(path.join(root, 'src/config/animations.json')).animations;
const behavior = load(path.join(root, 'src/config/behavior.json'));
function advance(ms) {
  const end = time + ms;
  while (true) {
    const due = [...timers].filter(([, t]) => t.at <= end).sort((a, b) => a[1].at - b[1].at)[0];
    if (!due) break;
    time = due[1].at; timers.delete(due[0]); due[1].fn();
  }
  time = end;
}
function setup(sample = 0, scale = 1) {
  time = 0; timers.clear();
  const played = [];
  const stage = new Element(); const events = new EventTarget();
  stage.scale = scale;
  const state = new PetStateMachine(behavior, { playAnimation(id) {
    assert.ok(catalog[id], `playable catalog entry ${id}`); played.push(id);
  } }, new AnimationRegistry(definitions));
  state.start();
  const service = { isDragging: false, onDragMove: () => () => {}, onDragEnd: () => () => {} };
  const controller = new PetInteractionController(stage, service, state, events,
    () => time, () => { service.isDragging = true; state.beginDrag(); }, () => sample);
  controller.start();
  const emit = (type, x, y, id = 1) => {
    const event = new Event(type);
    // Test coordinates are relative to the original 220px interaction area.
    Object.assign(event, { button: 0, clientX: (x + 74) * scale, clientY: y * scale, pointerId: id });
    (type === 'pointerdown' ? stage : events).dispatchEvent(event);
  };
  return { played, state, controller, emit };
}
let checks = 0;
function test(name, fn) { fn(); checks++; console.log(`PASS ${name}`); }
test('every active registry entry resolves to existing, correctly counted assets', () => {
  for (const definition of definitions.filter(d => d.status === 'active')) {
    const clip = catalog[definition.runtimeClipId]; assert.ok(clip, definition.id);
    assert.equal(clip.frames, definition.frameCount, definition.id);
    for (const file of clip.files ?? [clip.file]) assert.ok(fs.existsSync(path.join(root, 'public', file)), file);
  }
});
for (const [region, x, clip] of [
  ['belly', 110, 'touch_belly_dislike'],
  ['left flipper', 20, 'touch_flipper_react_screen_left'],
  ['right flipper', 200, 'touch_flipper_react_screen_right'],
]) {
  test(`${region}: earliest reaction is 5 seconds from pointer down, only once`, () => {
    const h = setup(); h.emit('pointerdown', x, 120); advance(4999);
    assert.ok(!h.played.includes(clip)); advance(1); assert.equal(h.played.at(-1), clip);
    h.state.handleAnimationComplete(clip); assert.equal(h.state.currentState, 'Idle');
    advance(30000); assert.equal(h.played.filter(id => id === clip).length, 1);
    h.emit('pointerup', x, 120); assert.equal(h.played.at(-1), 'idle_breathe'); h.controller.dispose();
  });
}
test('upper random boundary triggers at 10 seconds', () => {
  const h = setup(1); h.emit('pointerdown', 110, 120); advance(9999);
  assert.ok(!h.played.includes('touch_belly_dislike')); advance(1);
  assert.equal(h.played.at(-1), 'touch_belly_dislike'); h.controller.dispose();
});
for (const ending of ['pointerup', 'pointercancel', 'drag', 'dispose']) {
  test(`${ending} cancels pending body reaction`, () => {
    const h = setup(); h.emit('pointerdown', 20, 120); advance(1000);
    if (ending === 'drag') h.emit('pointermove', 30, 120);
    else if (ending === 'dispose') h.controller.dispose();
    else h.emit(ending, 20, 120);
    advance(20000); assert.ok(!h.played.some(id => id.startsWith('touch_flipper_react')));
    h.controller.dispose();
  });
}
test('belly double click and flipper click never trigger impatience', () => {
  const h = setup();
  for (const x of [110, 110, 20, 200]) { h.emit('pointerdown', x, 120); advance(50); h.emit('pointerup', x, 120); }
  advance(20000);
  assert.ok(!h.played.includes('touch_belly_dislike'));
  assert.ok(!h.played.some(id => id.startsWith('touch_flipper_react'))); h.controller.dispose();
});
test('head hold retains its existing reaction timing and release behavior', () => {
  const h = setup(); h.emit('pointerdown', 110, 30); advance(400);
  assert.equal(h.played.at(-1), 'touch_head_pat_start');
  h.state.handleAnimationComplete('touch_head_pat_start'); assert.equal(h.played.at(-1), 'touch_head_pat_loop');
  advance(8999); assert.ok(!h.played.includes('touch_head_pat_push_away')); advance(1);
  assert.equal(h.played.at(-1), 'touch_head_pat_push_away'); h.emit('pointerup', 110, 30);
  assert.equal(h.played.at(-1), 'touch_head_pat_push_away'); h.controller.dispose();
});
test('second pointer session clears the previous timer', () => {
  const h = setup(); h.emit('pointerdown', 110, 120); advance(4500);
  h.emit('pointerdown', 200, 120, 2); advance(500);
  assert.ok(!h.played.includes('touch_belly_dislike')); advance(4500);
  assert.equal(h.played.at(-1), 'touch_flipper_react_screen_right'); h.controller.dispose();
});
for (const scale of [0.5, 1, 1.2]) {
  test(`render gutters do not trigger touches at ${scale * 100}% size`, () => {
    const h = setup(0, scale);
    for (const x of [-25, 245]) { h.emit('pointerdown', x, 120); advance(12000); h.emit('pointerup', x, 120); }
    assert.deepEqual(h.played, ['idle_breathe']); h.controller.dispose();
  });
  test(`body and flipper hit zones stay attached at ${scale * 100}% size`, () => {
    const h = setup(0, scale);
    for (const [x, expected] of [[110, 'touch_belly_dislike'], [20, 'touch_flipper_react_screen_left'], [200, 'touch_flipper_react_screen_right']]) {
      h.emit('pointerdown', x, 120); advance(5000); assert.equal(h.played.at(-1), expected);
      h.emit('pointerup', x, 120); h.state.handleAnimationComplete(expected);
    }
    h.controller.dispose();
  });
}
test('belly hold starts after 400ms and remains a loop until the reaction', () => {
  const h = setup(); h.emit('pointerdown', 110, 120); advance(399);
  assert.ok(!h.played.includes('touch_belly_rub_loop')); advance(1);
  assert.equal(h.played.at(-1), 'touch_belly_rub_loop');
  assert.equal(h.state.currentAction, 'BellyRub');
  for (let i = 0; i < 3; i++) h.state.handleAnimationComplete('touch_belly_rub_loop');
  assert.equal(h.played.at(-1), 'touch_belly_rub_loop');
  advance(4600); assert.equal(h.played.at(-1), 'touch_belly_dislike');
  h.state.handleAnimationComplete('touch_belly_rub_loop');
  assert.equal(h.played.at(-1), 'touch_belly_dislike');
  h.emit('pointerup', 110, 120);
  assert.equal(h.played.at(-1), 'touch_belly_dislike');
  h.state.handleAnimationComplete('touch_belly_dislike');
  assert.equal(h.played.at(-1), 'idle_breathe'); h.controller.dispose();
});
for (const ending of ['pointerup', 'pointercancel', 'drag', 'dispose', 'replacement']) {
  test(`belly ${ending} stops the enjoyment loop and cancels impatience`, () => {
    const h = setup(); h.emit('pointerdown', 110, 120); advance(2000);
    assert.equal(h.state.currentAction, 'BellyRub');
    if (ending === 'drag') h.emit('pointermove', 130, 120);
    else if (ending === 'dispose') h.controller.dispose();
    else if (ending === 'replacement') h.emit('pointerdown', -25, 120, 2);
    else h.emit(ending, 110, 120);
    assert.notEqual(h.state.currentAction, 'BellyRub');
    advance(20000); assert.ok(!h.played.includes('touch_belly_dislike'));
    h.controller.dispose();
  });
}
test('release cleanup never overrides a higher-priority reaction', () => {
  const h = setup(); h.emit('pointerdown', 110, 120); advance(600);
  h.state.requestAnimation('touch_head_pat_nip'); h.emit('pointerup', 110, 120);
  assert.equal(h.played.at(-1), 'touch_head_pat_nip'); h.controller.dispose();
});
for (const [side, x] of [['left', 20], ['right', 200]]) {
  const hold = `touch_flipper_hold_screen_${side}`;
  const react = `touch_flipper_react_screen_${side}`;
  test(`${side} flipper starts after 400ms, loops, and reaction survives release`, () => {
    const h = setup(); h.emit('pointerdown', x, 120); advance(399);
    assert.ok(!h.played.includes(hold)); advance(1);
    assert.equal(h.state.currentAction, 'FlipperHold'); assert.equal(h.played.at(-1), hold);
    h.state.handleAnimationComplete(hold); assert.equal(h.played.at(-1), hold);
    advance(4600); assert.equal(h.played.at(-1), react);
    h.state.handleAnimationComplete(hold); assert.equal(h.played.at(-1), react);
    h.emit('pointerup', x, 120); assert.equal(h.played.at(-1), react);
    h.state.handleAnimationComplete(react); assert.equal(h.state.currentState, 'Idle');
    advance(20000); assert.equal(h.played.filter(id => id === react).length, 1); h.controller.dispose();
  });
  for (const ending of ['pointerup', 'pointercancel', 'drag', 'dispose', 'replacement']) {
    test(`${side} flipper ${ending} stops loop without restarting it`, () => {
      const h = setup(); h.emit('pointerdown', x, 120); advance(800);
      assert.equal(h.state.currentAction, 'FlipperHold');
      if (ending === 'drag') h.emit('pointermove', x+15, 120);
      else if (ending === 'dispose') h.controller.dispose();
      else if (ending === 'replacement') h.emit('pointerdown', -25, 120, 2);
      else h.emit(ending, x, 120);
      assert.notEqual(h.state.currentAction, 'FlipperHold');
      h.state.handleAnimationComplete(hold); advance(20000);
      assert.notEqual(h.state.currentAction, 'FlipperHold'); assert.ok(!h.played.includes(react)); h.controller.dispose();
    });
  }
  test(`${side} flipper retains 10s upper trigger boundary with slower clips`, () => {
    const h=setup(1); h.emit('pointerdown',x,120); advance(9999);
    assert.equal(h.played.at(-1),hold); advance(1);assert.equal(h.played.at(-1),react);h.controller.dispose();
  });
}
test('formal flipper timings and enlarged gutters preserve the body hit area', () => {
  for (const side of ['left','right']) {
    const hold=catalog[`touch_flipper_hold_screen_${side}`];
    const react=catalog[`touch_flipper_react_screen_${side}`];
    assert.equal(hold.frameDurationsMs.reduce((a,b)=>a+b),4250);
    assert.equal(react.frameDurationsMs.reduce((a,b)=>a+b),2040);
    assert.equal(hold.frameWidth,368); assert.equal(react.frameWidth,368);
  }
});
console.log(`${checks} checks passed`);
