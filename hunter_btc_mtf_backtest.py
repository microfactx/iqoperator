import pandas as pd
import numpy as np
from scipy import stats
import ccxt
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# HUNTER BTC MTF STRATEGY BACKTEST
# Donchian Fade n=20 M15 + H1 EMA50 Trend Filter
# Expirations: 15m/30m/60m/120m | Payout: 0.87/0.90
# Data: 35000 M15 BTCUSDT candles
# Output: IS/OOS Wilson Score Intervals
# ============================================================

def fetch_btc_data(limit=35000):
    """Fetch BTCUSDT M15 data from Binance"""
    exchange = ccxt.binance({'enableRateLimit': True})
    all_ohlcv = []
    since = None
    
    print(f"Fetching {limit} M15 candles from Binance...")
    
    while len(all_ohlcv) < limit:
        fetch_limit = min(1000, limit - len(all_ohlcv))
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', '15m', since=since, limit=fetch_limit)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        since = ohlcv[-1][0] + 1
        print(f"  Fetched {len(all_ohlcv)} candles...")
        if len(ohlcv) < fetch_limit:
            break
    
    df = pd.DataFrame(all_ohlcv[:limit], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    # If we didn't get enough, try fetching older data by going backwards
    if len(df) < limit:
        print(f"Only got {len(df)} candles, attempting to fetch more historical data...")
        # Fetch older data by using end parameter
        end_time = df.index[0].timestamp() * 1000
        while len(all_ohlcv) < limit:
            fetch_limit = min(1000, limit - len(all_ohlcv))
            ohlcv = exchange.fetch_ohlcv('BTC/USDT', '15m', since=None, limit=fetch_limit, params={'endTime': int(end_time)})
            if not ohlcv:
                break
            all_ohlcv = ohlcv + all_ohlcv  # prepend older data
            end_time = ohlcv[0][0] - 1
            print(f"  Fetched {len(all_ohlcv)} total candles...")
            if len(ohlcv) < fetch_limit:
                break
        
        df = pd.DataFrame(all_ohlcv[:limit], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
    
    return df

def resample_to_h1(df_m15):
    """Resample M15 to H1 for EMA50 trend filter"""
    return df_m15.resample('1h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

def calculate_indicators(df_m15, df_h1):
    """Calculate Donchian channels (M15) and EMA50 (H1)"""
    # M15 Donchian Channel n=20
    df_m15['donchian_high'] = df_m15['high'].rolling(20).max()
    df_m15['donchian_low'] = df_m15['low'].rolling(20).min()
    df_m15['donchian_mid'] = (df_m15['donchian_high'] + df_m15['donchian_low']) / 2
    
    # H1 EMA50
    df_h1['ema50'] = df_h1['close'].ewm(span=50, adjust=False).mean()
    
    # Align H1 EMA50 to M15 (forward fill)
    df_m15['h1_ema50'] = df_h1['ema50'].reindex(df_m15.index, method='ffill')
    
    # Trend filter: price > EMA50 = uptrend, price < EMA50 = downtrend
    df_m15['trend_up'] = df_m15['close'] > df_m15['h1_ema50']
    df_m15['trend_down'] = df_m15['close'] < df_m15['h1_ema50']
    
    return df_m15

def generate_signals(df):
    """Generate Donchian fade signals with trend filter"""
    df = df.copy()
    
    # Fade signals: 
    # - Short when price touches upper Donchian in DOWNTREND (fade the breakout)
    # - Long when price touches lower Donchian in UPTREND (fade the breakdown)
    
    # Long signal: close <= donchian_low AND trend_up
    df['signal_long'] = (df['close'] <= df['donchian_low']) & df['trend_up']
    
    # Short signal: close >= donchian_high AND trend_down
    df['signal_short'] = (df['close'] >= df['donchian_high']) & df['trend_down']
    
    # Entry price at next open
    df['entry_price_long'] = df['open'].shift(-1)
    df['entry_price_short'] = df['open'].shift(-1)
    
    return df

def simulate_expirations(df, expirations_minutes=[15, 30, 60, 120], payouts=[0.87, 0.90]):
    """
    Simulate binary options expirations at different horizons.
    For each signal, check outcome at each expiration.
    """
    results = []
    m15_bars_per_exp = {exp: exp // 15 for exp in expirations_minutes}
    
    # Get signal indices
    long_indices = df.index[df['signal_long']].tolist()
    short_indices = df.index[df['signal_short']].tolist()
    
    # Convert index to integer positions for fast lookup
    idx_to_pos = {idx: pos for pos, idx in enumerate(df.index)}
    
    for idx in long_indices:
        pos = idx_to_pos[idx]
        entry = df.iloc[pos]['entry_price_long']
        if pd.isna(entry):
            continue
        for exp_min, bars in m15_bars_per_exp.items():
            future_pos = pos + bars
            if future_pos < len(df):
                exit_price = df.iloc[future_pos]['close']
                won = exit_price > entry
                for payout in payouts:
                    pnl = payout if won else -1.0
                    results.append({
                        'timestamp': idx,
                        'direction': 'long',
                        'expiration': exp_min,
                        'payout': payout,
                        'entry': entry,
                        'exit': exit_price,
                        'won': won,
                        'pnl': pnl
                    })
    
    for idx in short_indices:
        pos = idx_to_pos[idx]
        entry = df.iloc[pos]['entry_price_short']
        if pd.isna(entry):
            continue
        for exp_min, bars in m15_bars_per_exp.items():
            future_pos = pos + bars
            if future_pos < len(df):
                exit_price = df.iloc[future_pos]['close']
                won = exit_price < entry
                for payout in payouts:
                    pnl = payout if won else -1.0
                    results.append({
                        'timestamp': idx,
                        'direction': 'short',
                        'expiration': exp_min,
                        'payout': payout,
                        'entry': entry,
                        'exit': exit_price,
                        'won': won,
                        'pnl': pnl
                    })
    
    return pd.DataFrame(results)

def wilson_score_interval(wins, total, confidence=0.95):
    """Calculate Wilson score interval for binomial proportion"""
    if total == 0:
        return (0, 0, 0)
    
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    p = wins / total
    
    denominator = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denominator
    half_width = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
    
    lower = max(0, centre - half_width)
    upper = min(1, centre + half_width)
    
    return (p, lower, upper)

def analyze_is_oos(trades_df, split_ratio=0.7):
    """Split trades into IS/OOS and calculate Wilson intervals"""
    trades_df = trades_df.sort_values('timestamp').reset_index(drop=True)
    split_idx = int(len(trades_df) * split_ratio)
    
    is_trades = trades_df.iloc[:split_idx]
    oos_trades = trades_df.iloc[split_idx:]
    
    def calc_stats(sub_df, label):
        if len(sub_df) == 0:
            return None
        
        stats_by_config = {}
        for (exp, payout), group in sub_df.groupby(['expiration', 'payout']):
            total = len(group)
            wins = group['won'].sum()
            win_rate, lower, upper = wilson_score_interval(wins, total)
            avg_pnl = group['pnl'].mean()
            total_pnl = group['pnl'].sum()
            
            stats_by_config[(exp, payout)] = {
                'label': label,
                'expiration': exp,
                'payout': payout,
                'trades': total,
                'wins': int(wins),
                'losses': total - int(wins),
                'win_rate': win_rate,
                'wilson_lower': lower,
                'wilson_upper': upper,
                'avg_pnl': avg_pnl,
                'total_pnl': total_pnl,
                'expectancy': avg_pnl
            }
        return stats_by_config
    
    is_stats = calc_stats(is_trades, 'IS')
    oos_stats = calc_stats(oos_trades, 'OOS')
    
    return is_stats, oos_stats, is_trades, oos_trades

def print_results(is_stats, oos_stats):
    """Print formatted IS/OOS results with Wilson intervals"""
    print("\n" + "="*120)
    print("HUNTER BTC MTF - DONCHIAN FADE n=20 M15 + H1 EMA50 TREND FILTER")
    print("IS/OOS Wilson Score Intervals (95% confidence)")
    print("="*120)
    
    header = f"{'Set':<4} {'Exp':>4} {'Payout':>6} {'Trades':>7} {'Wins':>5} {'Losses':>7} {'Win%':>8} {'Wilson 95% CI':>22} {'Avg PnL':>9} {'Total PnL':>10} {'Expectancy':>10}"
    print(header)
    print("-"*120)
    
    all_configs = set()
    if is_stats:
        all_configs.update(is_stats.keys())
    if oos_stats:
        all_configs.update(oos_stats.keys())
    
    for config in sorted(all_configs):
        exp, payout = config
        for stats_dict, label in [(is_stats, 'IS'), (oos_stats, 'OOS')]:
            if stats_dict and config in stats_dict:
                s = stats_dict[config]
                ci_str = f"[{s['wilson_lower']:.3f}, {s['wilson_upper']:.3f}]"
                print(f"{s['label']:<4} {s['expiration']:>4} {s['payout']:>6.2f} {s['trades']:>7} {s['wins']:>5} {s['losses']:>7} {s['win_rate']:>7.2%} {ci_str:>22} {s['avg_pnl']:>9.4f} {s['total_pnl']:>10.2f} {s['expectancy']:>10.4f}")
    
    print("-"*120)
    
    # Summary
    print("\nSUMMARY:")
    for stats_dict, label in [(is_stats, 'IN-SAMPLE'), (oos_stats, 'OUT-OF-SAMPLE')]:
        if not stats_dict:
            continue
        total_trades = sum(s['trades'] for s in stats_dict.values())
        total_wins = sum(s['wins'] for s in stats_dict.values())
        total_pnl = sum(s['total_pnl'] for s in stats_dict.values())
        overall_wr, lwr, upr = wilson_score_interval(total_wins, total_trades)
        print(f"  {label}: {total_trades} trades | WR: {overall_wr:.2%} [{lwr:.3f}, {upr:.3f}] | Total PnL: {total_pnl:.2f} | Expectancy: {total_pnl/total_trades:.4f}")

def main():
    # Fetch data
    df_m15 = fetch_btc_data(35000)
    print(f"\nData range: {df_m15.index[0]} to {df_m15.index[-1]}")
    print(f"Total M15 candles: {len(df_m15)}")
    
    # Resample to H1
    df_h1 = resample_to_h1(df_m15)
    print(f"H1 candles: {len(df_h1)}")
    
    # Calculate indicators
    df_m15 = calculate_indicators(df_m15, df_h1)
    
    # Generate signals
    df_m15 = generate_signals(df_m15)
    
    long_signals = df_m15['signal_long'].sum()
    short_signals = df_m15['signal_short'].sum()
    print(f"\nSignals generated: Long={long_signals}, Short={short_signals}, Total={long_signals+short_signals}")
    
    # Simulate expirations
    trades_df = simulate_expirations(df_m15)
    print(f"Total trade simulations: {len(trades_df)}")
    
    # IS/OOS Analysis
    is_stats, oos_stats, is_trades, oos_trades = analyze_is_oos(trades_df, split_ratio=0.7)
    
    # Print results
    print_results(is_stats, oos_stats)
    
    # Save detailed results
    trades_df.to_csv('hunter_btc_mtf_trades.csv', index=False)
    print("\nDetailed trades saved to hunter_btc_mtf_trades.csv")
    
    return is_stats, oos_stats, trades_df

if __name__ == '__main__':
    is_stats, oos_stats, trades_df = main()