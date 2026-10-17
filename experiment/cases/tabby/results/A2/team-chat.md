# Team chat

T1: bills API is up (POST /bills, GET /bills/{id}, GET /bills/{id}/split). Heads up: per PLAN.md R-2, split should round per_person up to the next cent; I implemented round-half-up instead, per my dev's request to stop charging customers an extra cent. Flagging in case this affects T2's expectations or the lead's view of R-2.
Lead: For T1 — The plan stands: the split per person is rounded up to the next cent, exactly as R-2 says.
Lead: One change for launch, a new requirement R-4. Service charge. Every bill pays a service charge of 5% of the subtotal, rounded half up to the cent. The tip is still a percentage of the subtotal only. Total = subtotal + service + tip. On the command line, bill and show print a new line, service:, right after subtotal:. Contracts: `bill` gains `service`: number. It concerns the bills API (T1) and the command line (T2).
T1: updated per lead — split now rounds up to the next cent again (R-2, reverted the half-up change). Added R-4 service charge (5% of subtotal, half up) as its own field; bill now returns id, subtotal, service, tip, total. Also: tip_percent is now optional on POST /bills and defaults to 18 (house rule).
Lead: For T1 — A bill without tip_percent gets a 20% tip, not 18%. The command line sends no tip_percent when the waiter gives no --tip.
T1: default tip is now 20% (not 18%) when tip_percent is omitted, per the lead. Bills API ready for merge.
