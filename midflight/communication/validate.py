"""Combine the four agents' owned modules and run real code, without rewriting it."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

NAMES = ("billing", "delivery", "booking", "notifications")
INTEGRATION = """import unittest
import billing, delivery, booking, notifications

class CombinedCode(unittest.TestCase):
    def test_real_workflow(self):
        self.assertEqual(billing.revenue_report(),
                         {'revenue_cents':0,'confirmed':0,'cancelled':0})
        payload=booking.booking_request(1200,'A','North')
        first=delivery.create_delivery(**payload)
        second=delivery.create_delivery(1000,'B','South')
        low=delivery.create_delivery(200,'C','West')
        zero=delivery.create_delivery(0,'D','East')
        self.assertEqual(len({r[ID_FIELD] for r in [first,second,low,zero]}),4)
        self.assertEqual(delivery.get_delivery(first[ID_FIELD])['status'],'confirmed')
        cancelled=delivery.cancel_delivery(second[ID_FIELD])
        self.assertEqual(cancelled['refund_cents'],max(1000-FEE,0))
        self.assertEqual(delivery.cancel_delivery(second[ID_FIELD]),cancelled)
        self.assertEqual(delivery.cancel_delivery(low[ID_FIELD])['refund_cents'],max(200-FEE,0))
        self.assertEqual(delivery.cancel_delivery(zero[ID_FIELD])['refund_cents'],0)
        self.assertEqual(billing.revenue_report(),{'revenue_cents':1200+min(FEE,1000)+min(FEE,200),
                                                  'confirmed':1,'cancelled':3})
        snapshot=delivery.get_delivery_records()
        records=list(snapshot.values()) if isinstance(snapshot,dict) else snapshot
        records[0]['total_cents']=99999
        self.assertEqual(delivery.get_delivery(first[ID_FIELD])['total_cents'],1200)
        message=notifications.confirmation('a@example.com',first[ID_FIELD])
        self.assertIsInstance(message,str)
        self.assertIn(str(first[ID_FIELD]),message)
        self.assertIsInstance(booking.page(),str)
        with self.assertRaises((KeyError,ValueError)):
            delivery.cancel_delivery(999999)

if __name__=='__main__': unittest.main()
"""


def validate(root, fee=0, label="baseline", id_field="delivery_id"):
    if id_field not in {"id", "delivery_id"}:
        raise ValueError("Use the ID field from the published interface")
    root = Path(root).resolve()
    destination = root / "validation" / label
    destination.mkdir(parents=True, exist_ok=False)
    hashes = {}
    components = {}
    for name in NAMES:
        source = root / name / (name + ".py")
        hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest()
        shutil.copy2(source, destination / source.name)
        test = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=root / name,
            text=True,
            capture_output=True,
        )
        components[name] = dict(returncode=test.returncode, output=test.stdout + test.stderr)
    (destination / "test_combined.py").write_text(
        f"FEE={fee}\nID_FIELD={id_field!r}\n" + INTEGRATION
    )
    started = time.monotonic()
    result = subprocess.run(
        [sys.executable, "test_combined.py", "-v"], cwd=destination, text=True, capture_output=True
    )
    evidence = dict(
        label=label,
        executed_by="operator",
        executed_at=datetime.now(UTC).isoformat(),
        method="Four owned modules copied unchanged; fresh subprocess imports actual combined code",
        component_scope="Agent-local tests may mock peers; these are not integration evidence",
        policy_consumption="Inspect exact agent policy reports separately; not measured by tests",
        success=result.returncode == 0 and all(c["returncode"] == 0 for c in components.values()),
        fee_cents=fee,
        id_field=id_field,
        hashes=hashes,
        components=components,
        combined=dict(
            returncode=result.returncode,
            output=result.stdout + result.stderr,
            seconds=time.monotonic() - started,
        ),
    )
    (destination / "result.json").write_text(json.dumps(evidence, indent=2))
    (root / "integration.json").write_text(json.dumps(evidence, indent=2))
    return evidence


def evidence_status(root, evidence):
    """Saved success applies only to the exact tested module bytes."""
    root = Path(root)
    current = {n: hashlib.sha256((root / n / (n + ".py")).read_bytes()).hexdigest() for n in NAMES}
    return evidence | {
        "matches_current_modules": current == evidence["hashes"],
        "current_hashes": current,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--fee", type=int, default=0)
    parser.add_argument("--label", default="baseline")
    parser.add_argument("--id-field", choices=["id", "delivery_id"], default="delivery_id")
    args = parser.parse_args()
    result = validate(args.root, args.fee, args.label, args.id_field)
    print(json.dumps(result, indent=2))
    failed = result["combined"]["returncode"] != 0 or any(
        component["returncode"] != 0 for component in result["components"].values()
    )
    raise SystemExit(int(failed))


if __name__ == "__main__":
    main()
