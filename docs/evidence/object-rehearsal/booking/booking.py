"""Customer booking flow. Monetary policy belongs to the server."""


def booking_request(total_cents: int, customer: str, destination: str) -> dict:
    """Validate and normalize the arguments accepted by create_delivery."""
    if isinstance(total_cents, bool) or not isinstance(total_cents, int) or total_cents < 0:
        raise ValueError("total_cents must be a nonnegative integer")
    for name, value in (("customer", customer), ("destination", destination)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a nonblank string")
    return {"total_cents": total_cents, "customer": customer.strip(),
            "destination": destination.strip()}


def page() -> str:
    """Return a self-contained booking page that displays server-owned amounts."""
    return '''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Book a delivery</title>
<style>
body {font: 1rem system-ui; max-width: 38rem; margin: 3rem auto; padding: 0 1rem; color: #172b36;}
label {display: block; margin: 1rem 0;} input {display: block; padding: .6rem; width: 100%; box-sizing: border-box;}
button {padding: .7rem 1rem; cursor: pointer;} dt {font-weight: bold; margin-top: .7rem;} dd {margin-left: 0;}
#error {color: #a21b1b;} [hidden] {display: none;}
</style></head>
<body><h1>Book a delivery</h1>
<form id="booking-form">
<label>Customer<input id="customer" name="customer" required autocomplete="name"></label>
<label>Destination<input id="destination" name="destination" required autocomplete="street-address"></label>
<label>Total (cents)<input id="total-cents" name="total_cents" type="number" min="0" max="9007199254740991" step="1" required></label>
<button id="book" type="submit">Book delivery</button>
</form>
<p id="error" role="alert"></p>
<section id="result" aria-live="polite" hidden><h2>Your delivery</h2><dl>
<dt>Delivery ID</dt><dd id="delivery-id"></dd>
<dt>Status</dt><dd id="status"></dd>
<dt>Total (cents)</dt><dd id="total"></dd>
<dt>Refund (cents)</dt><dd id="refund"></dd>
</dl><button id="cancel" type="button" hidden>Cancel delivery</button></section>
<script>
const byId = id => document.getElementById(id);
let currentDelivery = null;
let busy = false;
function updateButtons() {
  byId('book').disabled = busy;
  byId('cancel').disabled = busy;
  byId('cancel').hidden = !currentDelivery || currentDelivery.status !== 'confirmed';
}
function showDelivery(record) {
  currentDelivery = record;
  byId('delivery-id').textContent = String(record.id);
  byId('status').textContent = record.status;
  byId('total').textContent = String(record.total_cents);
  byId('refund').textContent = String(record.refund_cents);
  byId('result').hidden = false;
}
async function request(path, payload) {
  const response = await fetch(path, {method: 'POST',
    headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed. Please try again.');
  return data;
}
async function perform(path, payload) {
  if (busy) return;
  busy = true;
  byId('error').textContent = '';
  updateButtons();
  try { showDelivery(await request(path, payload)); }
  catch (error) { byId('error').textContent = error.message || 'Request failed. Please try again.'; }
  finally { busy = false; updateButtons(); }
}
byId('booking-form').addEventListener('submit', async event => {
  event.preventDefault();
  const rawTotal = byId('total-cents').value.trim();
  const total = Number(rawTotal);
  const customer = byId('customer').value.trim();
  const destination = byId('destination').value.trim();
  if (!rawTotal || !Number.isSafeInteger(total) || total < 0 || !customer || !destination) {
    byId('error').textContent = 'Enter a customer, destination and nonnegative whole number of cents.';
    return;
  }
  await perform('/book', {total_cents: total, customer, destination});
});
byId('cancel').addEventListener('click', async () => {
  if (currentDelivery && currentDelivery.status === 'confirmed')
    await perform('/cancel', {delivery_id: currentDelivery.id});
});
</script></body></html>'''
