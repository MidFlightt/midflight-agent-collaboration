import unittest
from unittest.mock import patch

import billing


class BillingTests(unittest.TestCase):
    def test_empty_report(self):
        with patch.object(billing, "get_delivery_records", return_value={}) as get_records:
            self.assertEqual(billing.revenue_report(), {
                "revenue_cents": 0, "confirmed": 0, "cancelled": 0,
            })
        get_records.assert_called_once_with()

    def test_saved_refunds_determine_revenue(self):
        records = [
            {"total_cents": 1501, "refund_cents": 0, "status": "confirmed"},
            {"total_cents": 1000, "refund_cents": 1000, "status": "cancelled"},
            {"total_cents": 999, "refund_cents": 250, "status": "cancelled"},
        ]
        original = [record.copy() for record in records]
        self.assertEqual(billing.summarize_records(records), {
            "revenue_cents": 2250, "confirmed": 1, "cancelled": 2,
        })
        self.assertEqual(records, original)

    def test_report_uses_current_saved_records(self):
        records = {7: {"total_cents": 123, "refund_cents": 123, "status": "cancelled"}}
        with patch.object(billing, "get_delivery_records", return_value=records) as get_records:
            self.assertEqual(billing.revenue_report(), {
                "revenue_cents": 0, "confirmed": 0, "cancelled": 1,
            })
        get_records.assert_called_once_with()

    def test_cancellation_fee_uses_saved_refunds_at_threshold(self):
        for total, refund, revenue in [
            (0, 0, 0), (399, 0, 399), (400, 0, 400),
            (401, 1, 400), (1000, 600, 400),
        ]:
            with self.subTest(total=total):
                records = {1: {
                    "total_cents": total, "refund_cents": refund,
                    "status": "cancelled",
                }}
                with patch.object(billing, "get_delivery_records", return_value=records):
                    self.assertEqual(billing.revenue_report(), {
                        "revenue_cents": revenue, "confirmed": 0, "cancelled": 1,
                    })

    def test_historical_refunds_are_not_recalculated(self):
        records = {
            1: {"total_cents": 1000, "refund_cents": 1000, "status": "cancelled"},
            2: {"total_cents": 1000, "refund_cents": 600, "status": "cancelled"},
            3: {"total_cents": 1000, "refund_cents": 250, "status": "cancelled"},
            4: {"total_cents": 501, "refund_cents": 0, "status": "confirmed"},
        }
        original = {key: record.copy() for key, record in records.items()}
        with patch.object(billing, "get_delivery_records", return_value=records):
            self.assertEqual(billing.revenue_report(), {
                "revenue_cents": 1651, "confirmed": 1, "cancelled": 3,
            })
        self.assertEqual(records, original)
