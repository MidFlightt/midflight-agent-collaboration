// Run with node tests/browser/terminal-colors.cjs. No paid agents or DOM dependency.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('midflight/theater/terminal.html', 'utf8');
const block = html.split('// BEGIN DEMO TEXT COLORS')[1].split('// END DEMO TEXT COLORS')[0];
const source = block.slice(block.indexOf('\n') + 1);
const classify = vm.runInNewContext(source + ';demoColorRanges');
const matches = text => Array.from(classify(text), r => [text.slice(r.start, r.end), r.color]);
assert.deepEqual(matches('Called theater_midflight.check_in({"task_id":"pricing"})'), [['theater_midflight.check_in','#79bdff']]);
assert.deepEqual(matches('Task pricing: Pricing (plan v2). No changes since your last check-in.'), [['plan v2','#7cdae7'],['No changes since your last check-in','#9499a3']]);
assert.deepEqual(matches('Requirement subscription-billing: We will do subscription based'), [['subscription-billing','#f7ba55'],['We will do subscription based','#f7ba55']]);
assert.deepEqual(matches('Your claim C-2 rev 2: APPROVED'), [['APPROVED','#65d8ac']]);
assert.deepEqual(matches('Acknowledged D-3; billing_interval="monthly"; subscription_id required'), [['Acknowledged','#65d8ac'],['D-3','#c4aaff'],['billing_interval','#f7ba55'],['monthly','#f7ba55'],['subscription_id','#f7ba55']]);
assert.deepEqual(matches('FAILED │ No changes since your last check-in'), [['FAILED','#ff8d91'],['No changes since your last check-in','#9499a3']]);
assert.equal(classify('Ordinary agent explanation without coordination keywords.').length, 0);
assert.equal(matches('✓ APPROVED')[0][0], 'APPROVED');
assert.equal(classify('Next time, pass since=pricing.123 to get only what changed.').length, 0);
console.log('9 semantic text-color cases passed');
