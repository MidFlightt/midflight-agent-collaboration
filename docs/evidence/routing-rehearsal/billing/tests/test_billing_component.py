"""Isolated billing tests; delivery snapshots are mocked at the boundary."""
import copy
import unittest
from unittest.mock import patch

import billing


def record(identifier=1, total=1000, refund=0, status="confirmed"):
    return {"id": identifier, "total_cents": total, "refund_cents": refund,
            "status": status, "customer": "Ada", "destination": "Office"}


class BillingComponentTests(unittest.TestCase):
    def test_empty_collections(self):
        for records in ({}, []):
            self.assertEqual(billing.summarize_records(records),
                             {"revenue_cents": 0, "confirmed": 0, "cancelled": 0})

    def test_actual_saved_refunds_and_counts_without_mutation(self):
        records = {1: record(), 2: record(2, 2000, 2000, "cancelled"),
                   3: record(3, 1500, 1250, "cancelled"),
                   4: record(4, 800, 100)}
        before = copy.deepcopy(records)
        expected = {"revenue_cents": 1950, "confirmed": 2, "cancelled": 2}
        self.assertEqual(billing.summarize_records(records), expected)
        self.assertEqual(billing.summarize_records(list(records.values())), expected)
        self.assertEqual(records, before)

    def test_revenue_report_reads_published_dictionary_boundary(self):
        with patch("billing.get_delivery_records", return_value={7: record(7, 900, 900, "cancelled")}) as read:
            self.assertEqual(billing.revenue_report(),
                             {"revenue_cents": 0, "confirmed": 0, "cancelled": 1})
            read.assert_called_once_with()

    def test_mixed_report_with_current_fee_and_previously_saved_refunds(self):
        # Policy event 9 retains up to 400 cents on new cancellations.
        # Historical refunds remain authoritative even if policy has changed.
        records = {
            10: record(10, 1200),
            20: record(20, 0),
            30: record(30, 1234, 834, "cancelled"),
            40: record(40, 99, 0, "cancelled"),
            50: record(50, 900, 900, "cancelled"),
            60: record(60, 1500, 1250, "cancelled"),
        }
        before = copy.deepcopy(records)
        expected = {"revenue_cents": 1949, "confirmed": 2, "cancelled": 4}
        with patch("billing.get_delivery_records", return_value=records) as read:
            self.assertEqual(billing.revenue_report(), expected)
            self.assertEqual(billing.revenue_report(), expected)
            self.assertEqual(read.call_count, 2)
        self.assertEqual(billing.summarize_records(records), expected)
        self.assertEqual(records, before)

    def test_small_cancelled_totals_in_mixed_reports(self):
        # Explicit saved refunds exercise zero, below, at, and above the fee.
        cases = [(0, 0, 0), (1, 0, 1), (399, 0, 399),
                 (400, 0, 400), (401, 1, 400)]
        for total, saved_refund, retained in cases:
            with self.subTest(total=total):
                records = {3: record(3, 17),
                           8: record(8, total, saved_refund, "cancelled")}
                with patch("billing.get_delivery_records", return_value=records):
                    self.assertEqual(billing.revenue_report(), {
                        "revenue_cents": 17 + retained,
                        "confirmed": 1, "cancelled": 1,
                    })

    def test_revenue_report_empty_saved_snapshot(self):
        with patch("billing.get_delivery_records", return_value={}) as read:
            self.assertEqual(billing.revenue_report(), {
                "revenue_cents": 0, "confirmed": 0, "cancelled": 0,
            })
            read.assert_called_once_with()

    def test_reject_invalid_records(self):
        cases = [None, "records", (), [None], [{}], {True: record()},
                 {0: record(0)}, {2: record(1)}, {1: record(True)}]
        for field in ("total_cents", "refund_cents"):
            for invalid in (True, -1, 1.5, "100", None):
                item = record()
                item[field] = invalid
                cases.append([item])
        for invalid in (None, "pending", [], {}):
            item = record()
            item["status"] = invalid
            cases.append([item])
        for records in cases:
            with self.subTest(records=records), self.assertRaises(ValueError):
                billing.summarize_records(records)

    def test_refund_is_not_recomputed_or_clamped(self):
        self.assertEqual(billing.summarize_records([record(refund=1200)]),
                         {"revenue_cents": -200, "confirmed": 1, "cancelled": 0})
