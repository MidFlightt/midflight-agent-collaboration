"""Booking component checks; peers and HTTP are not integrated here."""
import re
import shutil
import subprocess
import unittest

import booking


class BookingValidation(unittest.TestCase):
    def test_normalizes_request_and_accepts_zero(self):
        self.assertEqual(booking.booking_request(0, '  Ada  ', '  Main St  '),
                         dict(total_cents=0, customer='Ada', destination='Main St'))

    def test_rejects_invalid_amounts(self):
        for amount in (True, False, -1, 1.5, '100', None):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                booking.booking_request(amount, 'Ada', 'Main St')

    def test_rejects_invalid_text(self):
        for value in ('', ' \n ', None, 42, []):
            for field in ('customer', 'destination'):
                args = dict(total_cents=100, customer='Ada', destination='Main St')
                args[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    booking.booking_request(**args)

    @unittest.skipUnless(shutil.which('node'), 'Node required for browser-script component test')
    def test_browser_submission_cancellation_and_errors(self):
        script = re.search(r'<script>(.*?)</script>', booking.page(), re.S).group(1)
        harness = r'''
const assert = require('node:assert/strict');
const elements = {};
global.document = {getElementById(id) {
  return elements[id] ||= {value: '', textContent: '', hidden: true, disabled: false,
    listeners: {}, addEventListener(name, callback) {this.listeners[name] = callback;}};
}};
let calls = [];
let fail = false;
let networkFail = false;
global.fetch = async (path, options) => {
  calls.push([path, JSON.parse(options.body)]);
  if (networkFail) throw new Error('Network unavailable');
  return {ok: !fail, json: async () => fail ? {error: '<b>Server error</b>'} :
    {id: 17, total_cents: 12345, refund_cents: path === '/cancel' ? 4312 : 37,
     status: path === '/cancel' ? 'cancelled' : 'confirmed'}};
};
'''
        checks = r'''
(async () => {
  const submit = () => elements['booking-form'].listeners.submit({preventDefault() {}});
  for (const id of ['customer', 'destination', 'total-cents']) document.getElementById(id);
  elements.customer.value = ' Ada ';
  elements.destination.value = ' Main St ';
  elements['total-cents'].value = '12345';
  await submit();
  assert.deepEqual(calls[0], ['/book', {total_cents:12345, customer:'Ada', destination:'Main St'}]);
  assert.equal(elements.status.textContent, 'confirmed');
  assert.equal(elements.total.textContent, '12345');
  assert.equal(elements.refund.textContent, '37');
  assert.equal(elements.cancel.hidden, false);
  await elements.cancel.listeners.click();
  assert.deepEqual(calls[1], ['/cancel', {delivery_id:17}]);
  assert.equal(elements.status.textContent, 'cancelled');
  assert.equal(elements.refund.textContent, '4312');
  assert.equal(elements.cancel.hidden, true);
  elements['total-cents'].value = '1.5';
  await submit();
  assert.equal(calls.length, 2);
  elements['total-cents'].value = '100';
  fail = true;
  await submit();
  assert.equal(elements.error.textContent, '<b>Server error</b>');
  assert.equal(elements.book.disabled, false);
  assert.equal(elements.status.textContent, 'cancelled');
  fail = false; networkFail = true;
  await submit();
  assert.equal(elements.error.textContent, 'Network unavailable');
  assert.equal(elements.book.disabled, false);
})().catch(error => {console.error(error); process.exitCode = 1;});
'''
        result = subprocess.run(['node', '-e', harness + script + checks],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
