FEE=400
ID_FIELD='id'
import unittest
import billing, delivery, booking, notifications

class CombinedCode(unittest.TestCase):
    def test_real_workflow(self):
        self.assertEqual(billing.revenue_report(),
                         {'revenue_cents':0,'confirmed':0,'cancelled':0})
        payload=booking.booking_request(1200,'A','North')
        first=delivery.create_delivery(**payload)
        second=delivery.create_delivery(1000,'B','South')
        low=delivery.create_delivery(200,'C','West')
        zero=delivery.create_delivery(0,'D','East')
        self.assertEqual(len({r[ID_FIELD] for r in [first,second,low,zero]}),4)
        self.assertEqual(delivery.get_delivery(first[ID_FIELD])['status'],'confirmed')
        cancelled=delivery.cancel_delivery(second[ID_FIELD])
        self.assertEqual(cancelled['refund_cents'],max(1000-FEE,0))
        self.assertEqual(delivery.cancel_delivery(second[ID_FIELD]),cancelled)
        self.assertEqual(delivery.cancel_delivery(low[ID_FIELD])['refund_cents'],max(200-FEE,0))
        self.assertEqual(delivery.cancel_delivery(zero[ID_FIELD])['refund_cents'],0)
        self.assertEqual(billing.revenue_report(),{'revenue_cents':1200+min(FEE,1000)+min(FEE,200),
                                                  'confirmed':1,'cancelled':3})
        snapshot=delivery.get_delivery_records()
        records=list(snapshot.values()) if isinstance(snapshot,dict) else snapshot
        records[0]['total_cents']=99999
        self.assertEqual(delivery.get_delivery(first[ID_FIELD])['total_cents'],1200)
        message=notifications.confirmation('a@example.com',first[ID_FIELD])
        self.assertIsInstance(message,str)
        self.assertIn(str(first[ID_FIELD]),message)
        self.assertIsInstance(booking.page(),str)
        with self.assertRaises((KeyError,ValueError)):
            delivery.cancel_delivery(999999)

if __name__=='__main__': unittest.main()
