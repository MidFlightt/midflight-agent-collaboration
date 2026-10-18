import unittest

from app import dispatch
from notifications import confirmation


class NotificationsTests(unittest.TestCase):
    def test_confirmation_and_route(self):
        payload = {"email": "customer+orders@example.co.uk", "delivery_id": 42}
        expected = "Delivery 42 is confirmed. Confirmation for customer+orders@example.co.uk."
        self.assertEqual(confirmation(**payload), expected)
        self.assertEqual(dispatch("/notify", payload), {"message": expected})

    def test_invalid_email(self):
        for email in (None, 12, "", "a", "@example.com", "a@@example.com",
                      "a@example", "a@.com", "a@example..com", "a@-example.com",
                      "a@example-.com", "a b@example.com", "a@example.com\n",
                      "a\r\nBcc:x@example.com", ".a@example.com", "a.@example.com",
                      "a..b@example.com", "é@example.com", "a" * 65 + "@example.com"):
            with self.subTest(email=email), self.assertRaises(ValueError):
                confirmation(email, 1)

    def test_invalid_delivery_id(self):
        for delivery_id in (None, True, False, 0, -1, 1.0, "1", [], {}):
            with self.subTest(delivery_id=delivery_id), self.assertRaises(ValueError):
                confirmation("customer@example.com", delivery_id)

    def test_message_has_no_monetary_policy(self):
        message = confirmation("customer@example.com", 7).lower()
        for term in ("refund", "cents", "credit", "$", "revenue"):
            self.assertNotIn(term, message)
