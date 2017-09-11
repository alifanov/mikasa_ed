class Broker:
    INTERACTIVE_BROKER = 'IB'


class Event:
    pass


class MarketEvent(Event):
    type = 'MARKET'


class SignalEvent(Event):
    def __init__(self, strategy_id, symbol, datetime, signal_type, strength):
        self.type = 'SIGNAL'

        self.strategy_id = strategy_id
        self.symbol = symbol
        self.datetime = datetime
        self.signal_type = signal_type # LONG, SHORT, EXIT
        self.strength = strength


class OrderEvent(Event):
    def __init__(self, symbol, order_type, quantity, direction):
        self.type = 'ORDER'
        self.symbol = symbol
        self.order_type = order_type
        self.quantity = quantity
        self.direction = direction

    def print_order(self):
        print("Order: Symbol={}, Type={}, Quantity={}, Direction={}".format(self.symbol, self.order_type, self.quantity,
                                                                            self.direction))


class FillEvent(Event):
    def __init__(self, timeindex, symbol, exchange, quantity,
                 direction, fill_cost, commission=None):
        self.type = 'FILL'
        self.timeindex = timeindex
        self.symbol = symbol
        self.exchange = exchange
        self.quantity = quantity
        self.direction = direction
        self.fill_cost = fill_cost

        # Calculate commission
        if commission is None:
            self.commission = self.calculate_commission(Broker.INTERACTIVE_BROKER)
        else:
            self.commission = commission

    def calculate_commission(self, broker):
        commission = 0.002 * self.quantity
        # if broker == Broker.INTERACTIVE_BROKER:
        #     if self.quantity <= 500:
        #         commission = max(1.3, 0.013 * self.quantity)
        #     else:  # Greater than 500
        #         commission = max(1.3, 0.008 * self.quantity)
        #         commission = min(commission, 0.5 / 100.0 * self.quantity)
        return commission
