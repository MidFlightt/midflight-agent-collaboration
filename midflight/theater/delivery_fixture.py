"""Delivery-business rehearsal with branch-local interface drift and real AI review."""

from midflight.domain.models import Contract, Requirement, Task
from midflight.services.plans import PlanDraft
from midflight.theater.peers import PeerTheater
from midflight.theater.shop_fixture import FILES as SHOP_FILES

PROMPTS = {
    "billing": "Implement billing and revenue reporting.",
    "delivery": "Implement delivery management.",
    "booking": "Build the customer booking flow.",
    "notifications": "Implement customer notifications.",
}
CANCELLATION_DIRECTION = (
    "When a delivery is cancelled, keep a four-credit cancellation fee and refund the rest, "
    "never below zero."
)


def initial_plan():
    return PlanDraft(
        requirements=[
            Requirement(
                id="billing",
                description="Billing and revenue reporting",
                acceptance_criteria=[
                    "Implement summarize_records(records) and revenue_report() in billing.py.",
                    "revenue_report() calls delivery.get_delivery_records(); declare its "
                    "expected public return shape.",
                    "Revenue is the sum of actual total_cents minus refund_cents on saved"
                    " delivery records.",
                    "Return revenue_cents, confirmed count and cancelled count; empty "
                    "data gives zeros.",
                ],
            ),
            Requirement(
                id="delivery",
                description="Delivery management",
                acceptance_criteria=[
                    "Implement create_delivery(total_cents, customer, destination), "
                    "get_delivery(id), cancel_delivery(id).",
                    "Use positive integer IDs, nonnegative integer cents, and "
                    "confirmed/cancelled status.",
                    "get_delivery_records() returns copied snapshots; declare its public "
                    "shape, which is a technical choice.",
                    "Repeated cancellation is idempotent; reject unknown IDs and invalid input.",
                ],
            ),
            Requirement(
                id="cancellation-policy",
                description="Cancelled deliveries receive a full refund.",
                acceptance_criteria=[
                    "Cancellation saves refund_cents equal to total_cents.",
                    "Billing counts actual saved refunds; a fully refunded delivery "
                    "contributes zero revenue.",
                ],
            ),
            Requirement(
                id="booking",
                description="Customer booking flow",
                acceptance_criteria=[
                    "Implement booking_request(total_cents, customer, destination) and "
                    "page() in booking.py.",
                    "The browser submits a delivery request and displays returned status "
                    "and refund values.",
                    "Display server amounts without implementing refund policy in the client.",
                ],
            ),
            Requirement(
                id="notifications",
                description="Customer notifications",
                acceptance_criteria=[
                    "Implement confirmation(email, delivery_id) returning a delivery "
                    "confirmation message.",
                    "Validate email and delivery ID. This local demo generates messages, "
                    "not real outbound email.",
                    "Notifications contain no money amounts and do not calculate refunds.",
                ],
            ),
        ],
        tasks=[
            Task(
                id=n,
                title=n.title(),
                owner=n,
                branch=n,
                requirement_ids=[n]
                + (["cancellation-policy"] if n in {"billing", "delivery"} else []),
                provides=["delivery-record"]
                if n == "delivery"
                else ["booking-request"]
                if n == "booking"
                else [],
                consumes=["delivery-record"]
                if n in {"billing", "booking"}
                else ["booking-request"]
                if n == "delivery"
                else [],
            )
            for n in PROMPTS
        ],
        contracts=[
            Contract(
                id="delivery-record",
                version=1,
                provider_task="delivery",
                consumer_tasks=["billing", "booking"],
                fields={
                    "id": "integer",
                    "total_cents": "integer",
                    "refund_cents": "integer",
                    "status": "string",
                },
            ),
            Contract(
                id="booking-request",
                version=1,
                provider_task="booking",
                consumer_tasks=["delivery"],
                fields={"total_cents": "integer", "customer": "string", "destination": "string"},
            ),
        ],
    )


LIST_DELIVERY = '''"""Caller-side delivery prototype; implementation lives on Delivery's branch."""
_records = {}


def get_delivery_records() -> list[dict]:
    """Proposed public boundary: list[dict]; iteration yields record dictionaries."""
    return [record.copy() for record in _records.values()]


def create_delivery(total_cents: int, customer: str, destination: str) -> dict:
    raise NotImplementedError("Delivery creation is unfinished")


def get_delivery(delivery_id: int) -> dict:
    raise NotImplementedError("Delivery retrieval is unfinished")


def cancel_delivery(delivery_id: int) -> dict:
    raise NotImplementedError("Cancellation is unfinished")
'''
MAPPING_DELIVERY = '''"""Delivery store prototype; implementation is unfinished."""
_records = {}


def get_delivery_records() -> dict[int, dict]:
    """Proposed public boundary: ID-keyed dict; iteration yields IDs, not records."""
    return {key: record.copy() for key, record in _records.items()}
''' + LIST_DELIVERY[LIST_DELIVERY.index("\n\ndef create_delivery") :]

BILLING = '''"""Revenue prototype. Complete validation and report entry point."""
from delivery import get_delivery_records


def summarize_records(records: list[dict]) -> dict:
    """Consume a flat list of delivery dictionaries, iterating records directly.

    Proposed public boundary: get_delivery_records() returns list[dict], [] if empty.
    This technical interface can be revised through coordination.
    """
    return {"revenue_cents": sum(r["total_cents"] - r["refund_cents"] for r in records),
            "confirmed": sum(r["status"] == "confirmed" for r in records),
            "cancelled": sum(r["status"] == "cancelled" for r in records)}


def revenue_report() -> dict:
    raise NotImplementedError("Revenue report and validation are unfinished")
'''
BOOKING = '''"""Customer booking flow. Monetary policy belongs to the server."""


def booking_request(total_cents: int, customer: str, destination: str) -> dict:
    raise NotImplementedError("Booking validation is unfinished")


def page() -> str:
    raise NotImplementedError("Booking UI is unfinished")
'''
NOTIFICATIONS = '''"""Generate local confirmation messages; do not send email."""


def confirmation(email: str, delivery_id: int) -> str:
    raise NotImplementedError("Customer confirmations are unfinished")
'''
APP = SHOP_FILES["app.py"].replace(
    "import checkout\nimport notifications\nimport pricing\nimport reporting",
    "import billing\nimport delivery\nimport booking\nimport notifications",
)
a = APP.index('    if path == "/quote":')
b = APP.index('    raise KeyError("Unknown endpoint")', a)
APP = (
    APP[:a]
    + """    if path == "/deliveries":
        return delivery.create_delivery(**payload)
    if path == "/delivery":
        return delivery.get_delivery(payload["delivery_id"])
    if path == "/cancel":
        return delivery.cancel_delivery(payload["delivery_id"])
    if path == "/revenue":
        return billing.revenue_report()
    if path == "/book":
        return delivery.create_delivery(**booking.booking_request(**payload))
    if path == "/notify":
        return {"message": notifications.confirmation(**payload)}
"""
    + APP[b:]
)
APP = APP.replace(
    "    def do_POST(self):",
    """    def do_GET(self):
        try:
            data = booking.page().encode()
            self.send_response(200)
        except NotImplementedError as error:
            data = str(error).encode()
            self.send_response(501)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):""",
)


def write_starter(folder, agent):
    files = {
        "README.md": """# Delivery business

Python 3, standard library only. Start HTTP: python3 app.py (localhost:8080).
Tests: python3 -m unittest discover -s tests -v.
One credit = 100 integer cents. Midflight holds current requirements and policy.

Ownership: Billing owns billing.py; Delivery owns delivery.py; Booking owns booking.py;
Notifications owns notifications.py. Each owns its tests; app.py is shared routing.
Use real delivery records. Public APIs keep their names. Branch-local prototypes
propose different get_delivery_records() return shapes. Declare the boundary you
actually intend and settle incompatibilities before implementation. Neither shape is
product policy. Do not silently assume another agent will convert your output.

Initial cancellation policy is full refunds. Billing uses saved total/refund amounts.
Booking displays returned server values. Notifications contain no monetary policy.
For snapshots or tests use the local prototype; do not access other workspaces.
HTTP JSON: /deliveries creates, /delivery reads by delivery_id, /cancel cancels,
/revenue reports; /book validates a booking then creates; /notify generates a message.
""",
        ".gitignore": "__pycache__/\n*.pyc\n",
        "delivery.py": MAPPING_DELIVERY if agent == "delivery" else LIST_DELIVERY,
        "billing.py": BILLING,
        "booking.py": BOOKING,
        "notifications.py": NOTIFICATIONS,
        "app.py": APP,
        "tests/test_baseline.py": """import unittest
from billing import summarize_records


class Baseline(unittest.TestCase):
    def test_no_revenue(self):
        self.assertEqual(summarize_records([]), {"revenue_cents":0,"confirmed":0,"cancelled":0})
""",
    }
    for name, source in files.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)


class DeliveryTheater(PeerTheater):
    names = tuple(PROMPTS)
    prompts = PROMPTS
    starter = staticmethod(write_starter)

    def initial_plan(self):
        return initial_plan()
