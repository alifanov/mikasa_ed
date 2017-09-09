import queue

from unittest import TestCase

from strategy import BuyAndHoldStrategy
from data import HistoricCSVDataHandler


class StrategyTestCase(TestCase):
    def test_bnh_strategy(self):
        events_queue = queue.Queue(100)
        bars = HistoricCSVDataHandler(
            events_queue,
            './datasets/',
            ['BTC_ETC'],
            ['open', 'high', 'low', 'close']
        )
        strategy = BuyAndHoldStrategy(bars, events_queue)

        bars.update_bars()
        event = events_queue.get(False)
        strategy.calculate_signals(event)

        signal = events_queue.get(False)
        self.assertEqual(signal.symbol, 'BTC_ETC')
        self.assertEqual(signal.strategy_id, 'BUY_AND_HOLD')
        self.assertEqual(signal.signal_type, 'LONG')
