import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import json
import time
warnings.filterwarnings('ignore')

# Initialize Binance exchange
exchange = ccxt.binance({'enableRateLimit': True})

# Fetch 1 year of 15m data
end_time = int(datetime.now().timestamp() * 1000)
start_time = int((datetime.now() - timedelta(days=365)).timestamp() * 1000)

all_ohlcv = []
current_start = start_time
limit = 1000

print("Fetching BTC 15m data from Binance...")
while current_start < end_time:
    try:
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', '15m', since=current_start, limit=limit)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        current_start = ohlcv[-1][0] + 15 * 60 * 1000
        print(f"Fetched {len(all_ohlcv)} candles, latest: {datetime.fromtimestamp(ohlcv[-1][0]/1000)}")
        time.sleep(0.1)  # Rate limit
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)

if not all_ohlcv:
    print("No data fetched!")
    exit(1)

# Create DataFrame
btc = pd.DataFrame(all_ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
btc['timestamp'] = pd.to_datetime(btc['timestamp'], unit='ms')
btc.set_index('timestamp', inplace=True)
btc = btc[btc.index <= pd.Timestamp.now()]  # Remove any future candles
btc = btc.drop_duplicates().sort_index()

print(f"\nData shape: {btc.shape}")
print(f"Date range: {btc.index[0]} to {btc.index[-1]}")

# Calculate candle properties
btc['body'] = abs(btc['Close'] - btc['Open'])
btc['range'] = btc['High'] - btc['Low']
btc['upper_wick'] = btc['High'] - btc[['Open', 'Close']].max(axis=1)
btc['lower_wick'] = btc[['Open', 'Close']].min(axis=1) - btc['Low']
btc['body_ratio'] = btc['body'] / btc['range'].replace(0, np.nan)
btc['is_bullish'] = btc['Close'] > btc['Open']
btc['is_bearish'] = btc['Close'] < btc['Open']

# Engulfing patterns (strict)
btc['bullish_engulfing'] = (
    (btc['is_bearish'].shift(1)) & 
    (btc['is_bullish']) &
    (btc['Open'] < btc['Close'].shift(1)) &
    (btc['Close'] > btc['Open'].shift(1)) &
    (btc['body'] > btc['body'].shift(1))
)

btc['bearish_engulfing'] = (
    (btc['is_bullish'].shift(1)) & 
    (btc['is_bearish']) &
    (btc['Open'] > btc['Close'].shift(1)) &
    (btc['Close'] < btc['Open'].shift(1)) &
    (btc['body'] > btc['body'].shift(1))
)

# Pinbar detection with thresholds
def detect_pinbar(row, threshold):
    """Detect pinbar with given body_ratio threshold"""
    if pd.isna(row['body_ratio']) or row['body_ratio'] > threshold:
        return 0
    if row['is_bullish']:
        # Bullish pinbar: long lower wick, small upper wick
        return 1 if (row['lower_wick'] > row['body'] * 2) and (row['upper_wick'] < row['body'] * 0.5) else 0
    else:
        # Bearish pinbar: long upper wick, small lower wick
        return 1 if (row['upper_wick'] > row['body'] * 2) and (row['lower_wick'] < row['body'] * 0.5) else 0

for thr in [0.4, 0.5, 0.6]:
    btc[f'pinbar_{thr}'] = btc.apply(lambda r: detect_pinbar(r, thr), axis=1)

# Inside bar detection
btc['inside_bar'] = (
    (btc['High'] < btc['High'].shift(1)) & 
    (btc['Low'] > btc['Low'].shift(1))
)

# Inside bar break modes
btc['inside_break_mid'] = (
    btc['inside_bar'].shift(1) & 
    ((btc['Close'] > (btc['High'].shift(1) + btc['Low'].shift(1)) / 2) | 
     (btc['Close'] < (btc['High'].shift(1) + btc['Low'].shift(1)) / 2))
)

btc['inside_break_color'] = (
    btc['inside_bar'].shift(1) & 
    ((btc['is_bullish'] & (btc['Close'].shift(1) < btc['Open'].shift(1))) | 
     (btc['is_bearish'] & (btc['Close'].shift(1) > btc['Open'].shift(1))))
)

# Forward returns for 15m and 30m
btc['ret_15m'] = btc['Close'].shift(-1) / btc['Close'] - 1
btc['ret_30m'] = btc['Close'].shift(-2) / btc['Close'] - 1

# Wilson score calculation
def wilson_score(wins, total, z=1.96):
    if total == 0:
        return 0
    p = wins / total
    denominator = 1 + z**2 / total
    centre = p + z**2 / (2 * total)
    half = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2))
    return (centre - half) / denominator

# Split IS/OOS (70/30)
split_idx = int(len(btc) * 0.7)
is_data = btc.iloc[:split_idx].copy()
oos_data = btc.iloc[split_idx:].copy()

print(f"\nIS: {len(is_data)} bars, OOS: {len(oos_data)} bars")

# Strategy definitions
strategies = []

# 1. Engulfing strict
for direction in ['bullish_engulfing', 'bearish_engulfing']:
    for exp, payout in [(1, 0.87), (2, 0.90)]:
        ret_col = f'ret_{exp*15}m'
        for name, data in [('IS', is_data), ('OOS', oos_data)]:
            signals = data[data[direction]]
            if len(signals) > 10:
                wins = (signals[ret_col] > 0).sum() if 'bullish' in direction else (signals[ret_col] < 0).sum()
                total = len(signals)
                ws = wilson_score(wins, total)
                strategies.append({
                    'pattern': 'engulfing_strict',
                    'direction': direction,
                    'expiration': f'{exp*15}m',
                    'payout': payout,
                    'sample': name,
                    'trades': total,
                    'wins': int(wins),
                    'winrate': wins/total,
                    'wilson': ws,
                    'expectancy': (wins/total)*payout - (1-wins/total)
                })

# 2. Pinbar confirm with thresholds
for thr in [0.4, 0.5, 0.6]:
    for exp, payout in [(1, 0.87), (2, 0.90)]:
        ret_col = f'ret_{exp*15}m'
        for name, data in [('IS', is_data), ('OOS', oos_data)]:
            # Bullish pinbar -> long
            signals_long = data[(data[f'pinbar_{thr}'] == 1) & (data['is_bullish'])]
            if len(signals_long) > 10:
                wins = (signals_long[ret_col] > 0).sum()
                total = len(signals_long)
                ws = wilson_score(wins, total)
                strategies.append({
                    'pattern': f'pinbar_thr{thr}',
                    'direction': 'bullish',
                    'expiration': f'{exp*15}m',
                    'payout': payout,
                    'sample': name,
                    'trades': total,
                    'wins': int(wins),
                    'winrate': wins/total,
                    'wilson': ws,
                    'expectancy': (wins/total)*payout - (1-wins/total)
                })
            
            # Bearish pinbar -> short
            signals_short = data[(data[f'pinbar_{thr}'] == 1) & (data['is_bearish'])]
            if len(signals_short) > 10:
                wins = (signals_short[ret_col] < 0).sum()
                total = len(signals_short)
                ws = wilson_score(wins, total)
                strategies.append({
                    'pattern': f'pinbar_thr{thr}',
                    'direction': 'bearish',
                    'expiration': f'{exp*15}m',
                    'payout': payout,
                    'sample': name,
                    'trades': total,
                    'wins': int(wins),
                    'winrate': wins/total,
                    'wilson': ws,
                    'expectancy': (wins/total)*payout - (1-wins/total)
                })

# 3. Inside bar break modes
for mode in ['inside_break_mid', 'inside_break_color']:
    for exp, payout in [(1, 0.87), (2, 0.90)]:
        ret_col = f'ret_{exp*15}m'
        for name, data in [('IS', is_data), ('OOS', oos_data)]:
            signals = data[data[mode]]
            if len(signals) > 10:
                # Determine direction from break
                if mode == 'inside_break_mid':
                    mid = (signals['High'].shift(1) + signals['Low'].shift(1)) / 2
                    longs = signals[signals['Close'] > mid]
                    shorts = signals[signals['Close'] < mid]
                else:
                    longs = signals[signals['is_bullish']]
                    shorts = signals[signals['is_bearish']]
                
                for direction_name, dir_signals in [('long', longs), ('short', shorts)]:
                    if len(dir_signals) > 10:
                        wins = (dir_signals[ret_col] > 0).sum() if direction_name == 'long' else (dir_signals[ret_col] < 0).sum()
                        total = len(dir_signals)
                        ws = wilson_score(wins, total)
                        strategies.append({
                            'pattern': f'inside_break_{mode.split("_")[-1]}',
                            'direction': direction_name,
                            'expiration': f'{exp*15}m',
                            'payout': payout,
                            'sample': name,
                            'trades': total,
                            'wins': int(wins),
                            'winrate': wins/total,
                            'wilson': ws,
                            'expectancy': (wins/total)*payout - (1-wins/total)
                        })

# Convert to DataFrame and sort
df = pd.DataFrame(strategies)
df = df.sort_values(['sample', 'wilson'], ascending=[True, False])

# Top results by sample
print("\n=== TOP IS STRATEGIES (Wilson Score) ===")
top_is = df[df['sample'] == 'IS'].head(20)
print(top_is[['pattern', 'direction', 'expiration', 'payout', 'trades', 'winrate', 'wilson', 'expectancy']].to_string(index=False, float_format=lambda x: f'{x:.4f}'))

print("\n=== TOP OOS STRATEGIES (Wilson Score) ===")
top_oos = df[df['sample'] == 'OOS'].head(20)
print(top_oos[['pattern', 'direction', 'expiration', 'payout', 'trades', 'winrate', 'wilson', 'expectancy']].to_string(index=False, float_format=lambda x: f'{x:.4f}'))

# Save detailed results
df.to_csv('btc_m15_strategies.csv', index=False)

# Summary: Best IS -> OOS persistence
print("\n=== IS/OOS PERSISTENCE (strategies appearing in both top 10) ===")
is_top10 = set(df[df['sample']=='IS'].head(10).apply(lambda r: f"{r['pattern']}_{r['direction']}_{r['expiration']}", axis=1))
oos_top10 = set(df[df['sample']=='OOS'].head(10).apply(lambda r: f"{r['pattern']}_{r['direction']}_{r['expiration']}", axis=1))
persistent = is_top10 & oos_top10
for p in sorted(persistent):
    is_row = df[(df['sample']=='IS') & (df.apply(lambda r: f"{r['pattern']}_{r['direction']}_{r['expiration']}", axis=1) == p)].iloc[0]
    oos_row = df[(df['sample']=='OOS') & (df.apply(lambda r: f"{r['pattern']}_{r['direction']}_{r['expiration']}", axis=1) == p)].iloc[0]
    print(f"{p}: IS Wilson={is_row['wilson']:.4f} WR={is_row['winrate']:.2%} n={is_row['trades']} | OOS Wilson={oos_row['wilson']:.4f} WR={oos_row['winrate']:.2%} n={oos_row['trades']}")

# Also show all strategies with positive expectancy in both IS and OOS
print("\n=== STRATEGIES WITH POSITIVE EXPECTANCY IN BOTH IS & OOS ===")
positive_both = []
for pattern in df['pattern'].unique():
    for direction in df['direction'].unique():
        for exp in df['expiration'].unique():
            is_row = df[(df['sample']=='IS') & (df['pattern']==pattern) & (df['direction']==direction) & (df['expiration']==exp)]
            oos_row = df[(df['sample']=='OOS') & (df['pattern']==pattern) & (df['direction']==direction) & (df['expiration']==exp)]
            if len(is_row) > 0 and len(oos_row) > 0:
                is_exp = is_row.iloc[0]['expectancy']
                oos_exp = oos_row.iloc[0]['expectancy']
                if is_exp > 0 and oos_exp > 0:
                    positive_both.append({
                        'pattern': pattern, 'direction': direction, 'expiration': exp,
                        'is_wilson': is_row.iloc[0]['wilson'], 'is_wr': is_row.iloc[0]['winrate'],
                        'oos_wilson': oos_row.iloc[0]['wilson'], 'oos_wr': oos_row.iloc[0]['winrate'],
                        'is_exp': is_exp, 'oos_exp': oos_exp
                    })

if positive_both:
    pos_df = pd.DataFrame(positive_both).sort_values('oos_wilson', ascending=False)
    print(pos_df.to_string(index=False, float_format=lambda x: f'{x:.4f}'))
else:
    print("No strategies with positive expectancy in both IS and OOS")

# Output JSON for easy reading
result = {
    'top_is': top_is.head(10).to_dict('records'),
    'top_oos': top_oos.head(10).to_dict('records'),
    'persistent': list(persistent),
    'positive_both': positive_both
}
with open('btc_m15_results.json', 'w') as f:
    json.dump(result, f, indent=2, default=str)

print("\nResults saved to btc_m15_strategies.csv and btc_m15_results.json")