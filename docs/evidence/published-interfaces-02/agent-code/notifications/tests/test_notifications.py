"""Component coverage for local customer confirmation messages."""

import unittest

from app import dispatch
from notifications import confirmation


class ConfirmationTests(unittest.TestCase):
    def test_confirmation_preserves_address_and_identifies_delivery(self):
        self.assertEqual(
            confirmation("Alice+orders@Example.co.uk", 42),
            "Delivery 42 confirmed for Alice+orders@Example.co.uk.",
        )

    def test_invalid_addresses(self):
        for email in (None, 12, True, [], {}, "", "alice", "@example.com",
                      "alice@", "alice@example", "alice@@example.com",
                      "alice@.com", "alice@example.", "alice@example..com",
                      " alice@example.com", "alice@example.com ",
                      "alice\n@example.com", "alice@exam\tple.com"):
            with self.subTest(email=email), self.assertRaises(ValueError):
                confirmation(email, 1)

    def test_invalid_delivery_ids(self):
        for delivery_id in (None, True, False, 0, -1, 1.0, "1", [], {}):
            with self.subTest(delivery_id=delivery_id), self.assertRaises(ValueError):
                confirmation("alice@example.com", delivery_id)

    def test_notify_route_returns_local_message(self):
        self.assertEqual(
            dispatch("/notify", {"email": "alice@example.com", "delivery_id": 7}),
            {"message": "Delivery 7 confirmed for alice@example.com."},
        )

    def test_notify_route_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            dispatch("/notify", {"email": "alice@example.com", "delivery_id": False})
