import keras

import sys

sys.path.append('../')

import os
import datetime
import numpy as np

np.random.seed(7)

import pandas as pd
from strategy import Strategy
from event import SignalEvent
from backtest import Backtest
from data import HistoricCSVDataHandler
from portfolio import NaivePortfolio
from execution import SimulatedExecutionHandler

from sklearn.preprocessing import StandardScaler


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

        self.close_fields = ['close-{}'.format(i+1) for i in range(self.lag)]

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
                if prediction[1] > 0.9:
                    signal = SignalEvent(1, self.symbol_list[0], dt, 'LONG', 1.0)
                    self.events.put(signal)
                if prediction[0] > 0.9:
                    signal = SignalEvent(1, self.symbol_list[0], dt, 'EXIT', 1.0)
                    self.events.put(signal)


if __name__ == "__main__":
    csv_dir = '../datasets/5min/'
    symbol_list = ['BTC_ETH', ]
    initial_capital = 1000.0
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
        NaivePortfolio,
        PredictStrategy,
        fields=['open', 'high', 'low', 'close']
    )
    backtest.simulate_trading()
    backtest.plot()
