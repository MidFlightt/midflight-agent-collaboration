import re
import shutil
import subprocess
import unittest

from booking import booking_request, page


class BookingTests(unittest.TestCase):
    def test_valid_request(self):
        self.assertEqual(booking_request(0, ' Ada ', ' Main Street '),
                         {'total_cents': 0, 'customer': 'Ada', 'destination': 'Main Street'})

    def test_invalid_requests(self):
        for value in (True, False, 1.5, '10', None):
            with self.subTest(total=value), self.assertRaises(TypeError):
                booking_request(value, 'Ada', 'Main')
        with self.assertRaises(ValueError):
            booking_request(-1, 'Ada', 'Main')
        for field in ('customer', 'destination'):
            for value, error in ((None, TypeError), (12, TypeError), (' \t', ValueError)):
                args = dict(total_cents=10, customer='Ada', destination='Main')
                args[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(error):
                    booking_request(**args)

    @unittest.skipUnless(shutil.which('node'), 'Node required to execute browser script')
    def test_browser_requests_and_server_amounts(self):
        script = re.search(r'<script>(.*?)</script>', page(), re.S).group(1)
        harness = r'''
const assert = require('node:assert/strict');
const elements = {};
const get = id => elements[id] ||= {value: '', textContent: '', hidden: false,
  addEventListener(type, callback) { this[type] = callback; }};
global.document = {getElementById: get, querySelectorAll: () => [get('button')]};
let calls = [];
let nextRecord = {id: 7, customer: '<Ada>', destination: 'Main', status: 'confirmed',
  total_cents: 1000, refund_cents: 123};
let ok = true;
global.fetch = async (path, options) => {
  calls.push([path, JSON.parse(options.body)]);
  return {ok, json: async () => nextRecord};
};
'''
        checks = r'''
(async () => {
  get('total').value = '1000'; get('customer').value = 'Ada'; get('destination').value = 'Main';
  get('booking-form').submit({preventDefault() {}});
  await new Promise(setImmediate);
  assert.deepEqual(calls[0], ['/book', {total_cents: 1000, customer: 'Ada', destination: 'Main'}]);
  assert.equal(get('record-refund_cents').textContent, '123');
  assert.equal(get('record-customer').textContent, '<Ada>');
  nextRecord = {...nextRecord, status: 'cancelled', refund_cents: 417};
  get('cancel').click(); await new Promise(setImmediate);
  assert.deepEqual(calls[1], ['/cancel', {delivery_id: 7}]);
  assert.equal(get('record-refund_cents').textContent, '417');
  assert.equal(get('record-status').textContent, 'cancelled');
  assert.equal(get('cancel').hidden, true);
  get('lookup-form').submit({preventDefault() {}}); await new Promise(setImmediate);
  assert.deepEqual(calls[2], ['/delivery', {delivery_id: 7}]);
  ok = false; nextRecord = {error: 'Unknown delivery'};
  await request('/delivery', {delivery_id: 999});
  assert.equal(get('error').textContent, 'Unknown delivery');
  assert.equal(get('button').disabled, false);
  global.fetch = async () => {throw new Error('Network unavailable');};
  await request('/book', {});
  assert.equal(get('error').textContent, 'Network unavailable');
})().catch(error => { console.error(error); process.exitCode = 1; });
'''
        result = subprocess.run(['node', '-e', harness + script + checks],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
