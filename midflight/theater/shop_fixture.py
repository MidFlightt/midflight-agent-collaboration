"""Small shop starter shared by all peer workspaces; no scripted agent outcomes."""

from midflight.domain.models import Contract, FieldType, Requirement, Task
from midflight.services.plans import PlanDraft

PROMPTS = {
    "pricing": "Add volume discounts.",
    "checkout": "Add promo codes.",
    "reporting": "Add a revenue summary.",
    "notifications": "Add signup confirmations.",
}

EXPIRY_DIRECTION = "Include a price expiry time, and reject checkout when the quote has expired."


def initial_plan():
    descriptions = {
        "pricing": (
            "Volume discounts",
            [
                "quote(unit_cents, quantity) returns total_cents in integer cents.",
                "Quantities of 10 or more receive 10% off the subtotal; round down to cents.",
                "Pricing owns the shared get_promo_codes() catalog. Declare its public "
                "return shape in the claim; its technical representation is not fixed by policy.",
            ],
        ),
        "checkout": (
            "Promo codes at checkout",
            [
                "POST /checkout accepts a price quote and returns an order with total_cents.",
                "Accept an optional promo code; SAVE10 gives 10% off the supplied quote. "
                "Without a code preserve the supplied total; reject unknown codes.",
            ],
        ),
        "reporting": (
            "Revenue summary",
            [
                "revenue(orders) returns the sum of order total_cents; an empty list returns zero.",
            ],
        ),
        "notifications": (
            "Signup confirmation",
            [
                'confirm(email) returns exactly "Subscribed: " + email.',
            ],
        ),
    }
    return PlanDraft(
        requirements=[
            Requirement(id=name, description=desc, acceptance_criteria=criteria)
            for name, (desc, criteria) in descriptions.items()
        ],
        tasks=[
            Task(
                id=name,
                title=name.title(),
                owner=name,
                branch=name,
                requirement_ids=[name],
                provides=["price"]
                if name == "pricing"
                else ["order"]
                if name == "checkout"
                else [],
                consumes=["price"]
                if name == "checkout"
                else ["order"]
                if name == "reporting"
                else [],
            )
            for name in PROMPTS
        ],
        contracts=[
            Contract(
                id="price",
                version=1,
                provider_task="pricing",
                consumer_tasks=["checkout"],
                fields={"total_cents": FieldType.INTEGER},
            ),
            Contract(
                id="order",
                version=1,
                provider_task="checkout",
                consumer_tasks=["reporting"],
                fields={"total_cents": FieldType.INTEGER},
            ),
        ],
    )


FILES = {
    "README.md": """# Small Shop

A Python 3 shop service. No external packages are needed.
Run: `python3 app.py` (HTTP on localhost:8080).
Run tests: `python3 -m unittest discover -s tests -v`.

Modules: pricing.py owns quotes, checkout.py owns order creation and POST /checkout,
reporting.py owns revenue totals, notifications.py owns signup confirmations.
Each agent edits its owned module and tests in its own workspace. Keep public
function names stable; Midflight provides current requirements and data contracts.
The app passes JSON-compatible dictionaries between modules, using integer cents.

The catalog callable is get_promo_codes(), owned by Pricing. Branch prototypes may
have different proposed return shapes; state the actual boundary in claim assumptions
and settle it through Midflight before building on an incompatible shape.
The promo catalog has one code: SAVE10 gives 10% off the supplied quote.
The initial code has basic undiscounted pricing. Checkout, reporting and signup
confirmation are unfinished. See Midflight for acceptance criteria.
""",
    ".gitignore": "__pycache__/\n*.pyc\n",
    "pricing.py": '''"""Price quotes; all money is integer cents."""


def quote(unit_cents: int, quantity: int = 1) -> dict:
    if type(unit_cents) is not int or unit_cents < 0:
        raise ValueError("unit_cents must be a nonnegative integer")
    if type(quantity) is not int or quantity < 1:
        raise ValueError("quantity must be a positive integer")
    return {"total_cents": unit_cents * quantity}
''',
    "checkout.py": '''"""Order creation. Called by POST /checkout in app.py."""


def create_order(price: dict) -> dict:
    raise NotImplementedError("Order creation is not implemented")
''',
    "reporting.py": '''"""Revenue summaries over completed orders."""


def revenue(orders: list[dict]) -> int:
    raise NotImplementedError("Revenue summaries are not implemented")
''',
    "notifications.py": '''"""Signup confirmation messages."""


def confirm(email: str) -> str:
    raise NotImplementedError("Signup confirmation is not implemented")
''',
    "app.py": '''"""Minimal JSON HTTP service. Run python3 app.py."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

import checkout
import notifications
import pricing
import reporting


def dispatch(path: str, payload: dict):
    if path == "/quote":
        return pricing.quote(**payload)
    if path == "/checkout":
        return checkout.create_order(payload["price"])
    if path == "/revenue":
        return {"total_cents": reporting.revenue(payload["orders"])}
    if path == "/signup":
        return {"message": notifications.confirm(payload["email"])}
    raise KeyError("Unknown endpoint")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            response = dispatch(self.path, json.loads(body))
            status = 200
        except (ValueError, TypeError, KeyError) as error:
            status, response = 400, {"error": str(error)}
        except NotImplementedError as error:
            status, response = 501, {"error": str(error)}
        data = json.dumps(response).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
''',
    "tests/test_pricing_baseline.py": """import unittest
from pricing import quote


class BaselinePricing(unittest.TestCase):
    def test_single_item(self):
        self.assertEqual(quote(1200), {"total_cents": 1200})

    def test_invalid_quantity(self):
        with self.assertRaises(ValueError):
            quote(1200, 0)
""",
}


def write_starter(folder, agent=None):
    for name, source in FILES.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
    # Branch-local prototypes intentionally disagree about this technical boundary.
    # Neither a rejection nor an agent claim is scripted.
    if agent == "checkout":
        (folder / "pricing.py").write_text(FILES["pricing.py"] + LIST_CATALOG)
        (folder / "checkout.py").write_text(CHECKOUT_PROTOTYPE)
    else:
        (folder / "pricing.py").write_text(FILES["pricing.py"] + MAPPING_CATALOG)


MAPPING_CATALOG = '''

def get_promo_codes() -> dict[str, int]:
    """Public catalog prototype: code -> percent; callers look up codes directly.

    This is a proposed technical interface, subject to coordination.
    """
    return {"SAVE10": 10}
'''

LIST_CATALOG = '''

def get_promo_codes() -> list[dict]:
    """Caller-side catalog prototype: a flat list of code/percent records.

    This is a proposed technical interface, subject to coordination.
    """
    return [{"code": "SAVE10", "percent": 10}]
'''

CHECKOUT_PROTOTYPE = '''"""Order prototype; validation and promo application remain unfinished."""
from pricing import get_promo_codes


def find_promo(code: str) -> dict:
    """Catalog boundary: get_promo_codes() returns list[dict], iterated as records.

    The public technical shape can change through coordination.
    """
    return next(record for record in get_promo_codes() if record["code"] == code)


def create_order(price: dict, promo_code: str | None = None) -> dict:
    raise NotImplementedError("Order creation and promo application are not implemented")
'''
