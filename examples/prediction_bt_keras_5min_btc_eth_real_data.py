import keras

import sys

sys.path.append('../')

import os
import datetime
import numpy as np
import pandas as pd

np.random.seed(7)

from mikasa.strategy import Strategy
from mikasa.event import SignalEvent, OrderEvent
from mikasa.backtest import Backtest
from mikasa.data import HistoricCSVDataHandler, PoloniexDataHandler
from mikasa.portfolio import NaivePortfolio
from mikasa.execution import SimulatedExecutionHandler

from sklearn.preprocessing import StandardScaler


class NaiveStopPortfolio(NaivePortfolio):
    TILT = 0.001

    def generate_naive_order(self, signal):
        order = None

        mkt_quantity = 1000.0
        cur_quantity = self.current_positions[signal.symbol]
        order_type = 'STP'

        price = self.bars.get_latest_bars(signal.symbol)[0].close

        if signal.signal_type == 'LONG' and cur_quantity == 0:
            price *= (1.0 + self.TILT)
            order = OrderEvent(signal.symbol, order_type, mkt_quantity, 'BUY', price)
        if signal.signal_type == 'SHORT' and cur_quantity == 0:
            price *= (1.0 - self.TILT)
            order = OrderEvent(signal.symbol, order_type, mkt_quantity, 'SELL', price)

        if signal.signal_type == 'EXIT':
            if cur_quantity > 0:
                price *= (1.0 - self.TILT)
                order = OrderEvent(signal.symbol, order_type, abs(cur_quantity), 'SELL', price)
            if cur_quantity < 0:
                price *= (1.0 + self.TILT)
                order = OrderEvent(signal.symbol, order_type, abs(cur_quantity), 'BUY', price)

        return order


class PredictStrategy(Strategy):
    def __init__(self, bars, events):
        self.bars = bars
        self.symbol_list = self.bars.symbol_list
        self.events = events

        self.lag = 12

        csv_dir = '../datasets/5min/'

        df = pd.read_csv(os.path.join(csv_dir, symbol_list[0] + '.csv'))
        for lag in range(1, self.lag + 1):
            df['close-' + str(lag)] = df['close'] - df.shift(lag)['close']
        df.dropna(inplace=True)

        self.close_fields = ['close-{}'.format(i + 1) for i in range(self.lag)]

        df['up'] = df['close'] < df.shift(-1)['close']

        self.scaler = StandardScaler()
        X = df[self.close_fields].values
        self.scaler.fit(X)

        self.model = keras.models.load_model('../research/keras_5min_btc_eth.h5')

    def calculate_signals(self, event):
        if event.type == 'MARKET':
            dt = self.bars.get_latest_bars_values(self.symbol_list[0], 'datetime')[0]

            X = self.bars.get_latest_bars_values(self.symbol_list[0], 'close', N=self.lag + 1)
            if len(X) == self.lag + 1:
                df = pd.DataFrame(X, columns=['close'])
                for lag in range(1, self.lag + 1):
                    df['close-' + str(lag)] = df['close'] - df.shift(lag)['close']
                df.dropna(inplace=True)
                X = df[self.close_fields].values
                X = self.scaler.transform(X)
                prediction = self.model.predict(X)[0]
                if prediction[1] > 0.7:
                    signal = SignalEvent(1, self.symbol_list[0], dt, 'LONG', 1.0)
                    self.events.put(signal)
                if prediction[0] > 0.7:
                    signal = SignalEvent(1, self.symbol_list[0], dt, 'EXIT', 1.0)
                    self.events.put(signal)


class PoloniexBacktest(Backtest):
    def _generate_trading_instances(self):
        self.data_handler = self.data_handler_cls(self.events,
                                                  self.symbol_list, period=300)
        self.strategy = self.strategy_cls(self.data_handler, self.events)
        self.portfolio = self.portfolio_cls(self.data_handler, self.events,
                                            self.start_date,
                                            self.initial_capital)
        self.execution_handler = self.execution_handler_cls(self.events, self.portfolio)


if __name__ == "__main__":
    csv_dir = '../datasets/5min/'
    symbol_list = ['BTC_ETH', ]
    initial_capital = 1000.0
    heartbeat = 1
    start_date = datetime.datetime.now()

    backtest = PoloniexBacktest(
        csv_dir,
        symbol_list,
        initial_capital,
        heartbeat,
        start_date,
        PoloniexDataHandler,
        SimulatedExecutionHandler,
        NaiveStopPortfolio,
        PredictStrategy,
        fields=['open', 'high', 'low', 'close', 'volume']
    )
    backtest.simulate_trading()
    backtest.plot()
