const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
class Element {
  constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.style={};this.attributes={};this.hidden=false;this.textContent='';this.offsetHeight=160;}
  append(child){child.parent=this;this.children.push(child);}
  replaceChildren(...children){this.children=[];children.forEach(c=>this.append(c));}
  setAttribute(k,v){this.attributes[k]=v;}
  getBoundingClientRect(){return {left:0,top:48,right:1000,bottom:648,width:1000,height:600};}
  contains(e){return this===e||this.children.some(c=>c.contains?.(e));}
  remove(){this.parent.children=this.parent.children.filter(c=>c!==this);}
  focus(){}
}
const host=new Element('div'),panel=new Element('aside'),screen=new Element('screen');
const document={getElementById:id=>id==='claim-badges'?host:panel,querySelector:()=>screen,
 createElement:tag=>new Element(tag),createTextNode:text=>({textContent:text}),addEventListener(){}};
const html=fs.readFileSync('midflight/theater/terminal.html','utf8');
const start=html.indexOf('function installClaimBadges('),end=html.indexOf('\n(async()=>',start);
const context=vm.createContext({document,window:{addEventListener(){}},innerWidth:1000,innerHeight:700});
vm.runInContext(html.slice(start,end)+'\nthis.makeBadges=installClaimBadges;',context);
const badges=context.makeBadges({cols:100,rows:40});
const finding={explanation:'Delivery returns a mapping; Billing expects a list.',proposed_correction:'Return a list of record snapshots.'};
const status={layout:{billing:{x:0,y:1,width:49,height:19},delivery:{x:50,y:1,width:49,height:19}},
 claim_statuses:{billing:{state:'approved',claim_id:'C-1',revision:1,plan_version:1,history:[]},
 delivery:{state:'needs_revision',claim_id:'C-2',revision:1,plan_version:1,findings:[finding],history:[]}}};
const text=e=>(e.textContent||'')+e.children?.map(text).join('');
badges.paint(status);
assert.equal(host.children.length,2);
assert.match(text(host.children[0]),/APPROVED/);
assert.match(text(host.children[1]),/NEEDS REVISION/);
assert.equal(host.children[1].dataset.state,'needs_revision');
host.children[1].onclick();
assert.equal(panel.hidden,false);
assert.equal(host.children[1].attributes['aria-expanded'],'true');
assert.match(text(panel),/Delivery returns a mapping/);
assert.match(text(panel),/Fix: Return a list/);
const close=panel.children[0];badges.paint(status);
assert.equal(panel.children[0],close,'Unchanged polling must preserve the open card and focus');
status.claim_statuses.delivery={state:'approved',claim_id:'C-2',revision:2,plan_version:1,
 history:[{revision:1,state:'needs_revision',findings:[finding]}]};
badges.paint(status);
assert.match(text(host.children[1]),/APPROVED/);
assert.match(text(panel),/Earlier revisions/);
assert.match(text(panel),/r1 · NEEDS REVISION/);
assert.match(text(panel),/does not mean implementation or tests have passed/);
badges.clear();assert.equal(host.children.length,0);assert.equal(panel.hidden,true);
console.log('Claim badges: actual verdict labels, readable corrections, history, stable polling and reset passed');
