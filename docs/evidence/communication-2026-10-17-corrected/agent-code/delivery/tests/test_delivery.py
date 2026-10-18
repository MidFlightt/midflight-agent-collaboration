import unittest
from unittest.mock import patch

import delivery


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.store = patch.object(delivery, "_records", {})
        self.store.start()
        self.addCleanup(self.store.stop)

    def test_create_and_retrieve_isolated_snapshots(self):
        self.assertEqual(delivery.get_delivery_records(), [])
        first = delivery.create_delivery(100, " Ada ", " Home ")
        second = delivery.create_delivery(0, "Ben", "Office")
        self.assertGreater(first["delivery_id"], 0)
        self.assertGreater(second["delivery_id"], first["delivery_id"])
        self.assertEqual(first, dict(delivery_id=1, total_cents=100,
                                    customer="Ada", destination="Home",
                                    status="confirmed", refund_cents=0))
        first["total_cents"] = 900
        fetched = delivery.get_delivery(1)
        fetched["customer"] = "Other"
        snapshots = delivery.get_delivery_records()
        snapshots[0]["status"] = "cancelled"
        snapshots.clear()
        self.assertEqual(delivery.get_delivery(1)["total_cents"], 100)
        self.assertEqual(delivery.get_delivery(1)["customer"], "Ada")
        self.assertEqual(delivery.get_delivery(1)["status"], "confirmed")
        self.assertEqual(len(delivery.get_delivery_records()), 2)

    def test_cancellation_retains_fee_and_is_idempotent(self):
        for total, refund in ((0, 0), (100, 0), (399, 0), (400, 0), (401, 1), (1250, 850)):
            created = delivery.create_delivery(total, "Ada", "Home")
            cancelled = delivery.cancel_delivery(created["delivery_id"])
            self.assertEqual(cancelled["status"], "cancelled")
            self.assertEqual(cancelled["refund_cents"], refund)
            self.assertEqual(delivery.cancel_delivery(created["delivery_id"]), cancelled)
            cancelled["refund_cents"] = -1
            self.assertEqual(delivery.get_delivery(created["delivery_id"])["refund_cents"], refund)

    def test_invalid_creation_leaves_store_unchanged(self):
        for amount in (True, False, -1, 1.0, "1", None):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                delivery.create_delivery(amount, "Ada", "Home")
        for field in ("customer", "destination"):
            for value in (None, 123, "", " \t "):
                args = dict(total_cents=0, customer="Ada", destination="Home")
                args[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    delivery.create_delivery(**args)
        self.assertEqual(delivery.get_delivery_records(), [])

    def test_invalid_and_unknown_ids(self):
        delivery.create_delivery(100, "Ada", "Home")
        for operation in (delivery.get_delivery, delivery.cancel_delivery):
            for value in (True, False, 0, -1, 1.0, "1", None):
                with self.subTest(operation=operation, value=value), self.assertRaises(ValueError):
                    operation(value)
            with self.assertRaises(KeyError):
                operation(99)
        self.assertEqual(delivery.get_delivery(1)["status"], "confirmed")
