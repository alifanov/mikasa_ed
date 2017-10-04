import numpy as np
import pandas as pd
from abc import ABCMeta, abstractmethod

from .event import SignalEvent

import statsmodels.api as sm


class Strategy(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def calculate_signals(self, queue):
        raise NotImplementedError("Should implement calculate_signals()")


class BuyAndHoldStrategy(Strategy):
    def __init__(self, bars, queue):
        self.bars = bars
        self.symbol_list = self.bars.symbol_list
        self.queue = queue

        # Once buy & hold signal is given, these are set to True
        self.bought = self._calculate_initial_bought()

    def _calculate_initial_bought(self):
        bought = {}
        for s in self.symbol_list:
            bought[s] = False
        return bought

    def calculate_signals(self, event):
        if event.type == 'MARKET':
            for s in self.symbol_list:
                bars = self.bars.get_latest_bars(s, N=1)
                if bars is not None and bars != []:
                    if not self.bought[s]:
                        # (Symbol, Datetime, Type = LONG, SHORT or EXIT)
                        signal = SignalEvent(
                            'BUY_AND_HOLD',
                            bars[0].symbol,
                            bars[0].datetime,
                            'LONG',
                            1.0)
                        self.queue.put(signal)
                        self.bought[s] = True


class SMAStrategy(Strategy):
    def __init__(self, bars, queue, period=50):
        self.bars = bars
        self.queue = queue
        self.period = period

    def calculate_signals(self, event):
        if event.type == 'MARKET':
            if self.bars.index > self.period:

                data = self.bars.get_latest_bars(self.bars.symbol_list[0], 10*self.period)

                data = pd.DataFrame(data)
                data.set_index('datetime', inplace=True)

                sma = data['close'].rolling(center=False, window=self.period).mean()

                if data.iloc[-1]['close'] > sma[-1] and data.iloc[-2]['close'] <= sma[-2]:
                    signal = SignalEvent(self.bars.symbol_list[0], data.iloc[-1]['close'], 'LONG', 1.0)
                    self.queue.put(signal)
                if data.iloc[-1]['close'] < sma[-1] and data.iloc[-2]['close'] >= sma[-2]:
                    signal = SignalEvent(self.bars.symbol_list[0], data.iloc[-1]['close'], 'EXIT', 1.0)
                    self.queue.put(signal)


class StatArbitrageStrategy(Strategy):
    LOOK_BACK = 1000
    Z_ENTRY_THRESHOLD = 2.0
    Z_EXIT_THRESHOLD = 1.0
    WINDOW = 900

    def __init__(self, bars, queue):
        self.bars = bars
        self.symbol_list = self.bars.symbol_list
        self.queue = queue

    def calculate_signals(self, event):
        print(self.bars.index)
        if event.type == 'MARKET':
            s0 = 'BTC_ETC'
            s1 = 'BTC_LTC'
            if self.bars.index > self.LOOK_BACK:

                X = self.bars.get_latest_bars(s0, self.LOOK_BACK)
                Y = self.bars.get_latest_bars(s1, self.LOOK_BACK)

                X = pd.DataFrame(X)
                X.set_index('datetime', inplace=True)
                Y = pd.DataFrame(Y)
                Y.set_index('datetime', inplace=True)

                ols = rolling_sm_ols(Y['close'], X['close'], X.index, window=self.WINDOW)
                # ols = sm.OLS(Y['close'].values, X['close'].values).fit()
                # print(ols.params)

                # ols = rolling_beta(X['close'], Y['close'], X.index, window=self.LOOK_BACK)
                pairs = pd.concat([X['close'], Y['close']], axis=1, keys=['{}_close'.format(s0), '{}_close'.format(s1)])

                pairs['hedge_ratio'] = ols['beta']
                pairs.dropna(inplace=True)

                pairs['hedge_ratio'] = [v for v in pairs['hedge_ratio'].values]
                pairs['spread'] = pairs['{}_close'.format(s0)] - pairs['hedge_ratio'] * pairs['{}_close'.format(s1)]
                pairs['zscore'] = (pairs['spread'] - np.mean(pairs['spread'])) / np.std(pairs['spread'])
                current_zscore = pairs.iloc[-1]['zscore']
                current_x_close = pairs.iloc[-1]['{}_close'.format(s0)]
                current_y_close = pairs.iloc[-1]['{}_close'.format(s1)]

                if current_zscore <= -self.Z_ENTRY_THRESHOLD:
                    signal = SignalEvent(s0, current_x_close, 'LONG', 1.0)
                    self.queue.put(signal)
                    signal = SignalEvent(s1, current_y_close, 'SHORT', 1.0)
                    self.queue.put(signal)
                elif current_zscore >= self.Z_ENTRY_THRESHOLD:
                    signal = SignalEvent(s0, current_x_close, 'SHORT', 1.0)
                    self.queue.put(signal)
                    signal = SignalEvent(s1, current_y_close, 'LONG', 1.0)
                    self.queue.put(signal)
                elif current_zscore <= self.Z_EXIT_THRESHOLD:
                    signal = SignalEvent(s0, current_x_close, 'EXIT', 1.0)
                    self.queue.put(signal)
                    signal = SignalEvent(s1, current_y_close, 'EXIT', 1.0)
                    self.queue.put(signal)
