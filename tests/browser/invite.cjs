const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {randomUUID} = require('node:crypto');
(async () => {
 const html = fs.readFileSync('midflight/communication/invite.html', 'utf8');
 const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
 const nodes = new Map();
 const node = id => { if (!nodes.has(id)) nodes.set(id, {style:{},disabled:true,textContent:''}); return nodes.get(id); };
 const requests = [], storage = new Map(), downloads = [];
 let failures = 1;
 const access = {project:'invite_demo_test',expires_at:1900000000,tokens:{billing:'private'}};
 const context = {
  URLSearchParams, Blob, crypto:{randomUUID}, location:{hash:'#id=test&secret=invite-secret',origin:'https://example.com'},
  sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
  document:{getElementById:node,createElement:()=>({click(){}})},
  URL:{createObjectURL:b=>{downloads.push(b);return 'blob:test'},revokeObjectURL:()=>{}},setTimeout:()=>{},
  fetch:async (path,options)=>{requests.push({path,body:JSON.parse(options.body)});if(path.endsWith('/info'))return {ok:true,json:async()=>({remaining:2,expires_at:1900000000})};if(failures-- > 0)return {ok:false,json:async()=>({detail:'Retry safely'})};return {ok:true,json:async()=>access};}
 };
 vm.runInNewContext(script,context);
 await new Promise(setImmediate);
 assert.equal(node('create').disabled,false);
 await node('create').onclick();
 assert.equal(node('status').textContent,'Retry safely');
 assert.equal(node('create').disabled,false);
 await node('create').onclick();
 assert.equal(requests[1].body.request_id,requests[2].body.request_id);
 assert.equal(node('setup').style.display,'block');
 assert.deepEqual(JSON.parse(await downloads[0].text()),{...access,url:'https://example.com'});
 assert(node('commands').textContent.includes('midflight.communication.onboard'));
 assert(!node('commands').textContent.includes('private'));
 node('download').onclick();assert.equal(downloads.length,2);
 console.log('Invite page: stable retry, private file download and setup instructions passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
