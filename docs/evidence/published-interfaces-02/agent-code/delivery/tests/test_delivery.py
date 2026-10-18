import unittest
from unittest.mock import patch

import delivery


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.store = patch.object(delivery, "_records", {})
        self.store.start()
        self.addCleanup(self.store.stop)

    def test_create_and_retrieve_unique_records(self):
        first = delivery.create_delivery(1234, "Ada", "Main Street")
        second = delivery.create_delivery(0, "Ben", "Station")
        self.assertEqual(first, {"id": 1, "total_cents": 1234,
                               "customer": "Ada", "destination": "Main Street",
                               "status": "confirmed", "refund_cents": 0})
        self.assertEqual(second["id"], 2)
        self.assertEqual(delivery.get_delivery(1), first)

    def test_all_public_results_are_independent_snapshots(self):
        created = delivery.create_delivery(500, "Ada", "Station")
        created["total_cents"] = 999
        fetched = delivery.get_delivery(1)
        fetched["customer"] = "Other"
        snapshot = delivery.get_delivery_records()
        snapshot[1]["status"] = "cancelled"
        snapshot.clear()
        cancelled = delivery.cancel_delivery(1)
        cancelled["refund_cents"] = 0
        self.assertEqual(delivery.get_delivery(1)["refund_cents"], 100)
        self.assertEqual(delivery.get_delivery(1)["customer"], "Ada")
        self.assertEqual(fetched["status"], "confirmed")

    def test_cancel_keeps_four_credits_and_is_idempotent(self):
        for amount, refund in ((0, 0), (100, 0), (399, 0), (400, 0), (401, 1), (1251, 851)):
            record = delivery.create_delivery(amount, "Ada", "Station")
            cancelled = delivery.cancel_delivery(record["id"])
            self.assertEqual(cancelled["status"], "cancelled")
            self.assertEqual(cancelled["refund_cents"], refund)
            self.assertEqual(delivery.cancel_delivery(record["id"]), cancelled)

    def test_repeat_cancellation_preserves_previously_saved_refund(self):
        record = delivery.create_delivery(1251, "Ada", "Station")
        delivery._records[record["id"]].update(status="cancelled", refund_cents=1251)
        self.assertEqual(delivery.cancel_delivery(record["id"])["refund_cents"], 1251)

    def test_invalid_creation_does_not_save_records(self):
        for amount in (True, 1.0, "1", None, -1):
            with self.subTest(amount=amount), self.assertRaises((TypeError, ValueError)):
                delivery.create_delivery(amount, "Ada", "Station")
        for field in ("customer", "destination"):
            for value in (None, 5, "", " \t\n"):
                args = dict(total_cents=1, customer="Ada", destination="Station")
                args[field] = value
                with self.subTest(field=field, value=value), self.assertRaises((TypeError, ValueError)):
                    delivery.create_delivery(**args)
        self.assertEqual(delivery.get_delivery_records(), {})

    def test_invalid_and_unknown_ids(self):
        delivery.create_delivery(1, "Ada", "Station")
        for operation in (delivery.get_delivery, delivery.cancel_delivery):
            for value in (True, 1.0, "1", None, 0, -1):
                with self.subTest(operation=operation, value=value), self.assertRaises((TypeError, ValueError)):
                    operation(value)
            with self.assertRaises(KeyError):
                operation(2)
