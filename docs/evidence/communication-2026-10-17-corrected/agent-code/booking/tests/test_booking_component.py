import unittest
import shutil
import subprocess
from unittest.mock import patch

import app
import booking


class BookingComponent(unittest.TestCase):
    def test_valid_request_normalizes_text_and_preserves_cents(self):
        self.assertEqual(booking.booking_request(12345, " Ada ", " Main St "),
                         {"total_cents": 12345, "customer": "Ada", "destination": "Main St"})
        self.assertEqual(booking.booking_request(0, "Ada", "Main St")["total_cents"], 0)

    def test_invalid_amounts(self):
        for amount in (True, False, -1, 1.5, "100", None):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                booking.booking_request(amount, "Ada", "Main St")

    def test_invalid_customer_or_destination(self):
        for field in ("customer", "destination"):
            for value in (None, 123, "", " \n\t"):
                payload = {"total_cents": 100, "customer": "Ada", "destination": "Main St"}
                payload[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    booking.booking_request(**payload)

    def test_book_route_passes_validated_request_and_server_response(self):
        record = {"delivery_id": 7, "status": "cancelled", "total_cents": 100,
                  "refund_cents": 37}
        with patch.object(app.delivery, "create_delivery", return_value=record) as create:
            self.assertEqual(app.dispatch("/book", {"total_cents": 100,
                             "customer": " Ada ", "destination": " Main St "}), record)
            create.assert_called_once_with(total_cents=100, customer="Ada", destination="Main St")

    def test_invalid_booking_does_not_create_delivery(self):
        with patch.object(app.delivery, "create_delivery") as create:
            with self.assertRaises(ValueError):
                app.dispatch("/book", {"total_cents": -1, "customer": "Ada", "destination": "Main St"})
            create.assert_not_called()

    def test_page_exposes_form_and_displays_server_values_as_text(self):
        html = booking.page()
        self.assertIn("fetch('/book'", html)
        for field in ("status", "total_cents", "refund_cents"):
            self.assertIn(".textContent = data." + field, html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn("button.disabled = false", html)
        self.assertNotIn("innerHTML", html)

    @unittest.skipUnless(shutil.which("node"), "Node is needed to exercise browser JavaScript")
    def test_browser_submission_server_amounts_and_errors(self):
        script = booking.page().split("<script>", 1)[1].split("</script>", 1)[0]
        harness = r"""
const assert = require('node:assert/strict');
const elements = {};
for (const id of ['booking-form', 'submit', 'message', 'result', 'delivery-id', 'status', 'total', 'refund']) {
  elements[id] = {textContent: '', hidden: false, disabled: false};
}
const formElement = elements['booking-form'];
formElement.elements = {total_cents: {value: '100'}, customer: {value: 'Ada'}, destination: {value: 'Main St'}};
let submit;
formElement.addEventListener = (_, handler) => { submit = handler; };
global.document = {getElementById: id => elements[id]};
let request;
global.fetch = async (url, options) => {
  request = {url, options};
  return {ok: true, json: async () => ({delivery_id: 7, status: 'cancelled', total_cents: 100, refund_cents: 37})};
};
"""
        checks = r"""
(async () => {
  await submit({preventDefault() {}});
  assert.equal(request.url, '/book');
  assert.deepEqual(JSON.parse(request.options.body), {total_cents: 100, customer: 'Ada', destination: 'Main St'});
  assert.equal(elements.status.textContent, 'cancelled');
  assert.equal(elements.refund.textContent, 37);
  assert.equal(elements.total.textContent, 100);
  assert.equal(elements.result.hidden, false);
  assert.equal(elements.submit.disabled, false);
  global.fetch = async () => ({ok: false, json: async () => ({error: 'Invalid destination'})});
  await submit({preventDefault() {}});
  assert.equal(elements.message.textContent, 'Invalid destination');
  assert.equal(elements.result.hidden, true);
  assert.equal(elements.submit.disabled, false);
  global.fetch = async () => { throw new Error('Network unavailable'); };
  await submit({preventDefault() {}});
  assert.equal(elements.message.textContent, 'Network unavailable');
  assert.equal(elements.submit.disabled, false);
  formElement.elements.total_cents.value = '1.5';
  await submit({preventDefault() {}});
  assert.equal(elements.message.textContent, 'Enter a non-negative whole number of cents.');
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
        result = subprocess.run([shutil.which("node"), "-e", harness + script + checks],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
