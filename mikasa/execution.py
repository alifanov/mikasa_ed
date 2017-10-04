import datetime

from abc import ABCMeta, abstractmethod

from .event import FillEvent, OrderEvent


class ExecutionHandler(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def execute_order(self, queue):
        raise NotImplementedError("Should implement execute_order()")


class SimulatedExecutionHandler(ExecutionHandler):
    def __init__(self, events, portfolio):
        self.events = events
        self.stop_orders = []

        self.portfolio = portfolio

    def check_stop_orders(self, event):
        if event.type == 'MARKET':
            for order in self.stop_orders:
                for s in event.market_data:
                    if order.symbol == s:
                        if event.market_data[s].close > order.price and order.direction == 'BUY':
                            fill_event = FillEvent(order.datetime, order.symbol,
                                       'BACKTEST', order.quantity, order.direction, order.price)
                            self.portfolio.update_fill(fill_event)
                            self.stop_orders.remove(order)
                        if event.market_data[s].close < order.price and order.direction == 'SELL':
                            fill_event = FillEvent(order.datetime, order.symbol,
                                       'BACKTEST', order.quantity, order.direction, order.price)
                            self.portfolio.update_fill(fill_event)
                            self.stop_orders.remove(order)

    def execute_order(self, event):
        if event.type == 'ORDER':
            if event.order_type == 'MKT':
                fill_event = FillEvent(datetime.datetime.utcnow(), event.symbol,
                                       'BACKTEST', event.quantity, event.direction, None)
                self.events.put(fill_event)
            if event.order_type == 'STP':
                event.datetime = datetime.datetime.utcnow()
                self.stop_orders.append(event)
