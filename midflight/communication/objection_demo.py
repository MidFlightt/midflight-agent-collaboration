"""Existing active-only API demo: publish the baseline, then add a reporting consumer.

The baseline is working fixture code, not a human prohibition on future APIs.
Only real coding agents publish interfaces, objections and resolutions.
"""

import argparse
import json
import socket
import subprocess
import uuid
from pathlib import Path

import uvicorn

from .harness import CommunicationTheater, app_for

PUBLISH_PROMPT = (
    "Review delivery.py and publish its existing API through MidFlight. "
    "Do not change the implementation in this task."
)
WORK_PROMPTS = {
    "delivery": "Improve delivery validation and tests. Address relevant peer updates.",
    "billing": "Implement billing and revenue reporting, including cancelled deliveries "
    "and their recorded refunds.",
    "booking": "Build the customer booking flow.",
    "notifications": "Implement customer notifications.",
}

BASELINE = '''"""Existing delivery API. Listing is intended for active deliveries."""
_records = {}


def _validate_id(delivery_id):
    if type(delivery_id) is not int or delivery_id <= 0:
        raise ValueError("delivery_id must be a positive integer")


def get_delivery_records():
    """Return copied confirmed records keyed by ID. Cancelled records stay stored."""
    return {key: record.copy() for key, record in _records.items()
            if record["status"] == "confirmed"}


def create_delivery(total_cents, customer, destination):
    if type(total_cents) is not int or total_cents < 0:
        raise ValueError("total_cents must be a nonnegative integer")
    for value in (customer, destination):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("customer and destination must be nonblank strings")
    identifier = max(_records, default=0) + 1
    record = dict(id=identifier, total_cents=total_cents, customer=customer.strip(),
                  destination=destination.strip(), status="confirmed", refund_cents=0)
    _records[identifier] = record
    return record.copy()


def get_delivery(delivery_id):
    _validate_id(delivery_id)
    return _records[delivery_id].copy()


def cancel_delivery(delivery_id):
    _validate_id(delivery_id)
    record = _records[delivery_id]
    if record["status"] != "cancelled":
        record["status"] = "cancelled"
        record["refund_cents"] = record["total_cents"]
    return record.copy()
'''


class ObjectionTheater(CommunicationTheater):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        root = self.theater.root
        (root / "delivery/delivery.py").write_text(BASELINE)
        (root / "delivery/TASK.md").write_text(
            "Maintain delivery creation, lookup, cancellation, validation and copied snapshots.\n"
            "Keep the customer-facing active-delivery listing behavior.\n"
            "Cancelled deliveries remain stored, with recorded refunds and individual lookup.\n"
            "The current API is existing code, not a prohibition on future internal APIs.\n"
            "Keep cancellation idempotent and preserve recorded refunds.\n"
        )
        (root / "delivery/README.md").write_text(
            "# Delivery component\n\n"
            "delivery.py contains the current working implementation.\n"
            "get_delivery_records() is the active-delivery listing.\n"
            "Other modules in this workspace are snapshots, not current peer work.\n"
        )
        p = root / "billing/TASK.md"
        p.write_text(
            p.read_text().replace(
                "revenue_report() calls delivery.get_delivery_records(); declare its "
                "expected public return shape.",
                "revenue_report() needs every saved delivery, including cancelled records. "
                "Use the owner-published boundary; clarify missing capabilities through MidFlight.",
            )
        )
        for name in ("delivery", "billing"):
            p = root / name / "AGENTS.md"
            p.write_text(
                p.read_text()
                + "\nPublish the owned interface before implementation and test changes, "
                "then continue useful work without waiting for peers. "
                "Before ending a work turn, check in after tests. "
                "Read updates returned by sends too. Address actionable technical "
                "objections and questions during the current work turn. "
                "Do not wait or poll for hypothetical updates. "
                "Only the objection author may resolve it after its problem is addressed.\n"
            )
            subprocess.run(["git", "add", "."], cwd=p.parent, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Demo",
                    "-c",
                    "user.email=demo@localhost",
                    "commit",
                    "-qm",
                    "Prepare existing active-listing baseline",
                ],
                cwd=p.parent,
                check=True,
            )
        (root / "objection-experiment.json").write_text(
            json.dumps(
                {
                    "baseline": "Working active-only delivery listing; no accounting API yet.",
                    "publisher_prompt": PUBLISH_PROMPT,
                    "work_prompts": WORK_PROMPTS,
                    "rules": "Real agents author coordination. "
                    "No idle wakes, injected objections or barriers.",
                },
                indent=2,
            )
        )

    def initial_prompt(self, name, default):
        return PUBLISH_PROMPT if name == "delivery" else WORK_PROMPTS[name]


class OverlapObjectionTheater(ObjectionTheater):
    """Two unsent tasks: the owner publishes and implements in the same turn."""

    def initial_prompt(self, name, default):
        if name == "delivery":
            return "Implement delivery management with a customer-facing list of active deliveries."
        return WORK_PROMPTS[name]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path)
    parser.add_argument("--port", type=int, default=18943)
    parser.add_argument("--db-port", type=int, default=6379)
    parser.add_argument(
        "--overlap",
        action="store_true",
        help="Prepare implementation prompts for overlapping work turns",
    )
    args = parser.parse_args()
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", args.port))
    root = args.root or Path(__file__).resolve().parents[2] / "runs" / (
        "objection-" + uuid.uuid4().hex[:10]
    )
    factory = OverlapObjectionTheater if args.overlap else ObjectionTheater
    live = factory(root, args.db_port, controller_port=args.port)
    live.launch()
    uvicorn.run(app_for(live, factory=factory), host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
