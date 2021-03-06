import datetime
import os, os.path
import pandas as pd

from poloniex import Poloniex

from abc import ABCMeta, abstractmethod

from .event import MarketEvent


class DataPoint:
    def __init__(self, dt):
        self.dt = dt

    def to_dict(self):
        return self.dt

    def __repr__(self):
        return str(self.dt)

    def __getattr__(self, key):
        return self.dt[key]


class DataHandler(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_latest_bars_values(self, symbol, val_type, N=1):
        raise NotImplementedError("Should implement get_latest_bar_values()")

    @abstractmethod
    def get_latest_bars(self, symbol, N=1):
        raise NotImplementedError("Should implement get_latest_bars()")

    @abstractmethod
    def update_bars(self):
        raise NotImplementedError("Should implement update_bars()")


class HistoricCSVDataHandler(DataHandler):
    def __init__(self, events, csv_dir, symbol_list, fields, limit=None):
        self.events = events
        self.csv_dir = csv_dir
        self.symbol_list = symbol_list
        self.fields = fields

        self.symbol_data = {}
        self.latest_symbol_data = {}
        self.continue_backtest = True

        self.limit = limit

        self._open_convert_csv_files()

    def _open_convert_csv_files(self):
        comb_index = None
        for s in self.symbol_list:
            fname = os.path.join(self.csv_dir, '%s.csv' % s)

            self.symbol_data[s] = pd.read_csv(
                fname,
                header=0,
                index_col=0,
                # names=self.fields,
                nrows=self.limit
            )

            # Combine the index to pad forward values
            if comb_index is None:
                comb_index = self.symbol_data[s].index
            else:
                comb_index.union(self.symbol_data[s].index)

            # Set the latest symbol_data to None
            self.latest_symbol_data[s] = []

        # Reindex the dataframes
        for s in self.symbol_list:
            self.symbol_data[s] = self.symbol_data[s].reindex(index=comb_index, method='pad').iterrows()

    def _get_new_bar(self, symbol):
        for b in self.symbol_data[symbol]:
            yield DataPoint({
                'symbol': symbol,
                'datetime': datetime.datetime.fromtimestamp(b[0]),
                'timestamp': b[0],
                'open': b[1].open,
                'high': b[1].high,
                'low': b[1].low,
                'close': b[1].close,
                'volume': b[1].volume
            })

    def get_latest_bars_values(self, symbol, val_type, N=1):
        return [getattr(b, val_type) for b in self.get_latest_bars(symbol, N)]

    def get_latest_bars(self, symbol, N=1):
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
        else:
            return bars_list[-N:]

    def update_bars(self):
        for s in self.symbol_list:
            try:
                bar = next(self._get_new_bar(s))
            except StopIteration:
                self.continue_backtest = False
            else:
                if bar is not None:
                    self.latest_symbol_data[s].append(bar)
        self.events.put(MarketEvent(market_data={s: self.latest_symbol_data[s][-1] for s in self.symbol_list}))


class PoloniexDataHandler(HistoricCSVDataHandler):
    def __init__(self, events, symbol_list, period):
        self.events = events
        self.symbol_list = symbol_list

        self.latest_symbol_data = {s: [] for s in self.symbol_list}
        self.continue_backtest = True

        self.period = period

    def _get_new_bar(self, symbol):
        polo = Poloniex()
        start = datetime.datetime.now() - datetime.timedelta(days=1)
        data = polo.returnChartData(symbol, period=self.period, start=start.timestamp())[-1]

        yield DataPoint({
            'symbol': symbol,
            'datetime': datetime.datetime.fromtimestamp(data['date']),
            'timestamp': data['date'],
            'open': data['open'],
            'high': data['high'],
            'low': data['low'],
            'close': data['close'],
            'volume': data['volume']
        })
