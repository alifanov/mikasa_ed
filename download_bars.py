import csv
import requests

from datetime import datetime, timedelta

POLONIEX_TIME_FRAME_MAP = {
    '5min': 300,
    '30min': 1800,
    'day': 86400
}

FIELDS = [
            'datetime',
            'open',
            'high',
            'low',
            'close'
        ]


def download_bars(pair, start_date, end_date, time_frame='5min'):
    r = requests.get('https://poloniex.com/public?command=returnChartData',
        params={
            'currencyPair': pair,
            'start': start_date.timestamp(),
            'end': end_date.timestamp(),
            'period': POLONIEX_TIME_FRAME_MAP[time_frame]
        })
    r.raise_for_status()
    with open('datasets/{}/{}.csv'.format(time_frame, pair), 'w') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for d in r.json():
            d['datetime'] = d['date']
            dd = {f: d[f] for f in FIELDS}
            writer.writerow(dd)

if __name__ == "__main__":
    for p in ['5min', '30min', 'day']:
        download_bars('BTC_LTC', datetime.utcnow() - timedelta(days=365), datetime.utcnow(), time_frame=p)