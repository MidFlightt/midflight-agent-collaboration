"""Isolated booking tests; peer implementations are not exercised."""
import re
import shutil
import subprocess
import unittest

import booking


class BookingValidation(unittest.TestCase):
    def test_normalizes_and_preserves_cents(self):
        self.assertEqual(booking.booking_request(123, ' Ada ', ' Home '),
                         dict(total_cents=123, customer='Ada', destination='Home'))
        self.assertEqual(booking.booking_request(0, 'A', 'B')['total_cents'], 0)

    def test_rejects_invalid_values(self):
        for value in (True, False, -1, 1.5, '100', None):
            with self.subTest(total=value), self.assertRaises(ValueError):
                booking.booking_request(value, 'A', 'B')
        for field in ('customer', 'destination'):
            for value in ('', '  ', None, 42, []):
                args = dict(total_cents=100, customer='A', destination='B')
                args[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    booking.booking_request(**args)

    @unittest.skipUnless(shutil.which('node'), 'Node required for browser script test')
    def test_browser_requests_and_server_values(self):
        script = re.search(r'<script>(.*?)</script>', booking.page(), re.S).group(1)
        harness = r'''
const assert = require('node:assert/strict');
const elements = new Map();
const element = id => {
    if (!elements.has(id)) elements.set(id, {_value: '', get value() {return this._value;},
        set value(value) {this._value = String(value);}, textContent: '', hidden: true,
        name: id, handlers: {}, addEventListener(event, fn) {this.handlers[event] = fn;}});
    return elements.get(id);
};
global.document = {getElementById: element, querySelectorAll: () => []};
let requests = [];
let failed = false;
global.fetch = async (path, options) => {
    requests.push([path, JSON.parse(options.body)]);
    return {ok: !failed, json: async () => failed ? {error: '<server error>'} :
        {id: 7, customer: '<Ada>', destination: 'Home', status: 'cancelled',
         total_cents: 1000, refund_cents: 317}};
};
'''
        checks = r'''
(async () => {
    element('customer').value = 'Ada'; element('destination').value = 'Home';
    element('total').value = '1000';
    element('booking-form').handlers.submit({preventDefault() {}});
    await new Promise(resolve => setImmediate(resolve));
    assert.deepEqual(requests[0], ['/book', {total_cents:1000, customer:'Ada', destination:'Home'}]);
    assert.equal(element('record-refund').textContent, '317');
    assert.equal(element('record-status').textContent, 'cancelled');
    assert.equal(element('record-customer').textContent, '<Ada>');
    assert.equal(element('result').hidden, false);
    element('cancel').handlers.click();
    await new Promise(resolve => setImmediate(resolve));
    assert.deepEqual(requests[1], ['/cancel', {delivery_id:7}]);
    element('lookup-form').handlers.submit({preventDefault() {}});
    await new Promise(resolve => setImmediate(resolve));
    assert.deepEqual(requests[2], ['/delivery', {delivery_id:7}]);
    failed = true;
    await perform(() => submitRequest('/delivery', {delivery_id:7}));
    assert.equal(element('error').textContent, '<server error>');
    element('total').value = '1.5';
    const count = requests.length;
    element('booking-form').handlers.submit({preventDefault() {}});
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(requests.length, count);
    assert.match(element('error').textContent, /valid integer/);
})().catch(error => {console.error(error); process.exitCode = 1;});
'''
        result = subprocess.run(['node', '-e', harness + script + checks],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
