"""Customer booking flow. Monetary policy belongs to the server."""


def booking_request(total_cents: int, customer: str, destination: str) -> dict:
    """Validate a booking and return the delivery creation arguments."""
    if isinstance(total_cents, bool) or not isinstance(total_cents, int) or total_cents < 0:
        raise ValueError("total_cents must be a non-negative integer")
    fields = {}
    for name, value in (("customer", customer), ("destination", destination)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        fields[name] = value.strip()
    return {"total_cents": total_cents, **fields}


def page() -> str:
    """Render a booking form; all displayed monetary values come from the server."""
    return """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Book a delivery</title>
<style>
body { font: 1rem system-ui, sans-serif; max-width: 36rem; margin: 3rem auto; padding: 0 1rem; }
label { display: block; margin-top: 1rem; } input { box-sizing: border-box; width: 100%; padding: .6rem; }
button { margin-top: 1rem; padding: .7rem 1rem; } dt { font-weight: bold; } dd { margin: 0 0 1rem; }
</style></head>
<body><main><h1>Book a delivery</h1>
<form id="booking-form">
<label for="customer">Customer</label><input id="customer" name="customer" required>
<label for="destination">Destination</label><input id="destination" name="destination" required>
<label for="total_cents">Total (cents)</label>
<input id="total_cents" name="total_cents" type="number" min="0" step="1" required>
<button id="submit" type="submit">Book delivery</button>
</form>
<p id="message" role="status" aria-live="polite"></p>
<dl id="result" hidden>
<dt>Delivery ID</dt><dd id="delivery-id"></dd>
<dt>Status</dt><dd id="status"></dd>
<dt>Total (cents)</dt><dd id="total"></dd>
<dt>Refund (cents)</dt><dd id="refund"></dd>
</dl></main>
<script>
const form = document.getElementById('booking-form');
const button = document.getElementById('submit');
const message = document.getElementById('message');
const result = document.getElementById('result');
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  result.hidden = true;
  const total = Number(form.elements.total_cents.value);
  if (!Number.isSafeInteger(total) || total < 0) {
    message.textContent = 'Enter a non-negative whole number of cents.';
    return;
  }
  button.disabled = true;
  message.textContent = 'Submitting booking…';
  try {
    const response = await fetch('/book', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({total_cents: total,
        customer: form.elements.customer.value,
        destination: form.elements.destination.value})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Booking failed.');
    document.getElementById('delivery-id').textContent = data.delivery_id;
    document.getElementById('status').textContent = data.status;
    document.getElementById('total').textContent = data.total_cents;
    document.getElementById('refund').textContent = data.refund_cents;
    result.hidden = false;
    message.textContent = 'Booking submitted.';
  } catch (error) {
    message.textContent = error.message || 'Unable to submit booking.';
  } finally {
    button.disabled = false;
  }
});
</script></body></html>"""
