"""Component tests for local confirmation generation."""

import unittest

from notifications import confirmation


class ConfirmationTests(unittest.TestCase):
    def test_confirmation_preserves_recipient_and_id(self):
        self.assertEqual(
            confirmation("Customer+order@Sub.Example.com", 42),
            "Delivery 42 confirmed for Customer+order@Sub.Example.com.",
        )

    def test_email_types(self):
        for email in (None, 12, True, b"user@example.com", []):
            with self.subTest(email=email), self.assertRaises(TypeError):
                confirmation(email, 1)

    def test_invalid_addresses(self):
        addresses = (
            "", "user", "@example.com", "user@", "user@@example.com",
            "user@example", " user@example.com", "user@example.com ",
            "user\n@example.com", "user@example.com\r\nBcc:other@example.com",
            "first..last@example.com", ".user@example.com", "user.@example.com",
            "user@.example.com", "user@example..com", "user@example.com.",
            "user@-example.com", "user@example-.com", "user@exam_ple.com",
            "üser@example.com", "user@exämple.com", '"user"@example.com',
            "Name <user@example.com>", "x" * 65 + "@example.com",
            "user@" + "x" * 64 + ".com",
            "x" * 64 + "@" + ".".join(["y" * 63] * 3),
        )
        for email in addresses:
            with self.subTest(email=email), self.assertRaises(ValueError):
                confirmation(email, 1)

    def test_valid_address_length_limits(self):
        email = "x" * 64 + "@" + ".".join(["y" * 63, "z" * 63, "w" * 61])
        self.assertEqual(len(email), 254)
        self.assertIn(email, confirmation(email, 1))

    def test_delivery_id_types(self):
        for delivery_id in (None, True, False, "1", 1.0, []):
            with self.subTest(delivery_id=delivery_id), self.assertRaises(TypeError):
                confirmation("user@example.com", delivery_id)

    def test_delivery_id_must_be_positive(self):
        for delivery_id in (0, -1, -100):
            with self.subTest(delivery_id=delivery_id), self.assertRaises(ValueError):
                confirmation("user@example.com", delivery_id)

    def test_no_money_or_refund_content(self):
        message = confirmation("user@example.com", 7)
        for term in ("refund", "cents", "$", "fee"):
            self.assertNotIn(term, message.lower())


if __name__ == "__main__":
    unittest.main()
