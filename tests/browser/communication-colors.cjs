const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('midflight/communication/terminal.html', 'utf8');
const block = html.split('// BEGIN DEMO TEXT COLORS')[1].split('// END DEMO TEXT COLORS')[0];
const source = block.slice(block.indexOf('\n') + 1);
const {classify, ownerAt} = vm.runInNewContext(source + ';({classify:demoColorRanges,ownerAt:paneAgentAt})');
for (const name of ['midflight.send', 'theater_midflight.join']) {
  const ranges = classify('Called ' + name);
  assert.equal(ranges.length, 1);
  assert.equal(ranges[0].color, '#79bdff');
}
for (const label of ['midflight.object', 'theater_midflight.object', 'objection #7',
                     'objections', 'OBJECTION', 'open_objections', 'objection_id']) {
  const ranges = classify('Called ' + label);
  assert.equal(ranges.length, 1);
  assert.equal(ranges[0].color, '#ff6b6b');
  assert.equal(('Called ' + label).slice(ranges[0].start, ranges[0].end), label);
}
assert.equal(classify('object objects objective objectionable midflight.object_extra').length, 0);
const mixed = classify('Called midflight.object: objection #7 from Delivery agent', () => 'billing');
assert.equal(mixed.map(r => r.color).join(','), '#ff6b6b,#ff6b6b,#f7ba55');
for (const owner of ['billing', 'delivery', 'booking', 'notifications']) {
  for (const mentioned of ['Billing', 'Delivery', 'Booking', 'Notifications']) {
    const ranges = classify('Following the ' + mentioned + ' agent’s interface.', () => owner);
    assert.equal(ranges.length, owner === mentioned.toLowerCase() ? 0 : 1);
    if (ranges.length) assert.equal(ranges[0].color, '#f7ba55');
  }
}
assert.equal(classify('Billing agent Delivery agent').length, 0); // Unknown panel: no guess.
assert.equal(classify('I changed the consumer; adapted to policy revision 2.', () => 'billing').length, 0);
assert.equal(classify('midflight.send_extra').length, 0);
const layout = {billing:{x:0,y:1,width:40,height:15}, delivery:{x:41,y:1,width:40,height:15}};
assert.equal(ownerAt(layout, 4, 0), null); // Title row.
assert.equal(ownerAt(layout, 40, 4), null); // Separator.
assert.equal(ownerAt(layout, 4, 4), 'billing');
assert.equal(ownerAt(layout, 44, 4), 'delivery');
const line = 'Billing agent sees Delivery agent        Delivery agent sees Billing agent';
const ranges = classify(line, i => ownerAt(layout, i, 4));
assert.equal(ranges.length, 2);
assert.equal(line.slice(ranges[0].start, ranges[0].end), 'Delivery agent');
assert.equal(line.slice(ranges[1].start, ranges[1].end), 'Billing agent');
new vm.Script(html.split('<script>')[1].split('</script>')[0]);
console.log('Panel-aware highlighting checks passed');
