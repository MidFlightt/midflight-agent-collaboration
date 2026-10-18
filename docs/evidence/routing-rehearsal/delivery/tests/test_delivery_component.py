import unittest
from unittest.mock import patch

import delivery


class DeliveryComponent(unittest.TestCase):
    def setUp(self):
        self.store = patch.object(delivery, '_records', {})
        self.store.start()
        self.addCleanup(self.store.stop)

    def test_create_and_retrieve(self):
        first = delivery.create_delivery(1234, ' Alice ', ' Home ')
        self.assertEqual(first, dict(id=1, total_cents=1234, customer='Alice',
                                    destination='Home', status='confirmed', refund_cents=0))
        second = delivery.create_delivery(0, 'Bob', 'Office')
        self.assertEqual(second['id'], 2)
        self.assertEqual(delivery.get_delivery(1), first)

    def test_snapshots_are_independent(self):
        created = delivery.create_delivery(100, 'Alice', 'Home')
        created['total_cents'] = 999
        fetched = delivery.get_delivery(1)
        fetched['customer'] = 'changed'
        snapshot = delivery.get_delivery_records()
        snapshot[1]['destination'] = 'changed'
        snapshot.clear()
        self.assertEqual(delivery.get_delivery(1)['total_cents'], 100)
        self.assertEqual(delivery.get_delivery(1)['customer'], 'Alice')
        self.assertEqual(delivery.get_delivery(1)['destination'], 'Home')

    def test_cancel_retains_fee_and_is_idempotent(self):
        for amount, refund in ((0, 0), (1, 0), (399, 0), (400, 0), (401, 1), (1234, 834)):
            record = delivery.create_delivery(amount, 'Alice', 'Home')
            cancelled = delivery.cancel_delivery(record['id'])
            self.assertEqual(cancelled['status'], 'cancelled')
            self.assertEqual(cancelled['refund_cents'], refund)
            self.assertEqual(delivery.cancel_delivery(record['id']), cancelled)
            cancelled['refund_cents'] = -1
            self.assertEqual(delivery.get_delivery(record['id'])['refund_cents'], refund)
            self.assertEqual(record['status'], 'confirmed')

    def test_invalid_creation_leaves_store_empty(self):
        for amount in (-1, True, 1.0, '1', None):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                delivery.create_delivery(amount, 'Alice', 'Home')
        for value in ('', '  ', None, 1, False):
            for customer, destination in ((value, 'Home'), ('Alice', value)):
                with self.subTest(customer=customer, destination=destination):
                    with self.assertRaises(ValueError):
                        delivery.create_delivery(1, customer, destination)
        self.assertEqual(delivery.get_delivery_records(), {})

    def test_invalid_or_unknown_ids(self):
        delivery.create_delivery(1, 'Alice', 'Home')
        for value in (0, -1, True, 1.0, '1', None, 2):
            for action in (delivery.get_delivery, delivery.cancel_delivery):
                with self.subTest(value=value, action=action), self.assertRaises(ValueError):
                    action(value)
        self.assertEqual(delivery.get_delivery(1)['status'], 'confirmed')
