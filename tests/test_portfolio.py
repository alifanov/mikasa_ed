import queue

from unittest import TestCase
from datetime import datetime

from portfolio import NaivePortfolio
from data import HistoricCSVDataHandler
from event import FillEvent, SignalEvent


class PortfolioTestCase(TestCase):
    def test_create(self):
        events_queue = queue.Queue(100)
        bars = HistoricCSVDataHandler(
            events_queue,
            './datasets/',
            ['BTC_ETC'],
            ['open', 'high', 'low', 'close']
        )

        p = NaivePortfolio(bars, events_queue, datetime(2017, 4, 1, 0, 0, 0), 1000.0)
        self.assertEqual(p.initial_capital, 1000.0)
        self.assertEqual(p.all_positions, [{'datetime': datetime(2017, 4, 1, 0, 0, 0), 'BTC_ETC': 0}])
        self.assertEqual(p.all_holdings, [{'datetime': datetime(2017, 4, 1, 0, 0, 0), 'BTC_ETC': 0, 'cash': 1000.0,
                                           'commission': 0, 'total': 1000.0}])

    def test_update_signal(self):
        events_queue = queue.Queue(100)
        bars = HistoricCSVDataHandler(
            events_queue,
            './datasets/',
            ['BTC_ETC'],
            ['open', 'high', 'low', 'close']
        )

        p = NaivePortfolio(bars, events_queue, datetime(2017, 4, 1, 0, 0, 0), 1000.0)
        bars.update_bars()
        signal = SignalEvent(
            'BUY_AND_HOLD',
            'BTC_ETC',
            datetime.utcnow(),
            'LONG',
            1.0
        )
        p.update_signal(signal)
        events_queue.get(False) # MARKET
        event = events_queue.get(False) # ORDER

        self.assertEqual(event.type, 'ORDER')
        self.assertEqual(event.order_type, 'MKT')
        self.assertEqual(event.direction, 'BUY')
        self.assertEqual(event.quantity, 100)

    def test_update_fill(self):
        events_queue = queue.Queue(100)
        bars = HistoricCSVDataHandler(
            events_queue,
            './datasets/',
            ['BTC_ETC'],
            ['open', 'high', 'low', 'close']
        )

        p = NaivePortfolio(bars, events_queue, datetime(2017, 4, 1, 0, 0, 0), 1000.0)
        fill_event = FillEvent(
            datetime.utcnow(),
            'BTC_ETC',
            'BACKTEST',
            1.0,
            'BUY',
            None
        )
        bars.update_bars()
        p.update_fill(fill_event)
        self.assertEqual(p.current_holdings, {
            'BTC_ETC': 0.0025947399999999999,
            'cash': 999.99540525999998,
            'commission': 0.002,
            'total': 999.99540525999998})
        self.assertEqual(p.current_positions, {
            'BTC_ETC': 1.0
        })

        bars.update_bars()
        p.update_timeindex(None)

        self.assertEqual(p.all_positions, [{'BTC_ETC': 0, 'datetime': datetime(2017, 4, 1, 0, 0)},
                                           {'BTC_ETC': 1.0, 'datetime': datetime(2017, 4, 22, 18, 35)}])
        print(p.all_holdings)
        self.assertEqual(p.all_holdings, [
            {'commission': 0.0, 'BTC_ETC': 0.0, 'total': 1000.0, 'datetime': datetime(2017, 4, 1, 0, 0),
             'cash': 1000.0}, {'commission': 0.002, 'BTC_ETC': 0.00259552, 'total': 999.99800077999998,
                               'datetime': datetime(2017, 4, 22, 18, 35), 'cash': 999.99540525999998}])
