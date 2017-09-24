from __future__ import print_function
import datetime
import numpy as np
import pandas as pd
import statsmodels.api as sm
from strategy import Strategy
from event import SignalEvent
from backtest import Backtest
from data import HistoricCSVDataHandler
from portfolio import NaivePortfolio
from execution import SimulatedExecutionHandler


class IntradayOLSMRStrategy(Strategy):
    def __init__(self, bars, events, ols_window=500, zscore_low=0.5, zscore_high=3.0):
        """
        Initialises the stat arb strategy.
        Parameters:
        bars - The DataHandler object that provides bar information
        events - The Event Queue object.
        """
        self.bars = bars
        self.symbol_list = self.bars.symbol_list
        self.events = events
        self.ols_window = ols_window
        self.zscore_low = zscore_low
        self.zscore_high = zscore_high
        self.pair = ('BTC_ETC', 'BTC_LTC')
        self.datetime = datetime.datetime.utcnow()
        self.long_market = False
        self.short_market = False
        self.hedge_ratio = None

    def calculate_xy_signals(self, zscore_last):
        y_signal = None
        x_signal = None
        p0 = self.pair[0]
        p1 = self.pair[1]
        dt = self.datetime
        hr = abs(self.hedge_ratio)
        # If we're long the market and below the
        # negative of the high zscore threshold
        if zscore_last <= -self.zscore_high and not self.long_market:
            self.long_market = True
            y_signal = SignalEvent(1, p0, dt, 'LONG', 1.0)
            x_signal = SignalEvent(1, p1, dt, 'SHORT', hr)
        # If we're long the market and between the
        # absolute value of the low zscore threshold
        if abs(zscore_last) <= self.zscore_low and self.long_market:
            self.long_market = False
            y_signal = SignalEvent(1, p0, dt, 'EXIT', 1.0)
            x_signal = SignalEvent(1, p1, dt, 'EXIT', 1.0)
        # If we're short the market and above
        # the high zscore threshold
        if zscore_last >= self.zscore_high and not self.short_market:
            self.short_market = True
            y_signal = SignalEvent(1, p0, dt, 'SHORT', 1.0)
            x_signal = SignalEvent(1, p1, dt, 'LONG', hr)
        # If we're short the market and between the
        # absolute value of the low zscore threshold
        if abs(zscore_last) <= self.zscore_low and self.short_market:
            self.short_market = False
            y_signal = SignalEvent(1, p0, dt, 'EXIT', 1.0)
            x_signal = SignalEvent(1, p1, dt, 'EXIT', 1.0)
        return y_signal, x_signal

    def calculate_signals_for_pairs(self):
        # Obtain the latest window of values for each
        # component of the pair of tickers
        y = pd.DataFrame(self.bars.get_latest_bars_values(
            self.pair[0], "close", N=self.ols_window
        ))
        x = pd.DataFrame(self.bars.get_latest_bars_values(
            self.pair[1], "close", N=self.ols_window
        ))
        if y is not None and x is not None:
            # Check that all window periods are available
            if len(y) >= self.ols_window and len(x) >= self.ols_window:
                # Calculate the current hedge ratio using OLS
                self.hedge_ratio = sm.OLS(y, x).fit().params[0]
                # Calculate the current z-score of the residuals
                spread = y - self.hedge_ratio * x
                zscore_last = ((spread - spread.mean()) / spread.std()).iloc[-1, 0]
                # Calculate signals and add to events queue
                y_signal, x_signal = self.calculate_xy_signals(zscore_last)
                if y_signal is not None and x_signal is not None:
                    self.events.put(y_signal)
                    self.events.put(x_signal)

    def calculate_signals(self, event):
        if event.type == 'MARKET':
            self.calculate_signals_for_pairs()


if __name__ == "__main__":
    csv_dir = './datasets/'
    symbol_list = ['BTC_ETC', 'BTC_LTC']
    initial_capital = 1000.0
    heartbeat = 0.0
    start_date = datetime.datetime(2017, 4, 21, 0, 0, 1)
    backtest = Backtest(
        csv_dir,
        symbol_list,
        initial_capital,
        heartbeat,
        start_date,
        HistoricCSVDataHandler,
        SimulatedExecutionHandler,
        NaivePortfolio,
        IntradayOLSMRStrategy,
        fields=['open', 'high', 'low', 'close'],
        ticks_limit=2000
    )
    backtest.simulate_trading()
    backtest.plot()
