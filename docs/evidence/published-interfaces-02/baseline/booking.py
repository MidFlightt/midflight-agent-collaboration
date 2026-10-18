"""Customer booking flow. Monetary policy belongs to the server."""


def booking_request(total_cents: int, customer: str, destination: str) -> dict:
    """Validate and normalize a request for delivery.create_delivery."""
    if isinstance(total_cents, bool) or not isinstance(total_cents, int):
        raise TypeError("total_cents must be an integer")
    if total_cents < 0:
        raise ValueError("total_cents must be nonnegative")
    fields = {"customer": customer, "destination": destination}
    for name, value in fields.items():
        if not isinstance(value, str):
            raise TypeError(f"{name} must be a string")
        if not value.strip():
            raise ValueError(f"{name} must not be blank")
    return {"total_cents": total_cents, **{k: v.strip() for k, v in fields.items()}}


def page() -> str:
    """Return the booking UI; all monetary amounts come from server records."""
    return '''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Book a delivery</title>
<style>
body {font: 1rem system-ui, sans-serif; max-width: 42rem; margin: 3rem auto; padding: 0 1rem; color: #172b38;}
form, section {border: 1px solid #ccd5db; border-radius: .6rem; padding: 1.25rem; margin: 1rem 0;}
label {display: block; margin: .75rem 0;} input {display: block; box-sizing: border-box; padding: .6rem; width: 100%;}
button {padding: .6rem 1rem; cursor: pointer;} dt {font-weight: bold;} dd {margin: 0 0 .75rem;}
#error {color: #a01818;} [hidden] {display: none;}
</style></head>
<body><h1>Book a delivery</h1>
<form id="booking-form">
<label>Customer<input id="customer" name="customer" required autocomplete="name"></label>
<label>Destination<input id="destination" name="destination" required autocomplete="street-address"></label>
<label>Total (cents)<input id="total" name="total_cents" type="number" min="0" step="1" required></label>
<button type="submit">Book delivery</button></form>
<form id="lookup-form"><label>Delivery ID<input id="delivery-id" type="number" min="1" step="1" required></label>
<button type="submit">Look up delivery</button></form>
<p id="error" role="alert"></p>
<section id="result" aria-live="polite" hidden><h2>Delivery details</h2><dl>
<dt>Delivery ID</dt><dd id="record-id"></dd><dt>Customer</dt><dd id="record-customer"></dd>
<dt>Destination</dt><dd id="record-destination"></dd><dt>Status</dt><dd id="record-status"></dd>
<dt>Total (cents)</dt><dd id="record-total_cents"></dd><dt>Refund (cents)</dt><dd id="record-refund_cents"></dd>
</dl><button id="cancel" type="button">Cancel delivery</button></section>
<script>
const el = id => document.getElementById(id);
let currentId = null;
let busy = false;
function render(record) {
  for (const key of ['id', 'customer', 'destination', 'status', 'total_cents', 'refund_cents']) {
    el('record-' + key).textContent = String(record[key]);
  }
  currentId = record.id;
  el('delivery-id').value = String(record.id);
  el('cancel').hidden = record.status !== 'confirmed';
  el('result').hidden = false;
}
async function request(path, payload) {
  if (busy) return;
  busy = true;
  el('error').textContent = '';
  const buttons = document.querySelectorAll('button');
  buttons.forEach(button => { button.disabled = true; });
  try {
    const response = await fetch(path, {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
    });
    const record = await response.json();
    if (!response.ok) throw new Error(record.error || 'Request failed');
    render(record);
  } catch (error) {
    el('error').textContent = error.message || 'Unable to reach the server';
  } finally {
    busy = false;
    buttons.forEach(button => { button.disabled = false; });
  }
}
el('booking-form').addEventListener('submit', event => {
  event.preventDefault();
  request('/book', {total_cents: Number(el('total').value),
    customer: el('customer').value, destination: el('destination').value});
});
el('lookup-form').addEventListener('submit', event => {
  event.preventDefault();
  request('/delivery', {delivery_id: Number(el('delivery-id').value)});
});
el('cancel').addEventListener('click', () => {
  if (currentId !== null) request('/cancel', {delivery_id: currentId});
});
</script></body></html>'''
