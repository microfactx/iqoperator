"""Hunter BTC MTF: donchian_fade n=20 M15 + filtro tendência H1 EMA50
Expirações 15m(1)/30m(2)/60m(4)/120m(8) M15
Payout 0.87 BE 53.48% / 0.90 BE 52.63%
Dados: 35000 M15 BTCUSDT 1y. IS 70% / OOS 30%
Retorna IS/OOS Wilson para ambos payouts.
"""
import csv
import math
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kelly import kelly_fraction_stake

DATA_M15 = "data/BTCUSDT_M15_1y.csv"
PAYOUTS = (0.87, 0.90)
EXPIRIES = (1, 2, 4, 8)  # M15 bars
N_DONCHIAN = 20
EMA_PERIOD = 50
IS_SPLIT = 0.70


def load_m15(path):
    t, o, h, l, c = [], [], [], [], []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                v = int(float(r["time"]))
            except ValueError:
                continue
            if v >= 10**15:
                v //= 1000
            elif v < 10_000_000_000:
                v *= 1000
            t.append(v)
            o.append(float(r["open"]))
            h.append(float(r["high"]))
            l.append(float(r["low"]))
            c.append(float(r["close"]))
    return {"t": t, "o": o, "h": h, "l": l, "c": c}


def ema_list(xs, period):
    """EMA com span=period"""
    out = [None] * len(xs)
    if len(xs) < period:
        return out
    k = 2.0 / (period + 1)
    sma = sum(xs[:period]) / period
    out[period - 1] = sma
    for i in range(period, len(xs)):
        out[i] = xs[i] * k + out[i - 1] * (1 - k)
    return out


def resample_m15_to_h1(m15):
    """Resample M15 OHLCV to H1 (4 bars per hour)"""
    t, o, h, l, c = m15["t"], m15["o"], m15["h"], m15["l"], m15["c"]
    n = len(t)
    h1_t, h1_o, h1_h, h1_l, h1_c = [], [], [], [], []
    
    for i in range(0, n, 4):
        if i + 3 >= n:
            break
        # H1 timestamp = first M15 bar timestamp
        h1_t.append(t[i])
        h1_o.append(o[i])
        h1_h.append(max(h[i:i+4]))
        h1_l.append(min(l[i:i+4]))
        h1_c.append(c[i+3])
    
    return {"t": h1_t, "o": h1_o, "h": h1_h, "l": h1_l, "c": h1_c}


def donchian_fade_signals(m15, n):
    """Fade do rompimento Donchian: toca banda e volta (oposto do breakout)"""
    h, l, c = m15["h"], m15["l"], m15["c"]
    sig = []
    for i in range(n, len(c) - 1):
        hi = max(h[i - n:i])
        lo = min(l[i - n:i])
        if c[i] > hi:
            sig.append((i, "put"))   # fade up -> put
        elif c[i] < lo:
            sig.append((i, "call"))  # fade down -> call
    return sig


def wilson_lower(wins, n, z=1.96):
    if not n:
        return 0.0
    p = wins / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - m) / d


def run_backtest(signals, closes, balance, expiry, payout):
    """Backtest com Kelly fraction"""
    bal, peak, max_dd = balance, balance, 0.0
    hist = deque(maxlen=50)
    wins = losses = 0
    for i, side in signals:
        if i + expiry >= len(closes):
            continue
        n_hist = len(hist)
        p = (0.58 * 20 + sum(1 for w in hist if w)) / (20 + n_hist) if n_hist else 0.58
        stake, _ = kelly_fraction_stake(bal, payout, p, 0.25, 0.02, 1.0)
        entry, nxt = closes[i], closes[i + expiry]
        if nxt == entry:
            continue
        won = (side == "call") == (nxt > entry)
        bal += stake * payout if won else -stake
        hist.append(won)
        wins += 1 if won else 0
        losses += 0 if won else 1
        peak = max(peak, bal)
        max_dd = max(max_dd, (peak - bal) / peak if peak else 0)
    tot = wins + losses
    return {"trades": tot, "wins": wins, "wr": wins / tot if tot else 0.0,
            "profit": round(bal - balance, 2), "max_dd": round(max_dd, 4)}


def align_h1_to_m15(h1_ema, h1_t, m15_t):
    """Alinha EMA H1 para cada barra M15 (last closed H1 bar)"""
    # h1_t são timestamps de abertura das barras H1
    # H1 bar closes at h1_t + 3600000ms
    h1_close_times = [x + 3_600_000 for x in h1_t]
    aligned = []
    for mt in m15_t:
        entry_close = mt + 900_000  # M15 close time
        # find last H1 bar fully closed before entry
        idx = -1
        for j, h1ct in enumerate(h1_close_times):
            if h1ct <= entry_close:
                idx = j
            else:
                break
        if idx >= 0 and h1_ema[idx] is not None:
            aligned.append(h1_ema[idx])
        else:
            aligned.append(None)
    return aligned


def main():
    # Load M15 data
    m15 = load_m15(DATA_M15)
    print(f"[DATA] M15: {len(m15['c'])} candles")
    
    # Resample to H1
    h1 = resample_m15_to_h1(m15)
    print(f"[DATA] H1:  {len(h1['c'])} candles (resampled from M15)")
    
    # Compute H1 EMA50
    h1_ema = ema_list(h1["c"], EMA_PERIOD)
    
    # Align H1 EMA to M15 timestamps
    h1_ema_m15 = align_h1_to_m15(h1_ema, h1["t"], m15["t"])
    
    # Generate donchian fade signals on M15
    all_signals = donchian_fade_signals(m15, N_DONCHIAN)
    print(f"[SIGNALS] Donchian fade n={N_DONCHIAN}: {len(all_signals)} raw signals")
    
    # Apply H1 EMA50 trend filter
    filtered_signals = []
    for i, side in all_signals:
        ema = h1_ema_m15[i]
        if ema is None:
            continue
        close = m15["c"][i]
        # Trend filter: call only if price > EMA (uptrend), put only if price < EMA (downtrend)
        if side == "call" and close > ema:
            filtered_signals.append((i, side))
        elif side == "put" and close < ema:
            filtered_signals.append((i, side))
    
    print(f"[SIGNALS] After H1 EMA{EMA_PERIOD} trend filter: {len(filtered_signals)} signals")
    
    # IS/OOS split
    n_total = len(m15["c"])
    cut = int(n_total * IS_SPLIT)
    print(f"[SPLIT] IS: 0..{cut-1} ({cut} bars, {cut/n_total:.0%}) | OOS: {cut}..{n_total-1} ({n_total-cut} bars, {(n_total-cut)/n_total:.0%})")
    
    sig_is = [(i, s) for i, s in filtered_signals if i < cut]
    sig_oos = [(i, s) for i, s in filtered_signals if i >= cut]
    print(f"[SPLIT] IS signals: {len(sig_is)} | OOS signals: {len(sig_oos)}")
    
    closes = m15["c"]
    
    # Header
    print(f"\n{'='*120}")
    print(f"HUNTER BTC MTF: Donchian Fade n={N_DONCHIAN} M15 + H1 EMA{EMA_PERIOD} Trend Filter")
    print(f"Data: {len(m15['c'])} M15 candles | IS 70% / OOS 30% | Kelly(0.25, 2%, 1$) | Wilson 95%")
    print(f"{'='*120}")
    
    for payout in PAYOUTS:
        BE = 1 / (1 + payout)
        print(f"\n{'='*120}")
        print(f"PAYOUT {payout:.2f}  BE {BE:.2%}  (Wilson 95% lower bound)")
        print(f"{'='*120}")
        
        rows = []
        for exp in EXPIRIES:
            exp_min = exp * 15
            
            r_is = run_backtest(sig_is, closes, 1000.0, exp, payout)
            r_oos = run_backtest(sig_oos, closes, 1000.0, exp, payout)
            
            w_is = wilson_lower(r_is["wins"], r_is["trades"])
            w_oos = wilson_lower(r_oos["wins"], r_oos["trades"])
            
            checks = (r_oos["trades"] >= 50, w_oos > BE, r_oos["profit"] > 0)
            ok_oos = all(checks)
            
            rows.append({
                "exp": exp, "exp_m": exp_min,
                "r_is": r_is, "r_oos": r_oos,
                "w_is": w_is, "w_oos": w_oos,
                "ok_oos": ok_oos, "BE": BE
            })
        
        # Sort by IS profit desc
        rows_sorted = sorted(rows, key=lambda x: x["r_is"]["profit"], reverse=True)
        
        print(f"\n[RESULTS by IS profit] payout={payout:.2f}")
        header = "{:<3} {:<18} {:>10} {:>6} {:>7} {:>9} {:>11} {:>6} {:>7} {:>10} {:>8} {}"
        print(header.format("#", "Config", "IS Profit", "IS n", "IS WR", "IS Wilson", "OOS Profit", "OOS n", "OOS WR", "OOS Wilson", "vs BE", "Verdict"))
        print("-" * 110)
        for idx, r in enumerate(rows_sorted, 1):
            cfg = f"exp={r['exp_m']}m"
            is_ = r["r_is"]; oos = r["r_oos"]
            gap = r["w_oos"] - r["BE"]
            print(header.format(idx, cfg, f"{is_['profit']:+.2f}", is_["trades"], f"{is_['wr']:.2%}", f"{r['w_is']:.2%}",
                              f"{oos['profit']:+.2f}", oos["trades"], f"{oos['wr']:.2%}", f"{r['w_oos']:.2%}",
                              f"{gap:+.2%}", "PASS" if r["ok_oos"] else "FAIL"))
        
        # Sort by OOS Wilson desc
        rows_wilson = sorted(rows, key=lambda x: x["w_oos"], reverse=True)
        
        print(f"\n[RESULTS by OOS Wilson] payout={payout:.2f}")
        header2 = "{:<3} {:<18} {:>11} {:>6} {:>7} {:>10} {:>8} {:>10} {:>9} {}"
        print(header2.format("#", "Config", "OOS Wilson", "OOS n", "OOS WR", "OOS Profit", "vs BE", "IS Profit", "IS Wilson", "Verdict"))
        print("-" * 100)
        for idx, r in enumerate(rows_wilson, 1):
            cfg = f"exp={r['exp_m']}m"
            print(header2.format(idx, cfg, f"{r['w_oos']:.2%}", r["r_oos"]["trades"], f"{r['r_oos']['wr']:.2%}",
                                 f"{r['r_oos']['profit']:+.2f}", f"{r['w_oos']-r['BE']:+.2%}",
                                 f"{r['r_is']['profit']:+.2f}", f"{r['w_is']:.2%}",
                                 "PASS" if r["ok_oos"] else "FAIL"))
        
        # Summary
        passes = sum(1 for r in rows if r["ok_oos"])
        print(f"\n[SUMMARY payout={payout:.2f}] PASS OOS (trades>=50 & Wilson>BE & profit>0): {passes}/{len(rows)}")
        if passes == 0:
            best = max(rows, key=lambda x: x["w_oos"])
            print(f"  -> BEST OOS Wilson: exp={best['exp_m']}m | Wilson {best['w_oos']:.2%} vs BE {best['BE']:.2%} gap {best['w_oos']-best['BE']:+.2%} | n={best['r_oos']['trades']} WR={best['r_oos']['wr']:.2%} profit={best['r_oos']['profit']:+.2f}")
            print(f"  -> IS Wilson: {best['w_is']:.2%} | IS profit: {best['r_is']['profit']:+.2f}")
            print(f"  -> VERDICT: FAIL - No config passes OOS Wilson > BE")
        else:
            print(f"  -> VERDICT: PASS - {passes} config(s) pass OOS criteria")
            for r in rows:
                if r["ok_oos"]:
                    print(f"     PASS: exp={r['exp_m']}m | OOS Wilson {r['w_oos']:.2%} > BE {r['BE']:.2%} | n={r['r_oos']['trades']} WR={r['r_oos']['wr']:.2%} profit={r['r_oos']['profit']:+.2f}")

    print(f"\n{'='*120}")
    print("DONE")
    print(f"{'='*120}")


if __name__ == "__main__":
    main()