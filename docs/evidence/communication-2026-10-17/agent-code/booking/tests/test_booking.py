import json
import re
import shutil
import subprocess
import unittest
from unittest.mock import patch

import app
from booking import booking_request, page


class BookingTests(unittest.TestCase):
    def test_valid_request_normalizes_text_and_allows_zero(self):
        self.assertEqual(booking_request(0, ' Ada ', ' Main Street '),
                         dict(total_cents=0, customer='Ada', destination='Main Street'))

    def test_rejects_invalid_amounts(self):
        for value in [True, False, 1.5, '100', None]:
            with self.subTest(value=value), self.assertRaises(TypeError):
                booking_request(value, 'Ada', 'Main Street')
        with self.assertRaises(ValueError):
            booking_request(-1, 'Ada', 'Main Street')

    def test_rejects_missing_customer_or_destination(self):
        for field in ['customer', 'destination']:
            for value, error in [(None, TypeError), (1, TypeError), ('', ValueError), (' \n ', ValueError)]:
                payload = dict(total_cents=100, customer='Ada', destination='Main Street')
                payload[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(error):
                    booking_request(**payload)

    def test_book_dispatch_passes_validated_request(self):
        with patch.object(app.delivery, 'create_delivery', return_value={'status': 'confirmed'}) as create:
            self.assertEqual(app.dispatch('/book', dict(total_cents=100, customer=' Ada ', destination=' Main ')),
                             {'status': 'confirmed'})
            create.assert_called_once_with(total_cents=100, customer='Ada', destination='Main')

    @unittest.skipUnless(shutil.which('node'), 'Node required for browser script component test')
    def test_browser_submits_displays_server_refund_and_recovers_from_errors(self):
        script = re.search(r'<script>(.*?)</script>', page(), re.S).group(1)
        harness = r'''
const assert = require('node:assert/strict');
const nodes = {};
for (const key of ['booking','cancel','submit','error','delivery_id','status','total_cents','refund_cents']) {
  nodes[key] = {textContent:'', disabled:false, addEventListener(type, handler) {this[type] = handler;}};
}
nodes.booking.elements = {total_cents:{value:'1000'}, customer:{value:'Ada'}, destination:{value:'Main'}};
global.document = {getElementById: key => nodes[key]};
let calls = [];
let result = {delivery_id:7, status:'confirmed', total_cents:1000, refund_cents:0};
let ok = true;
global.fetch = async (path, options) => {
  calls.push([path, JSON.parse(options.body)]);
  return {ok, json:async () => result};
};
'''
        assertions = r'''
(async () => {
  const tick = () => new Promise(resolve => setImmediate(resolve));
  nodes.booking.submit({preventDefault(){}});
  await tick();
  assert.deepEqual(calls[0], ['/book', {total_cents:1000, customer:'Ada', destination:'Main'}]);
  assert.equal(nodes.status.textContent, 'confirmed');
  assert.equal(nodes.refund_cents.textContent, 0);
  assert.equal(nodes.cancel.disabled, false);
  result = {delivery_id:7, status:'cancelled', total_cents:1000, refund_cents:375};
  nodes.cancel.click();
  await tick();
  assert.deepEqual(calls[1], ['/cancel', {delivery_id:7}]);
  assert.equal(nodes.status.textContent, 'cancelled');
  assert.equal(nodes.total_cents.textContent, 1000);
  assert.equal(nodes.refund_cents.textContent, 375);
  assert.equal(nodes.cancel.disabled, true);
  ok = false; result = {error:'Server rejected booking'};
  nodes.booking.submit({preventDefault(){}});
  await tick();
  assert.equal(nodes.error.textContent, 'Server rejected booking');
  assert.equal(nodes.submit.disabled, false);
  global.fetch = async () => {throw new Error('Network unavailable');};
  nodes.booking.submit({preventDefault(){}});
  await tick();
  assert.equal(nodes.error.textContent, 'Network unavailable');
  assert.equal(nodes.submit.disabled, false);
})().catch(error => {console.error(error); process.exitCode = 1;});
'''
        completed = subprocess.run(['node', '-e', harness + script + assertions], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
