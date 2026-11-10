import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'XAUTUSDT', 'SNDKUSDT', 'ZECUSDT', 'QNTUSDT']
INTERVALS = {'15m': '15', '4h': '240'}
BASE = 'https://api.bytick.com/v5/market/kline'


def fetch(symbol, interval):
    query = urllib.parse.urlencode({'category': 'linear', 'symbol': symbol, 'interval': interval, 'limit': 160})
    request = urllib.request.Request(f'{BASE}?{query}', headers={'User-Agent': 'bybit-market-scanner/1.0'})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)
    if data.get('retCode') != 0:
        raise RuntimeError(f"{symbol}/{interval}: {data.get('retMsg')}")
    rows = sorted(data['result']['list'], key=lambda x: int(x[0]))
    # Exclude the current, potentially unfinished candle.
    now_ms = int(time.time() * 1000)
    duration_ms = int(interval) * 60_000
    rows = [r for r in rows if int(r[0]) + duration_ms <= now_ms]
    if len(rows) < 40:
        raise RuntimeError(f'{symbol}/{interval}: insufficient completed candles')
    return rows


def ema(values, period):
    alpha = 2 / (period + 1)
    result = [values[0]]
    for v in values[1:]:
        result.append(alpha * v + (1 - alpha) * result[-1])
    return result


def indicators(rows):
    close = [float(r[4]) for r in rows]
    high = [float(r[2]) for r in rows]
    low = [float(r[3]) for r in rows]
    fast, slow = ema(close, 12), ema(close, 26)
    dif = [a - b for a, b in zip(fast, slow)]
    dea = ema(dif, 9)
    k, d = 50.0, 50.0
    for i in range(len(rows)):
        lo = min(low[max(0, i-8):i+1])
        hi = max(high[max(0, i-8):i+1])
        rsv = (close[i] - lo) / (hi - lo) * 100 if hi > lo else 50.0
        k = (2*k + rsv) / 3
        d = (2*d + k) / 3
    return {
        'last_closed_candle_utc': datetime.fromtimestamp(int(rows[-1][0])/1000, timezone.utc).isoformat(),
        'close': close[-1], 'high': high[-1], 'low': low[-1],
        'ema7': round(ema(close, 7)[-1], 4),
        'ema14': round(ema(close, 14)[-1], 4),
        'ema28': round(ema(close, 28)[-1], 4),
        'macd_dif': round(dif[-1], 4),
        'macd_dea': round(dea[-1], 4),
        'macd_histogram_2x': round(2*(dif[-1]-dea[-1]), 4),
        'kdj_k': round(k, 4), 'kdj_d': round(d, 4), 'kdj_j': round(3*k-2*d, 4),
        'recent_20_high': max(high[-20:]), 'recent_20_low': min(low[-20:]),
    }


def main():
    result = {'generated_at_utc': datetime.now(timezone.utc).isoformat(), 'exchange': 'Bybit', 'category': 'linear', 'symbols': {}, 'errors': {}}
    for symbol in SYMBOLS:
        result['symbols'][symbol] = {}
        for label, interval in INTERVALS.items():
            try:
                result['symbols'][symbol][label] = indicators(fetch(symbol, interval))
                print(f'OK {symbol} {label}')
            except Exception as exc:
                result['errors'][f'{symbol}/{label}'] = str(exc)
                print(f'ERROR {symbol} {label}: {exc}')
    os.makedirs('data', exist_ok=True)
    with open('data/latest.json', 'w', encoding='utf-8') as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    if result['errors']:
        raise SystemExit('Some markets failed; inspect data/latest.json and Actions logs')


if __name__ == '__main__':
    main()
