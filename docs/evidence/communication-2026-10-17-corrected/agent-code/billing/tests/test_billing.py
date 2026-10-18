import copy
import unittest
from unittest.mock import patch

import billing


class BillingTests(unittest.TestCase):
    def test_empty_records(self):
        self.assertEqual(billing.summarize_records([]),
                         {"revenue_cents": 0, "confirmed": 0, "cancelled": 0})

    def test_saved_amounts_and_counts_without_mutation(self):
        records = [
            {"total_cents": 1200, "refund_cents": 0, "status": "confirmed", "id": 1},
            {"total_cents": 700, "refund_cents": 700, "status": "cancelled"},
            {"total_cents": 900, "refund_cents": 200, "status": "cancelled"},
            {"total_cents": 100, "refund_cents": 25, "status": "confirmed"},
            {"total_cents": 0, "refund_cents": 0, "status": "confirmed"},
        ]
        before = copy.deepcopy(records)
        self.assertEqual(billing.summarize_records(records),
                         {"revenue_cents": 1975, "confirmed": 3, "cancelled": 2})
        self.assertEqual(records, before)

    def test_report_reads_delivery_records(self):
        with patch("billing.get_delivery_records", return_value=[
            {"total_cents": 1000, "refund_cents": 1000, "status": "cancelled"}
        ]) as get_records:
            self.assertEqual(billing.revenue_report(),
                             {"revenue_cents": 0, "confirmed": 0, "cancelled": 1})
            get_records.assert_called_once_with()

    def test_saved_cancellation_fee_policy(self):
        # Saved refunds supplied by Delivery under policy 17, revision 2.
        cases = [(0, 0, 0), (100, 0, 100), (399, 0, 399),
                 (400, 0, 400), (401, 1, 400), (1250, 850, 400)]
        for total, refund, revenue in cases:
            with self.subTest(total_cents=total):
                with patch("billing.get_delivery_records", return_value=[
                    {"total_cents": total, "refund_cents": refund,
                     "status": "cancelled"}
                ]):
                    self.assertEqual(billing.revenue_report(),
                                     {"revenue_cents": revenue,
                                      "confirmed": 0, "cancelled": 1})

    def test_report_empty_real_store(self):
        self.assertEqual(billing.revenue_report(),
                         {"revenue_cents": 0, "confirmed": 0, "cancelled": 0})

    def test_invalid_container_or_record(self):
        for records in (None, {}, (), [None], [[]]):
            with self.subTest(records=records), self.assertRaises(TypeError):
                billing.summarize_records(records)

    def test_missing_fields(self):
        for field in ("total_cents", "refund_cents", "status"):
            record = {"total_cents": 100, "refund_cents": 0, "status": "confirmed"}
            del record[field]
            with self.subTest(field=field), self.assertRaises(KeyError):
                billing.summarize_records([record])

    def test_invalid_amounts(self):
        for field in ("total_cents", "refund_cents"):
            for value in (True, False, 1.5, "100", None, -1):
                record = {"total_cents": 100, "refund_cents": 0, "status": "confirmed"}
                record[field] = value
                error = ValueError if value == -1 else TypeError
                with self.subTest(field=field, value=value), self.assertRaises(error):
                    billing.summarize_records([record])

    def test_excess_refund_and_invalid_status(self):
        with self.assertRaises(ValueError):
            billing.summarize_records([{"total_cents": 1, "refund_cents": 2,
                                        "status": "cancelled"}])
        for status in ("pending", None, [], 1):
            with self.subTest(status=status), self.assertRaises(ValueError):
                billing.summarize_records([{"total_cents": 1, "refund_cents": 0,
                                            "status": status}])
