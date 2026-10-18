import unittest
from billing import summarize_records


class Baseline(unittest.TestCase):
    def test_no_revenue(self):
        self.assertEqual(summarize_records([]), {"revenue_cents":0,"confirmed":0,"cancelled":0})
