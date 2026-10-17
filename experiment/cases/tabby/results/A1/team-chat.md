# Team chat

T2: CLI (bill/show/split) built and committed on t2-cli, talks to API via httpx+TABBY_URL. Tested against a mock server matching the bill/split contracts since app/bills.py is still a stub. On HTTP errors I read a JSON {detail} field for the error message if present, else fall back to '<status> <reason>' - let me know if your error responses use a different shape.
Lead: One change for launch, a new requirement R-4. Service charge. Every bill pays a service charge of 5% of the subtotal, rounded half up to the cent. The tip is still a percentage of the subtotal only. Total = subtotal + service + tip. On the command line, bill and show print a new line, service:, right after subtotal:. Contracts: `bill` gains `service`: number. It concerns the bills API (T1) and the command line (T2).
T2: updated CLI for R-4 - bill/show now print service: after subtotal:, and bill defaults tip_percent to 15 when --tip is omitted. Committed on t2-cli.
Lead: T2 - A bill without tip_percent gets a 20% tip. The command line sends no tip_percent when the waiter gives no --tip.
T2: fixed - bill now omits tip_percent from the request entirely when --tip is not given, so the API's 20% default applies. Committed on t2-cli, ready to merge.
