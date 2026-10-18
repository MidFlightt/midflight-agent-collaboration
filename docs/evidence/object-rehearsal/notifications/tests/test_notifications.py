import unittest

from notifications import confirmation


class ConfirmationTests(unittest.TestCase):
    def test_confirmation_message(self):
        self.assertEqual(
            confirmation("customer+order@example.co.uk", 42),
            "Delivery #42 is confirmed for customer+order@example.co.uk.",
        )

    def test_invalid_emails(self):
        for email in (None, 12, "", "person", "@example.com", "a@@example.com",
                      "a@example", "a@.com", "a@example.", "a@example..com",
                      " a@example.com", "a b@example.com", "a@example.com\n",
                      "a\x00@example.com", "a\x7f@example.com"):
            with self.subTest(email=email), self.assertRaises(ValueError):
                confirmation(email, 1)

    def test_invalid_delivery_ids(self):
        for delivery_id in (None, True, False, 0, -1, 1.0, "1", [], {}):
            with self.subTest(delivery_id=delivery_id), self.assertRaises(ValueError):
                confirmation("a@example.com", delivery_id)

    def test_message_does_not_include_financial_language(self):
        message = confirmation("a@example.com", 1).lower()
        for word in ("refund", "fee", "cents", "$", "credit"):
            self.assertNotIn(word, message)
