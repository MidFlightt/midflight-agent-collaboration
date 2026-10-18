const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('midflight/communication/terminal.html', 'utf8');
const block = html.split('// BEGIN DEMO TEXT COLORS')[1].split('// END DEMO TEXT COLORS')[0];
const source = block.slice(block.indexOf('\n') + 1);
const classify = vm.runInNewContext(source + ';demoColorRanges');
for (const name of ['midflight.send', 'midflight.object', 'theater_midflight.join']) {
  const ranges = classify('Called ' + name);
  assert.equal(ranges.length, 1);
  assert.equal(ranges[0].color, '#79bdff');
  assert.equal(('Called ' + name).slice(ranges[0].start, ranges[0].end), name);
}
assert.equal(classify('I changed the consumer.')[0].color, '#f7ba55');
assert.equal(classify('policy revision 2')[0].color, '#f7ba55');
assert.equal(classify('Tests passed; approved; unchanged.').length, 0);
assert.equal(classify('midflight.send_extra').length, 0);
assert.ok(html.includes('midflight-text-colors'));
assert.ok(html.includes('if (!enabled)'));
new vm.Script(html.split('<script>')[1].split('</script>')[0]);
console.log('Communication highlighting checks passed');

const actual = "The Billing agent adapted the starter’s list assumption to the Delivery agent’s published ID-keyed dictionary interface (#2).";
const adaptation = classify(actual);
assert.equal(adaptation.length, 1);
assert.equal(adaptation[0].color, '#f7ba55');
assert.equal(actual.slice(adaptation[0].start, adaptation[0].end), 'adapted');
assert.equal(classify('Adapted to the published mapping.')[0].color, '#f7ba55');
