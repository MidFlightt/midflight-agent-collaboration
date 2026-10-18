import unittest
from unittest.mock import patch

import delivery


class DeliveryComponent(unittest.TestCase):
    def setUp(self):
        self.store = patch.object(delivery, "_records", {})
        self.counter = patch.object(delivery, "_next_id", 1)
        self.store.start()
        self.counter.start()
        self.addCleanup(self.store.stop)
        self.addCleanup(self.counter.stop)

    def test_create_and_retrieve(self):
        first = delivery.create_delivery(1250, "Ada", "Main Street")
        second = delivery.create_delivery(0, "Ben", "Station")
        self.assertEqual(first, {"delivery_id": 1, "total_cents": 1250,
                                "customer": "Ada", "destination": "Main Street",
                                "status": "confirmed", "refund_cents": 0})
        self.assertEqual(second["delivery_id"], 2)
        self.assertEqual(delivery.get_delivery(1), first)

    def test_cancellation_keeps_four_credits_and_is_idempotent(self):
        for amount, refund in ((0, 0), (399, 0), (400, 0), (401, 1), (1999, 1599)):
            record = delivery.create_delivery(amount, "Ada", "Main Street")
            key = record["delivery_id"]
            cancelled = delivery.cancel_delivery(key)
            self.assertEqual(cancelled["status"], "cancelled")
            self.assertEqual(cancelled["refund_cents"], refund)
            self.assertEqual(delivery.cancel_delivery(key), cancelled)
            self.assertEqual(delivery.get_delivery(key), cancelled)

    def test_snapshots_cannot_modify_store_and_remain_snapshots(self):
        self.assertEqual(delivery.get_delivery_records(), {})
        created = delivery.create_delivery(500, "Ada", "Main Street")
        snapshot = delivery.get_delivery_records()
        created["total_cents"] = 1
        delivery.get_delivery(1)["customer"] = "Changed"
        snapshot[1]["destination"] = "Changed"
        snapshot.clear()
        before_cancel = delivery.get_delivery_records()
        cancelled = delivery.cancel_delivery(1)
        cancelled["refund_cents"] = 0
        self.assertEqual(before_cancel[1]["status"], "confirmed")
        stored = delivery.get_delivery(1)
        self.assertEqual(stored["total_cents"], 500)
        self.assertEqual(stored["refund_cents"], 100)
        self.assertEqual(stored["customer"], "Ada")
        self.assertEqual(stored["destination"], "Main Street")

    def test_invalid_creation_does_not_save_records(self):
        for amount in (True, False, 1.2, "1", None, -1):
            with self.subTest(amount=amount), self.assertRaises((TypeError, ValueError)):
                delivery.create_delivery(amount, "Ada", "Main Street")
        for text in (None, 123, "", " \t\n"):
            for field in ("customer", "destination"):
                args = dict(total_cents=0, customer="Ada", destination="Main Street")
                args[field] = text
                with self.subTest(field=field, text=text), self.assertRaises((TypeError, ValueError)):
                    delivery.create_delivery(**args)
        self.assertEqual(delivery.get_delivery_records(), {})
        self.assertEqual(delivery.create_delivery(0, "Ada", "Main Street")["delivery_id"], 1)

    def test_reject_invalid_and_unknown_ids(self):
        delivery.create_delivery(1, "Ada", "Main Street")
        for operation in (delivery.get_delivery, delivery.cancel_delivery):
            for key in (True, False, 1.0, "1", None, 0, -1):
                with self.subTest(operation=operation.__name__, key=key), self.assertRaises((TypeError, ValueError)):
                    operation(key)
            with self.assertRaises(KeyError):
                operation(999)
        self.assertEqual(delivery.get_delivery(1)["status"], "confirmed")
