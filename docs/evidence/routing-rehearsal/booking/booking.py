"""Customer booking flow. Monetary policy belongs to the server."""


def booking_request(total_cents: int, customer: str, destination: str) -> dict:
    """Validate and normalize the arguments accepted by delivery creation."""
    if isinstance(total_cents, bool) or not isinstance(total_cents, int) or total_cents < 0:
        raise ValueError("total_cents must be a nonnegative integer")
    for name, value in (("customer", customer), ("destination", destination)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a nonempty string")
    return {"total_cents": total_cents, "customer": customer.strip(),
            "destination": destination.strip()}


def page() -> str:
    """Return a self-contained UI that displays server-saved monetary values."""
    return '''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Book a delivery</title>
<style>
body { font: 1rem system-ui, sans-serif; max-width: 38rem; margin: 2rem auto; padding: 0 1rem; }
label { display: block; margin: 1rem 0; } input { display: block; padding: .5rem; width: 95%; }
button { padding: .6rem 1rem; margin: .3rem 0; } dt { font-weight: bold; } dd { margin: 0 0 .7rem; }
#error { color: #a00; }
</style></head>
<body><main><h1>Book a delivery</h1>
<form id="booking-form">
<label>Customer<input id="customer" name="customer" required></label>
<label>Destination<input id="destination" name="destination" required></label>
<label>Total (integer cents)<input id="total" name="total_cents" type="number" min="0" step="1" required></label>
<button type="submit">Book delivery</button></form>
<h2>Manage a delivery</h2><form id="lookup-form">
<label>Delivery ID<input id="delivery-id" name="delivery_id" type="number" min="1" step="1" required></label>
<button type="submit">Refresh status</button>
<button id="cancel" type="button">Cancel delivery</button></form>
<p id="error" role="alert"></p>
<section id="result" aria-live="polite" hidden><h2>Delivery details</h2><dl>
<dt>Delivery ID</dt><dd id="record-id"></dd>
<dt>Customer</dt><dd id="record-customer"></dd>
<dt>Destination</dt><dd id="record-destination"></dd>
<dt>Status</dt><dd id="record-status"></dd>
<dt>Total (cents)</dt><dd id="record-total"></dd>
<dt>Refund (cents)</dt><dd id="record-refund"></dd>
</dl></section></main>
<script>
const byId = id => document.getElementById(id);
function integerValue(id, minimum) {
    const raw = byId(id).value.trim();
    const value = Number(raw);
    if (raw === '' || !Number.isSafeInteger(value) || value < minimum) {
        throw new Error('Enter a valid integer for ' + byId(id).name + '.');
    }
    return value;
}
function showRecord(record) {
    for (const [element, key] of [['id', 'id'], ['customer', 'customer'],
        ['destination', 'destination'], ['status', 'status'],
        ['total', 'total_cents'], ['refund', 'refund_cents']]) {
        byId('record-' + element).textContent = String(record[key]);
    }
    byId('delivery-id').value = record.id;
    byId('result').hidden = false;
}
async function submitRequest(path, payload) {
    const response = await fetch(path, {method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    const record = await response.json();
    if (!response.ok) throw new Error(record.error || 'Request failed.');
    showRecord(record);
}
let pending = false;
async function perform(action) {
    if (pending) return;
    pending = true;
    byId('error').textContent = '';
    const buttons = document.querySelectorAll('button');
    buttons.forEach(button => button.disabled = true);
    try { await action(); }
    catch (error) { byId('error').textContent = error.message || 'Request failed.'; }
    finally { pending = false; buttons.forEach(button => button.disabled = false); }
}
byId('booking-form').addEventListener('submit', event => {
    event.preventDefault();
    perform(() => submitRequest('/book', {total_cents: integerValue('total', 0),
        customer: byId('customer').value, destination: byId('destination').value}));
});
byId('lookup-form').addEventListener('submit', event => {
    event.preventDefault();
    perform(() => submitRequest('/delivery', {delivery_id: integerValue('delivery-id', 1)}));
});
byId('cancel').addEventListener('click', () => {
    perform(() => submitRequest('/cancel', {delivery_id: integerValue('delivery-id', 1)}));
});
</script></body></html>'''
