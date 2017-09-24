import os
import pandas as pd
import backtrader as bt
import keras

from sklearn.preprocessing import StandardScaler


class PredictStrategy(bt.Strategy):
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.symbol = 'BTC_ETH'

        self.lag = 12
        csv_dir = '../datasets/5min/'

        df = pd.read_csv(os.path.join(csv_dir, self.symbol + '.csv'))
        for lag in range(1, self.lag + 1):
            df['close-' + str(lag)] = df['close'] - df.shift(lag)['close']
        df.dropna(inplace=True)

        self.close_fields = ['close-{}'.format(i + 1) for i in range(self.lag)]

        df['up'] = df['close'] < df.shift(-1)['close']

        self.scaler = StandardScaler()
        X = df[self.close_fields].values
        self.scaler.fit(X)

        self.model = keras.models.load_model('../research/keras_5min_btc_eth.h5')

    def next(self):
        if len(self) > self.lag:
            X = [self.dataclose[n] for n in range(-self.lag, 1)]
            df = pd.DataFrame(X, columns=['close'])
            for lag in range(1, self.lag + 1):
                df['close-' + str(lag)] = df['close'] - df.shift(lag)['close']
            df.dropna(inplace=True)
            X = df[self.close_fields].values
            X = self.scaler.transform(X)
            prediction = self.model.predict(X)[0]
            if prediction[1] > 0.7:
                if not self.position:
                    self.buy(size=1.0)
            if prediction[0] > 0.7:
                if self.position:
                    self.sell(size=1.0)


if __name__ == '__main__':
    cerebro = bt.Cerebro()

    cerebro.addstrategy(PredictStrategy)

    datapath = os.path.join('../datasets/5min/BTC_ETH_noheader.csv')

    data = bt.feeds.GenericCSVData(
        dataname=datapath,

        dtformat=1,

        time=-1,
        datetime=0,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5,
        openinterest=-1
    )

    cerebro.adddata(data)

    cerebro.broker.setcash(2.0)

    cerebro.broker.setcommission(commission=0.002)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    cerebro.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
