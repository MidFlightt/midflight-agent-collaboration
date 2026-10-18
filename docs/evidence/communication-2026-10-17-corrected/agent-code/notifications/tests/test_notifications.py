import unittest

from app import dispatch
from notifications import confirmation


class NotificationsTests(unittest.TestCase):
    def test_confirmation_preserves_recipient_and_id(self):
        self.assertEqual(
            confirmation("Customer+orders@example.co.uk", 42),
            "Delivery 42 confirmed for Customer+orders@example.co.uk.",
        )

    def test_invalid_email(self):
        for email in (None, 123, "", "customer", "@example.com", "a@", "a@@example.com",
                      "a@example", "a@.com", "a@example..com", ".a@example.com",
                      "a..b@example.com", "a@-example.com", "a@example-.com",
                      " a@example.com", "a@example.com ", "a b@example.com",
                      "a@example.com\n", "a@example.com\r\nBcc:x@example.com"):
            with self.subTest(email=email), self.assertRaises(ValueError):
                confirmation(email, 1)

    def test_invalid_delivery_id(self):
        for delivery_id in (None, True, False, 0, -1, 1.0, "1", [], {}):
            with self.subTest(delivery_id=delivery_id), self.assertRaises(ValueError):
                confirmation("customer@example.com", delivery_id)

    def test_notify_route(self):
        self.assertEqual(
            dispatch("/notify", {"email": "a@example.com", "delivery_id": 7}),
            {"message": "Delivery 7 confirmed for a@example.com."},
        )

    def test_notify_route_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            dispatch("/notify", {"email": "a@example.com", "delivery_id": True})
