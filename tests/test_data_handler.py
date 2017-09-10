import queue

from unittest import TestCase
from data import HistoricCSVDataHandler


class DataHandlerTestCase(TestCase):
    def test_historical_data_handler(self):
        s = 'BTC_ETC'
        events_queue = queue.Queue(100)
        data = HistoricCSVDataHandler(
            events_queue,
            './tests/datasets',
            [s],
            ['open', 'high', 'low', 'close']
        )

        self.assertEqual(set(data.symbol_data.keys()), {s})

        data.update_bars()

        d = data.get_latest_bars(s)[0]
        self.assertEqual(round(d.open, 8), 0.00258999)
        self.assertEqual(round(d.high, 8), 0.00259506)
        self.assertEqual(round(d.low, 8), 0.00258998)
        self.assertEqual(round(d.close, 8), 0.00259474)

        self.assertEqual(data.get_latest_bars(s)[0], d)
        self.assertEqual(data.get_latest_bars(s), [d])
        self.assertEqual(data.get_latest_bars_values(s, 'datetime')[0], d.datetime)
        self.assertEqual(round(data.get_latest_bars_values(s, 'open')[0], 8), 0.00258999)
        values = data.get_latest_bars_values(s, 'open')
        self.assertEqual(round(values[0], 8), 0.00258999)