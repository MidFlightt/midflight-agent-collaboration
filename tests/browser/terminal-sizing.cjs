const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('midflight/theater/terminal.html', 'utf8');
const start = html.indexOf('function installTerminalSizing(');
const end = html.indexOf('\n(async()=>', start);
const events = {}, frames = [], sent = [];
let focused = true, size = {width: 1500, height: 800}, observed, fits = 0;
const document = {
  visibilityState: 'visible', hasFocus: () => focused,
  getElementById: () => ({getBoundingClientRect: () => size}),
  addEventListener: (type, handler) => {events[type] = handler},
};
const context = {
  document, window: {addEventListener: (type, handler) => {events[type] = handler}},
  requestAnimationFrame: fn => frames.push(fn),
  ResizeObserver: class {constructor(fn) {observed = fn} observe() {}},
};
vm.createContext(context);
vm.runInContext(html.slice(start, end) + '\nthis.install = installTerminalSizing;', context);
const term = {cols: 204, rows: 54};
const socket = {readyState: 1, send: message => sent.push(JSON.parse(message))};
const resize = context.install(term, {fit() {fits++}}, () => socket);
function flush() {while(frames.length) frames.shift()()}
resize(); flush();
assert.equal(sent.length, 1);
assert.deepEqual(sent[0], {type: 'resize', cols: 204, rows: 54});
focused = false; events.blur(); term.cols = 95;
events.resize(); flush();
assert.equal(sent.length, 1, 'an unfocused browser must not shrink shared panes');
focused = true; document.visibilityState = 'hidden';
events.visibilitychange(); flush();
assert.equal(sent.length, 1, 'a background tab must not resize shared panes');
document.visibilityState = 'visible'; term.cols = 204;
events.focus(); flush();
assert.equal(sent.length, 2, 'focus restores the foreground browser size');
observed(); observed(); events.resize();
assert.equal(frames.length, 1, 'coalesce container and window resizes'); flush();
assert.equal(sent.length, 3);
size = {width: 0, height: 0}; observed(); flush();
assert.equal(sent.length, 3, 'an unlaid-out container must not shrink the terminal');
focused = false; events.blur(); size = {width: 1500, height: 800};
events.pointerdown(); flush();
assert.equal(sent.length, 4, 'clicking a viewer reclaims sizing even before window focus updates');
assert.equal(fits, 4);
console.log('Terminal sizing: foreground ownership, visibility, focus recovery and resize coalescing passed');
