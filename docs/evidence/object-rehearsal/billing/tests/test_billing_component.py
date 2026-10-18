import copy
import unittest
from unittest.mock import patch

import billing


class BillingComponentTests(unittest.TestCase):
    def test_report_mixed_records_with_current_fee_and_historical_refunds(self):
        # Current policy event 14 retains up to 400 cents on new cancellations.
        # Historical refunds remain authoritative, even when they differ.
        records = {
            11: {"total_cents": 1251, "refund_cents": 0, "status": "confirmed"},
            23: {"total_cents": 0, "refund_cents": 0, "status": "confirmed"},
            37: {"total_cents": 0, "refund_cents": 0, "status": "cancelled"},
            41: {"total_cents": 1, "refund_cents": 0, "status": "cancelled"},
            59: {"total_cents": 399, "refund_cents": 0, "status": "cancelled"},
            61: {"total_cents": 400, "refund_cents": 0, "status": "cancelled"},
            73: {"total_cents": 401, "refund_cents": 1, "status": "cancelled"},
            89: {"total_cents": 1251, "refund_cents": 851, "status": "cancelled"},
            97: {"total_cents": 900, "refund_cents": 900, "status": "cancelled"},
            101: {"total_cents": 700, "refund_cents": 500, "status": "cancelled"},
        }
        original = copy.deepcopy(records)
        with patch("billing.get_delivery_records", return_value=records) as read:
            self.assertEqual(billing.revenue_report(),
                             {"revenue_cents": 3051, "confirmed": 2, "cancelled": 8})
            # Re-reading saved data must neither reprice nor mutate refunds.
            self.assertEqual(billing.revenue_report(),
                             {"revenue_cents": 3051, "confirmed": 2, "cancelled": 8})
            self.assertEqual(read.call_count, 2)
        self.assertEqual(records, original)

    def test_small_cancelled_totals_use_saved_refunds(self):
        for total, refund, revenue in (
            (0, 0, 0), (1, 0, 1), (399, 0, 399),
            (400, 0, 400), (401, 1, 400), (1251, 851, 400),
            (399, 399, 0), (401, 400, 1),
        ):
            with self.subTest(total=total, refund=refund):
                self.assertEqual(billing.summarize_records([
                    {"total_cents": total, "refund_cents": refund,
                     "status": "cancelled"}
                ]), {"revenue_cents": revenue, "confirmed": 0, "cancelled": 1})

    def test_saved_refunds_and_status_counts(self):
        records = [
            {"total_cents": 1200, "refund_cents": 0, "status": "confirmed"},
            {"total_cents": 900, "refund_cents": 900, "status": "cancelled"},
            {"total_cents": 700, "refund_cents": 500, "status": "cancelled"},
            {"total_cents": 0, "refund_cents": 0, "status": "confirmed"},
        ]
        original = copy.deepcopy(records)
        self.assertEqual(billing.summarize_records(records),
                         {"revenue_cents": 1400, "confirmed": 2, "cancelled": 2})
        self.assertEqual(records, original)

    def test_report_reads_published_mapping(self):
        with patch("billing.get_delivery_records", return_value={
            42: {"total_cents": 850, "refund_cents": 50, "status": "cancelled"}
        }) as read:
            self.assertEqual(billing.revenue_report(),
                             {"revenue_cents": 800, "confirmed": 0, "cancelled": 1})
            read.assert_called_once_with()

    def test_empty_report(self):
        with patch("billing.get_delivery_records", return_value={}):
            self.assertEqual(billing.revenue_report(),
                             {"revenue_cents": 0, "confirmed": 0, "cancelled": 0})

    def test_invalid_records(self):
        valid = {"total_cents": 100, "refund_cents": 0, "status": "confirmed"}
        for field in ("total_cents", "refund_cents"):
            for value in (True, -1, 1.5, "100", None):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        billing.summarize_records([{**valid, field: value}])
        for record in ({}, None, {**valid, "status": "pending"}):
            with self.subTest(record=record):
                with self.assertRaises(ValueError):
                    billing.summarize_records([record])
