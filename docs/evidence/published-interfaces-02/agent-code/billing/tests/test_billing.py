import copy
import unittest
from unittest.mock import patch

from billing import revenue_report, summarize_records


def record(total=1000, refund=0, status="confirmed"):
    return {"total_cents": total, "refund_cents": refund, "status": status}


class BillingTests(unittest.TestCase):
    def test_empty_inputs(self):
        for records in ({}, []):
            self.assertEqual(summarize_records(records),
                             {"revenue_cents": 0, "confirmed": 0, "cancelled": 0})

    def test_saved_refunds_and_counts(self):
        records = {1: record(), 2: record(1500, 1500, "cancelled"),
                   3: record(1200, 800, "cancelled"), 4: record(0)}
        original = copy.deepcopy(records)
        self.assertEqual(summarize_records(records),
                         {"revenue_cents": 1400, "confirmed": 2, "cancelled": 2})
        self.assertEqual(records, original)
        self.assertEqual(summarize_records(list(records.values())),
                         summarize_records(records))

    def test_entry_point_consumes_published_mapping(self):
        with patch("billing.get_delivery_records", return_value={7: record(900, 300, "cancelled")}) as fetch:
            self.assertEqual(revenue_report(),
                             {"revenue_cents": 600, "confirmed": 0, "cancelled": 1})
            fetch.assert_called_once_with()

    def test_invalid_container_and_records(self):
        for records in (None, (), "records", [None], {True: record()}, {"1": record()}):
            with self.subTest(records=records), self.assertRaises(TypeError):
                summarize_records(records)
        for key in (0, -1):
            with self.assertRaises(ValueError):
                summarize_records({key: record()})

    def test_invalid_fields(self):
        for field in ("total_cents", "refund_cents", "status"):
            missing = record()
            del missing[field]
            with self.subTest(field=field), self.assertRaises(KeyError):
                summarize_records([missing])
        for field in ("total_cents", "refund_cents"):
            for value in (True, 1.5, "100", None):
                invalid = record()
                invalid[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(TypeError):
                    summarize_records([invalid])
            invalid = record()
            invalid[field] = -1
            with self.assertRaises(ValueError):
                summarize_records([invalid])
        with self.assertRaises(TypeError):
            summarize_records([record(status=None)])
        with self.assertRaises(ValueError):
            summarize_records([record(status="pending")])


if __name__ == "__main__":
    unittest.main()
