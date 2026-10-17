// Only agents and shared interfaces are visible; hidden claims retain provenance.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const script=fs.readFileSync('midflight/theater/graph.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
new vm.Script(script);
const nodes=new Map(),lanes=new Map(),rowSlots=new Map();
const context=vm.createContext({nodes,lanes,rowSlots});
vm.runInContext(script.slice(script.indexOf('function slot('),script.indexOf('function fit(')),context);
const raw={plan_version:2,nodes:[
 {id:'a',kind:'agent'},{id:'b',kind:'agent'},{id:'unrelated',kind:'agent'},
 {id:'ca',kind:'claim',label:'C-1',state:'approved'}, {id:'cb',kind:'claim',label:'C-2'},
 {id:'shared',kind:'interface',label:'Price'}, {id:'file',kind:'file',label:'price.py'},
 {id:'d',kind:'directive',state:'delivered',plan_version:2},
],edges:[
 {source:'a',target:'ca',kind:'claims'},{source:'b',target:'cb',kind:'claims'},
 {source:'ca',target:'shared',kind:'provides',fields:{total_cents:'integer'}},
 {source:'cb',target:'shared',kind:'consumes',fields:{total_cents:'integer'}},
 {source:'ca',target:'file',kind:'declares'},{source:'d',target:'b',kind:'notifies'},
]};
function layout(){
 context.raw=raw;
 const data=vm.runInContext('simplify(raw)',context);
 for(const n of data.nodes)if(!nodes.has(n.id))nodes.set(n.id,{...n});
 context.data=data;vm.runInContext('hierarchy(data)',context);return data;
}
const view=layout();
assert.deepEqual(Array.from(view.nodes,n=>n.kind),['agent','agent','agent','interface']);
assert(view.edges.some(e=>e.source==='a'&&e.target==='shared'&&e.kind==='provides'));
assert(view.edges.some(e=>e.source==='shared'&&e.target==='b'&&e.kind==='consumes'));
assert.equal(view.nodes.find(n=>n.id==='a').files[0],'price.py');
assert.equal(view.nodes.find(n=>n.id==='a').claims[0].id,'ca');
assert.equal(view.nodes.find(n=>n.id==='b').change,'pending');
assert.equal(view.nodes.find(n=>n.id==='unrelated').change,null);
assert.equal(nodes.get('a').y,nodes.get('b').y);
assert(nodes.get('a').y<nodes.get('shared').y);
const original=[...nodes].map(([id,n])=>[id,n.x,n.y]);
raw.nodes.push({id:'new-agent',kind:'agent'},{id:'file2',kind:'file',label:'test.py'});
raw.edges.push({source:'ca',target:'file2',kind:'declares'});
raw.nodes.find(n=>n.id==='d').state='acknowledged';
const updated=layout();
assert.equal(updated.nodes.find(n=>n.id==='b').change,'acknowledged');
for(const [id,x,y] of original){assert.equal(nodes.get(id).x,x);assert.equal(nodes.get(id).y,y)}
for(const n of nodes.values()){assert.equal(n.fx,n.x);assert.equal(n.fy,n.y)}
console.log('Simplified graph checks passed: two node types, directed dependencies, provenance, selective colors, stable positions.');
