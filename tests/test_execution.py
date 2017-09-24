import queue

from datetime import datetime

from unittest import TestCase
from execution import SimulatedExecutionHandler
from data import HistoricCSVDataHandler
from portfolio import NaivePortfolio

from event import OrderEvent


class ExecutionTestCase(TestCase):
    def test_execution(self):
        events_queue = queue.Queue(100)
        oe = OrderEvent(
            'BTC_ETC',
            'MKT',
            1.0,
            'BUY'
        )
        e = SimulatedExecutionHandler(events_queue, portfolio=None)
        e.execute_order(oe)
        ee = events_queue.get(False)
        self.assertEqual(ee.type, 'FILL')
        self.assertEqual(ee.direction, 'BUY')
        self.assertEqual(ee.exchange, 'BACKTEST')
        self.assertEqual(ee.quantity, 1.0)

    def test_execution_stop_order(self):
        csv_dir = './tests/datasets/'
        symbol_list = ['BTC_ETC', ]
        events_queue = queue.Queue(100)
        bars = HistoricCSVDataHandler(
            events_queue,
            csv_dir,
            symbol_list,
            ['open', 'high', 'low', 'close']
        )
        p = NaivePortfolio(bars, events_queue, datetime(2017, 4, 1, 0, 0, 0), 1000.0)
        e = SimulatedExecutionHandler(events_queue, portfolio=p)

        bars.update_bars()
        oe = OrderEvent(
            'BTC_ETC',
            'STP',
            300000.0,
            'BUY',
            0.00259
        )
        e.execute_order(oe)
        self.assertTrue(len(e.stop_orders) > 0)
        bars.update_bars()
        ee = events_queue.get(False)
        e.check_stop_orders(ee)
        p.update_timeindex(ee)

        p.create_equity_curve_dataframe()
        self.assertEqual(p.equity_curve['equity_curve'][-1], 1.0001020000000001)
