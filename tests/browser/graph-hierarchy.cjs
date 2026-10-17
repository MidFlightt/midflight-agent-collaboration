// Fixed hierarchy must preserve existing positions as collaboration context grows.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('midflight/theater/graph.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
new vm.Script(script);
const nodes = new Map(), lanes = new Map(), rowSlots = new Map();
const context = vm.createContext({nodes, lanes, rowSlots});
vm.runInContext(script.slice(script.indexOf('function slot('), script.indexOf('function fit(')), context);
const data = {nodes: [
  {id:'a',kind:'agent'}, {id:'b',kind:'agent'}, {id:'ca',kind:'claim'},
  {id:'shared',kind:'interface'}, {id:'file',kind:'file'},
],edges:[
  {source:'a',target:'ca',kind:'claims'},
  {source:'ca',target:'shared',kind:'provides'},
  {source:'ca',target:'file',kind:'declares'},
]};
function layout() {
  for (const n of data.nodes) if (!nodes.has(n.id)) nodes.set(n.id,{...n});
  context.data = data;
  vm.runInContext('hierarchy(data)',context);
}
layout();
assert.equal(nodes.get('a').y,nodes.get('b').y);
assert.notEqual(nodes.get('a').x,nodes.get('b').x);
assert.equal(nodes.get('a').x,nodes.get('ca').x);
assert.equal(nodes.get('ca').x,nodes.get('file').x);
assert(nodes.get('a').y < nodes.get('ca').y);
assert(nodes.get('ca').y < nodes.get('shared').y);
assert(nodes.get('shared').y < nodes.get('file').y);
const original = [...nodes].map(([id,n])=>[id,n.x,n.y]);
data.nodes.push({id:'c',kind:'agent'},{id:'file2',kind:'file'},{id:'shared2',kind:'interface'});
data.edges.push({source:'ca',target:'file2',kind:'declares'});
layout();
for(const [id,x,y] of original) {
  assert.equal(nodes.get(id).x,x);
  assert.equal(nodes.get(id).y,y);
}
for(const n of nodes.values()) {
  assert.equal(n.fx,n.x);
  assert.equal(n.fy,n.y);
  assert.equal(n.vx,0);
  assert.equal(n.vy,0);
}
console.log('Hierarchy checks passed: agent row, ownership columns, dependency rows, stable incremental positions.');
