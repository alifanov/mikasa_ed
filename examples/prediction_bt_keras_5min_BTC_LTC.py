import keras

import sys

sys.path.append('../')

import os
import datetime
import numpy as np

np.random.seed(7)

import pandas as pd
from mikasa.strategy import Strategy
from mikasa.event import SignalEvent, OrderEvent
from mikasa.backtest import Backtest
from mikasa.data import HistoricCSVDataHandler
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

        self.lag = 18

        csv_dir = '../datasets/5min/'
        df = pd.read_csv(os.path.join(csv_dir, self.symbol_list[0] + '.csv'), index_col=0)

        df['datetime'] = pd.to_datetime(df.index, unit='s')
        df['hour'] = df['datetime'].dt.hour
        df['dow'] = df['datetime'].dt.weekday

        df = pd.get_dummies(df, columns=['dow', 'hour'])
        self.dow_fields = [col for col in df if col.startswith('dow')]
        self.hour_fields = [col for col in df if col.startswith('hour')]

        for lag in range(1, self.lag + 1):
            df['close-' + str(lag)] = df['close'] - df.shift(lag)['close']
            df['volume-' + str(lag)] = df['volume'] - df.shift(lag)['volume']
        df.dropna(inplace=True)

        self.close_fields = ['close-{}'.format(i + 1) for i in range(self.lag)]
        self.volume_fields = ['volume-{}'.format(i + 1) for i in range(self.lag)]

        df['up'] = df['close'] < df.shift(-1)['close']

        self.scaler = StandardScaler()
        X = df[self.close_fields + self.volume_fields + self.dow_fields + self.hour_fields].values
        self.scaler.fit(X)

        self.model = keras.models.load_model('../research/keras_5min_lag_18_BTC_LTC.h5')

    def calculate_signals(self, event):
        if event.type == 'MARKET':
            dt = self.bars.get_latest_bars_values(self.symbol_list[0], 'datetime')[0]

            X_dt = self.bars.get_latest_bars_values(self.symbol_list[0], 'datetime', N=self.lag + 1)
            X_close = self.bars.get_latest_bars_values(self.symbol_list[0], 'close', N=self.lag + 1)
            X_vol = self.bars.get_latest_bars_values(self.symbol_list[0], 'volume', N=self.lag + 1)

            if len(X_dt) == self.lag + 1:

                df = pd.DataFrame(list(zip(X_dt, X_close, X_vol)), columns=['datetime', 'close', 'volume'])
                df.set_index('datetime', inplace=True)

                df['datetime'] = pd.to_datetime(df.index, unit='s')
                df['hour'] = df['datetime'].dt.hour
                df['dow'] = df['datetime'].dt.weekday
                df = pd.get_dummies(df, columns=['dow', 'hour'])
                missing_columns = set(self.dow_fields + self.hour_fields) - set(df.columns)
                for c in missing_columns:
                    df[c] = pd.Series(0, index=df.index)

                for lg in range(1, self.lag + 1):
                    df['close-' + str(lg)] = df['close'] - df.shift(lg)['close']
                    df['volume-' + str(lg)] = df['volume'] - df.shift(lg)['volume']
                df.dropna(inplace=True)
                df.drop(['datetime', 'close', 'volume'], inplace=True, axis=1)

                X = df[self.close_fields + self.volume_fields + self.dow_fields + self.hour_fields].values
                X = self.scaler.transform(X)

                prediction = self.model.predict(X)[0]
                if prediction[1] > 0.7:
                    signal = SignalEvent(1, self.symbol_list[0], dt, 'LONG', 1.0)
                    self.events.put(signal)
                if prediction[0] > 0.7:
                    signal = SignalEvent(1, self.symbol_list[0], dt, 'EXIT', 1.0)
                    self.events.put(signal)


if __name__ == "__main__":
    csv_dir = '../datasets/5min/'
    symbol_list = ['BTC_LTC', ]
    initial_capital = 1.0
    heartbeat = 0.0
    start_date = datetime.datetime(2016, 9, 9, 0, 0, 1)

    backtest = Backtest(
        csv_dir,
        symbol_list,
        initial_capital,
        heartbeat,
        start_date,
        HistoricCSVDataHandler,
        SimulatedExecutionHandler,
        NaiveStopPortfolio,
        PredictStrategy,
        fields=['open', 'high', 'low', 'close', 'volume']
    )
    backtest.simulate_trading()
    backtest.plot()
