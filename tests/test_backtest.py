from datetime import datetime

from unittest import TestCase

from backtest import Backtest
from data import HistoricCSVDataHandler
from execution import SimulatedExecutionHandler
from portfolio import NaivePortfolio
from strategy import BuyAndHoldStrategy


class BacktestTestCase(TestCase):
    def test_create(self):
        csv_dir = './tests/datasets/'
        symbol_list = ['BTC_ETC', ]
        initial_capital = 1000.0
        heartbeat = 0.0
        start_date = datetime(2017, 4, 21, 0, 0, 1)
        backtest = Backtest(
            csv_dir,
            symbol_list,
            initial_capital,
            heartbeat,
            start_date,
            HistoricCSVDataHandler,
            SimulatedExecutionHandler,
            NaivePortfolio,
            BuyAndHoldStrategy,
            fields=['open', 'high', 'low', 'close']
        )
        self.assertEqual(backtest.heartbeat, 0.0)
        self.assertEqual(backtest.initial_capital, 1000.0)
        self.assertEqual(backtest.signals, 0)
        self.assertEqual(backtest.orders, 0)
        self.assertEqual(backtest.fills, 0)
        self.assertEqual(backtest.num_strats, 1.0)

    def test_simulate(self):
        csv_dir = './tests/datasets/'
        symbol_list = ['BTC_ETC', ]
        initial_capital = 1000.0
        heartbeat = 0.0
        start_date = datetime(2017, 4, 21, 0, 0, 1)
        backtest = Backtest(
            csv_dir,
            symbol_list,
            initial_capital,
            heartbeat,
            start_date,
            HistoricCSVDataHandler,
            SimulatedExecutionHandler,
            NaivePortfolio,
            BuyAndHoldStrategy,
            fields=['open', 'high', 'low', 'close']
        )
        backtest.simulate_trading()
        backtest.portfolio.create_equity_curve_dataframe()
        stats = backtest.portfolio.output_summary_stats()
        self.assertEqual(stats, [('Total Return', '-0.01%'),
                                 ('Sharpe Ratio', '-17.72'),
                                 ('Max Drawdown', '0.02%'),
                                 ('Drawdown Duration', '2000')])
