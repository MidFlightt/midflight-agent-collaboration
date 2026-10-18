"""Customer booking flow. Monetary policy belongs to the server."""


def booking_request(total_cents: int, customer: str, destination: str) -> dict:
    """Validate a booking and preserve the delivery service's input fields."""
    if isinstance(total_cents, bool) or not isinstance(total_cents, int) or total_cents < 0:
        raise ValueError("total_cents must be a nonnegative integer")
    for name, value in (("customer", customer), ("destination", destination)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a nonblank string")
    return {"total_cents": total_cents, "customer": customer, "destination": destination}


def page() -> str:
    """Render a booking form that displays authoritative server amounts."""
    return '''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Book a delivery</title></head>
<body>
<main>
<h1>Book a delivery</h1>
<form id="booking">
<p><label>Customer <input name="customer" required></label></p>
<p><label>Destination <input name="destination" required></label></p>
<p><label>Total (cents) <input name="total_cents" type="number" min="0" step="1" required></label></p>
<button id="submit" type="submit">Book delivery</button>
</form>
<p id="error" role="alert"></p>
<section id="result" aria-live="polite" hidden>
<h2>Delivery</h2>
<dl><dt>ID</dt><dd id="delivery-id"></dd>
<dt>Status</dt><dd id="status"></dd>
<dt>Total (cents)</dt><dd id="total"></dd>
<dt>Refund (cents)</dt><dd id="refund"></dd></dl>
<button id="cancel" type="button">Cancel delivery</button>
</section>
</main>
<script>
const form = document.getElementById('booking');
const submit = document.getElementById('submit');
const cancel = document.getElementById('cancel');
const error = document.getElementById('error');
let deliveryId = null;
function display(record) {
  deliveryId = record.id;
  document.getElementById('delivery-id').textContent = record.id;
  document.getElementById('status').textContent = record.status;
  document.getElementById('total').textContent = record.total_cents;
  document.getElementById('refund').textContent = record.refund_cents;
  document.getElementById('result').hidden = false;
  cancel.hidden = record.status === 'cancelled';
}
async function request(path, payload) {
  error.textContent = '';
  submit.disabled = true;
  cancel.disabled = true;
  try {
    const response = await fetch(path, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const record = await response.json();
    if (!response.ok) throw new Error(record.error || 'Request failed');
    display(record);
  } catch (failure) {
    error.textContent = failure.message || 'Request failed';
  } finally {
    submit.disabled = false;
    cancel.disabled = false;
  }
}
form.addEventListener('submit', event => {
  event.preventDefault();
  const fields = new FormData(form);
  const total = Number(fields.get('total_cents'));
  if (!Number.isSafeInteger(total) || total < 0) {
    error.textContent = 'Total must be a nonnegative integer in cents';
    return;
  }
  request('/book', {total_cents: total, customer: fields.get('customer'),
                    destination: fields.get('destination')});
});
cancel.addEventListener('click', () => {
  if (deliveryId !== null) request('/cancel', {delivery_id: deliveryId});
});
</script>
</body></html>'''
