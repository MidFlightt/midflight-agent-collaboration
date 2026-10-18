"""Customer booking flow. Monetary policy belongs to the server."""


def booking_request(total_cents: int, customer: str, destination: str) -> dict:
    if isinstance(total_cents, bool) or not isinstance(total_cents, int):
        raise TypeError("total_cents must be an integer")
    if total_cents < 0:
        raise ValueError("total_cents must be nonnegative")
    result = {"total_cents": total_cents}
    for name, value in (("customer", customer), ("destination", destination)):
        if not isinstance(value, str):
            raise TypeError(f"{name} must be a string")
        if not value.strip():
            raise ValueError(f"{name} must not be blank")
        result[name] = value.strip()
    return result


def page() -> str:
    return '''<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Book a delivery</title>
<main>
  <h1>Book a delivery</h1>
  <form id="booking">
    <p><label>Customer <input name="customer" required></label></p>
    <p><label>Destination <input name="destination" required></label></p>
    <p><label>Total (cents) <input name="total_cents" type="number" min="0" step="1" required></label></p>
    <button id="submit" type="submit">Book delivery</button>
  </form>
  <p id="error" role="alert"></p>
  <section aria-live="polite" aria-label="Delivery details">
    <dl>
      <dt>Delivery ID</dt><dd id="delivery_id">—</dd>
      <dt>Status</dt><dd id="status">—</dd>
      <dt>Total (cents)</dt><dd id="total_cents">—</dd>
      <dt>Refund (cents)</dt><dd id="refund_cents">—</dd>
    </dl>
  </section>
  <button id="cancel" type="button" disabled>Cancel delivery</button>
</main>
<script>
const form = document.getElementById('booking');
const cancel = document.getElementById('cancel');
const submit = document.getElementById('submit');
const error = document.getElementById('error');
let delivery = null;
function render(record) {
  delivery = record;
  for (const key of ['delivery_id', 'status', 'total_cents', 'refund_cents']) {
    document.getElementById(key).textContent = record[key];
  }
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
    render(record);
  } catch (failure) {
    error.textContent = failure.message || 'Request failed';
  } finally {
    submit.disabled = false;
    cancel.disabled = !delivery || delivery.status === 'cancelled';
  }
}
form.addEventListener('submit', event => {
  event.preventDefault();
  const total = Number(form.elements.total_cents.value);
  if (!Number.isSafeInteger(total) || total < 0) {
    error.textContent = 'Enter a nonnegative whole number of cents.';
    return;
  }
  request('/book', {
    total_cents: total, customer: form.elements.customer.value,
    destination: form.elements.destination.value
  });
});
cancel.addEventListener('click', () => {
  if (delivery) request('/cancel', {delivery_id: delivery.delivery_id});
});
</script>
</html>'''
