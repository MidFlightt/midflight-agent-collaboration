import unittest
from unittest.mock import patch

import delivery


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        store = patch.object(delivery, "_records", {})
        store.start()
        self.addCleanup(store.stop)

    def test_create_and_get(self):
        first = delivery.create_delivery(1250, " Ada ", " Main St ")
        second = delivery.create_delivery(0, "Bob", "Market St")
        self.assertEqual(first, dict(id=1, total_cents=1250, customer="Ada",
                                     destination="Main St", status="confirmed",
                                     refund_cents=0))
        self.assertEqual(second["id"], 2)
        self.assertEqual(delivery.get_delivery(1), first)

    def test_cancellation_keeps_four_credits_and_is_idempotent(self):
        for amount, refund in ((0, 0), (399, 0), (400, 0), (401, 1), (1251, 851)):
            record = delivery.create_delivery(amount, "Ada", "Main St")
            cancelled = delivery.cancel_delivery(record["id"])
            self.assertEqual(cancelled["status"], "cancelled")
            self.assertEqual(cancelled["refund_cents"], refund)
            self.assertEqual(delivery.cancel_delivery(record["id"]), cancelled)
            self.assertEqual(record["status"], "confirmed")

    def test_return_values_are_isolated_snapshots(self):
        created = delivery.create_delivery(100, "Ada", "Main St")
        created["total_cents"] = 999
        fetched = delivery.get_delivery(1)
        fetched["customer"] = "Changed"
        snapshots = delivery.get_delivery_records()
        snapshots[1]["refund_cents"] = 500
        snapshots.clear()
        cancelled = delivery.cancel_delivery(1)
        cancelled["refund_cents"] = 999
        self.assertEqual(delivery.get_delivery(1)["refund_cents"], 0)
        self.assertEqual(delivery.get_delivery(1)["customer"], "Ada")
        self.assertEqual(fetched["status"], "confirmed")

    def test_invalid_input_does_not_create_records(self):
        for amount in (-1, True, False, 1.0, "100", None):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                delivery.create_delivery(amount, "Ada", "Main St")
        for field in ("customer", "destination"):
            for value in ("", " \t", None, 42, []):
                args = dict(total_cents=1, customer="Ada", destination="Main St")
                args[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    delivery.create_delivery(**args)
        self.assertEqual(delivery.get_delivery_records(), {})

    def test_invalid_and_unknown_ids(self):
        delivery.create_delivery(1, "Ada", "Main St")
        for operation in (delivery.get_delivery, delivery.cancel_delivery):
            for value in (0, -1, True, False, 1.0, "1", None):
                with self.subTest(operation=operation, value=value), self.assertRaises(ValueError):
                    operation(value)
            with self.assertRaises(KeyError):
                operation(999)
        self.assertEqual(delivery.get_delivery(1)["status"], "confirmed")
