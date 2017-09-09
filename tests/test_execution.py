import queue

from unittest import TestCase
from execution import SimulatedExecutionHandler

from event import OrderEvent


class ExecutionTestCase(TestCase):
    def test_execution(self):
        events_queue = queue.Queue(100)
        oe = OrderEvent(
            'BTC_ETC',
            'LONG',
            1.0,
            'BUY'
        )
        e = SimulatedExecutionHandler(events_queue)
        e.execute_order(oe)
        ee = events_queue.get(False)
        self.assertEqual(ee.type, 'FILL')
        self.assertEqual(ee.direction, 'BUY')
        self.assertEqual(ee.exchange, 'BACKTEST')
        self.assertEqual(ee.quantity, 1.0)