"""Hunter EURUSD H1 (agregado M15 histdata ~10000 H1): 
Bollinger p=20,50 mult=1.5,2.0 exp=60/120m
Donchian n=20,40,60 exp=60/120m
RSI per=7,14,21 bandas=70/30,75/25 exp=60/120m
Payout 0.90 BE 52.63%. IS 70% OOS 30%. Retorne top IS/OOS.
"""
import csv
import math
import sys
import os
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kelly import kelly_fraction_stake


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


def resample_m15_to_h1(m15):
    """Resample M15 OHLC to H1 (4 bars per hour)"""
    t, o, h, l, c = m15["t"], m15["o"], m15["h"], m15["l"], m15["c"]
    n = len(t)
    h1_t, h1_o, h1_h, h1_l, h1_c = [], [], [], [], []

    for i in range(0, n, 4):
        if i + 3 >= n:
            break
        h1_t.append(t[i])
        h1_o.append(o[i])
        h1_h.append(max(h[i:i+4]))
        h1_l.append(min(l[i:i+4]))
        h1_c.append(c[i+3])

    return {"t": h1_t, "o": h1_o, "h": h1_h, "l": h1_l, "c": h1_c}


def sma(xs, p):
    out = [None] * len(xs)
    s = 0.0
    for i, x in enumerate(xs):
        s += x
        if i >= p:
            s -= xs[i - p]
        if i >= p - 1:
            out[i] = s / p
    return out


def stdev(xs, p):
    out = [None] * len(xs)
    for i in range(p - 1, len(xs)):
        w = xs[i - p + 1: i + 1]
        m = sum(w) / p
        out[i] = math.sqrt(sum((x - m) ** 2 for x in w) / p)
    return out


def rsi(xs, p):
    """RSI Wilder's smoothing"""
    if len(xs) < p + 1:
        return [None] * len(xs)
    gains = []
    losses = []
    for i in range(1, len(xs)):
        diff = xs[i] - xs[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    out = [None] * len(xs)
    # First avg gain/loss
    avg_gain = sum(gains[:p]) / p
    avg_loss = sum(losses[:p]) / p
    if avg_loss == 0:
        out[p] = 100.0
    else:
        rs = avg_gain / avg_loss
        out[p] = 100 - 100 / (1 + rs)
    # Wilder's smoothing
    for i in range(p + 1, len(xs)):
        avg_gain = (avg_gain * (p - 1) + gains[i-1]) / p
        avg_loss = (avg_loss * (p - 1) + losses[i-1]) / p
        if avg_loss == 0:
            out[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100 - 100 / (1 + rs)
    return out


# Bollinger mean reversion: price touches band -> expect reversion
def fam_boll(d, p, mult):
    c = d["c"]
    basis, sd = sma(c, p), stdev(c, p)
    sig = []
    for i in range(p, len(c) - 1):
        if basis[i] is None or sd[i] is None:
            continue
        upper = basis[i] + mult * sd[i]
        lower = basis[i] - mult * sd[i]
        if c[i] < lower:
            sig.append((i, "call"))  # oversold -> call
        elif c[i] > upper:
            sig.append((i, "put"))   # overbought -> put
    return sig


# Donchian breakout: price breaks n-period high/low -> follow trend
def fam_donchian(d, n):
    h, l, c = d["h"], d["l"], d["c"]
    sig = []
    for i in range(n, len(c) - 1):
        hi = max(h[i - n: i])
        lo = min(l[i - n: i])
        if c[i] > hi:
            sig.append((i, "call"))  # break up -> call
        elif c[i] < lo:
            sig.append((i, "put"))   # break down -> put
    return sig


# RSI mean reversion: RSI crosses bands -> expect reversion
def fam_rsi(d, period, upper_band, lower_band):
    c = d["c"]
    rsi_vals = rsi(c, period)
    sig = []
    for i in range(period + 1, len(c) - 1):
        if rsi_vals[i] is None or rsi_vals[i-1] is None:
            continue
        prev = rsi_vals[i-1]
        curr = rsi_vals[i]
        # Crossed below lower band -> oversold -> call
        if prev > lower_band and curr <= lower_band:
            sig.append((i, "call"))
        # Crossed above upper band -> overbought -> put
        elif prev < upper_band and curr >= upper_band:
            sig.append((i, "put"))
    return sig


def run(signals, closes, balance, expiry, payout):
    bal, peak, max_dd = balance, balance, 0.0
    hist = deque(maxlen=50)
    wins = losses = 0
    for i, side in signals:
        if i + expiry >= len(closes):
            continue
        n = len(hist)
        p = (0.58 * 20 + sum(1 for w in hist if w)) / (20 + n) if n else 0.58
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
    return {
        "trades": tot,
        "wins": wins,
        "wr": wins / tot if tot else 0.0,
        "profit": round(bal - balance, 2),
        "max_dd": round(max_dd, 4),
    }


def wilson(wins, n, z=1.96):
    if not n:
        return 0.0
    p = wins / n
    d = 1 + z * z / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


def main():
    # Load M15 and resample to H1
    m15 = load_m15("data/EURUSD_M15_histdata.csv")
    h1 = resample_m15_to_h1(m15)
    c = h1["c"]
    n_total = len(c)
    cut = int(n_total * 0.70)
    print(f"[DATA] EURUSD M15->H1: {n_total} H1 bars | IS:0..{cut-1} ({cut}) OOS:{cut}..{n_total-1} ({n_total-cut})")

    PAYOUT = 0.90
    BE = 1 / (1 + PAYOUT)
    print(f"[PAYOUT] {PAYOUT:.2f} BE {BE:.2%}")

    # Parameters
    EXPIRIES_H1 = (4, 8)  # 60m = 4 H1 bars, 120m = 8 H1 bars
    EXPIRY_LABELS = {4: "60m", 8: "120m"}

    rows = []

    # Bollinger: p=20,50 mult=1.5,2.0
    for p in (20, 50):
        for mult in (1.5, 2.0):
            sig_all = fam_boll(h1, p=p, mult=mult)
            sig_is = [(i, s) for i, s in sig_all if i < cut]
            sig_oos = [(i, s) for i, s in sig_all if i >= cut]
            for exp in EXPIRIES_H1:
                r_is = run(sig_is, c, 1000.0, exp, PAYOUT)
                r_oos = run(sig_oos, c, 1000.0, exp, PAYOUT)
                w_is = wilson(r_is["wins"], r_is["trades"])
                w_oos = wilson(r_oos["wins"], r_oos["trades"])
                exp_label = EXPIRY_LABELS[exp]
                checks = (r_oos["trades"] >= 50, w_oos > BE, r_oos["profit"] > 0)
                ok_oos = all(checks)
                rows.append({
                    "type": "boll",
                    "p": p, "mult": mult, "exp": exp, "exp_label": exp_label,
                    "r_is": r_is, "r_oos": r_oos, "w_is": w_is, "w_oos": w_oos,
                    "ok_oos": ok_oos, "BE": BE,
                })

    # Donchian: n=20,40,60
    for n in (20, 40, 60):
        sig_all = fam_donchian(h1, n=n)
        sig_is = [(i, s) for i, s in sig_all if i < cut]
        sig_oos = [(i, s) for i, s in sig_all if i >= cut]
        for exp in EXPIRIES_H1:
            r_is = run(sig_is, c, 1000.0, exp, PAYOUT)
            r_oos = run(sig_oos, c, 1000.0, exp, PAYOUT)
            w_is = wilson(r_is["wins"], r_is["trades"])
            w_oos = wilson(r_oos["wins"], r_oos["trades"])
            exp_label = EXPIRY_LABELS[exp]
            checks = (r_oos["trades"] >= 50, w_oos > BE, r_oos["profit"] > 0)
            ok_oos = all(checks)
            rows.append({
                "type": "donchian",
                "n": n, "exp": exp, "exp_label": exp_label,
                "r_is": r_is, "r_oos": r_oos, "w_is": w_is, "w_oos": w_oos,
                "ok_oos": ok_oos, "BE": BE,
            })

    # RSI: per=7,14,21 bandas=70/30,75/25
    for period in (7, 14, 21):
        for upper, lower in [(70, 30), (75, 25)]:
            sig_all = fam_rsi(h1, period=period, upper_band=upper, lower_band=lower)
            sig_is = [(i, s) for i, s in sig_all if i < cut]
            sig_oos = [(i, s) for i, s in sig_all if i >= cut]
            for exp in EXPIRIES_H1:
                r_is = run(sig_is, c, 1000.0, exp, PAYOUT)
                r_oos = run(sig_oos, c, 1000.0, exp, PAYOUT)
                w_is = wilson(r_is["wins"], r_is["trades"])
                w_oos = wilson(r_oos["wins"], r_oos["trades"])
                exp_label = EXPIRY_LABELS[exp]
                checks = (r_oos["trades"] >= 50, w_oos > BE, r_oos["profit"] > 0)
                ok_oos = all(checks)
                rows.append({
                    "type": "rsi",
                    "period": period, "upper": upper, "lower": lower,
                    "exp": exp, "exp_label": exp_label,
                    "r_is": r_is, "r_oos": r_oos, "w_is": w_is, "w_oos": w_oos,
                    "ok_oos": ok_oos, "BE": BE,
                })

    print(f"\n[CONFIGS TESTED] {len(rows)}")
    print(f"  Bollinger: 2 periods x 2 mults x 2 exp = 8")
    print(f"  Donchian: 3 periods x 2 exp = 6")
    print(f"  RSI: 3 periods x 2 bands x 2 exp = 12")
    print(f"  Total: {8+6+12} = {len(rows)}")

    def fmt_cfg(r):
        if r["type"] == "boll":
            return f"boll p={r['p']} m={r['mult']} exp={r['exp_label']}"
        elif r["type"] == "donchian":
            return f"donchian n={r['n']} exp={r['exp_label']}"
        else:
            return f"rsi per={r['period']} b={r['upper']}/{r['lower']} exp={r['exp_label']}"

    # Top 5 IS by profit
    rows_sorted = sorted(rows, key=lambda x: x["r_is"]["profit"], reverse=True)
    print(f"\n=== TOP 5 IS por LUCRO ===")
    print(f"{'#':<3} {'cfg':<40} {'IS profit':>10} {'IS n':>6} {'IS WR':>7} {'IS Wilson':>10} {'OOS profit':>11} {'OOS n':>6} {'OOS WR':>7} {'OOS Wilson':>11} {'vs BE':>9} {'OOS verdict'}")
    for idx, r in enumerate(rows_sorted[:5], 1):
        cfg = fmt_cfg(r)
        is_ = r["r_is"]; oos = r["r_oos"]
        print(f"{idx:<3} {cfg:<40} {is_['profit']:+10.2f} {is_['trades']:>6} {is_['wr']:>6.2%} {r['w_is']:>9.2%}     {oos['profit']:+11.2f} {oos['trades']:>6} {oos['wr']:>6.2%} {r['w_oos']:>10.2%}     {r['w_oos']-r['BE']:+.2%}   {'PASS' if r['ok_oos'] else 'FAIL'}")

    # Top 5 OOS by Wilson
    rows_oos_wilson = sorted(rows, key=lambda x: x["w_oos"], reverse=True)
    print(f"\n=== TOP 5 OOS por WILSON (95% lower bound) ===")
    print(f"{'#':<3} {'cfg':<40} {'OOS Wilson':>11} {'OOS n':>6} {'OOS WR':>7} {'OOS profit':>11} {'vs BE':>9} {'IS profit':>10} {'IS Wilson':>10} {'OOS verdict'}")
    for idx, r in enumerate(rows_oos_wilson[:5], 1):
        cfg = fmt_cfg(r)
        print(f"{idx:<3} {cfg:<40} {r['w_oos']:>10.2%} {r['r_oos']['trades']:>6} {r['r_oos']['wr']:>6.2%} {r['r_oos']['profit']:+11.2f} {r['w_oos']-r['BE']:+.2%}   {r['r_is']['profit']:+10.2f} {r['w_is']:>9.2%}     {'PASS' if r['ok_oos'] else 'FAIL'}")

    # Top 5 OOS by profit
    rows_oos_profit = sorted(rows, key=lambda x: x["r_oos"]["profit"], reverse=True)
    print(f"\n=== TOP 5 OOS por LUCRO OOS ===")
    print(f"{'#':<3} {'cfg':<40} {'OOS profit':>11} {'OOS n':>6} {'OOS WR':>7} {'OOS Wilson':>11} {'IS profit':>10} {'IS WR':>7}")
    for idx, r in enumerate(rows_oos_profit[:5], 1):
        cfg = fmt_cfg(r)
        print(f"{idx:<3} {cfg:<40} {r['r_oos']['profit']:+11.2f} {r['r_oos']['trades']:>6} {r['r_oos']['wr']:>6.2%} {r['w_oos']:>10.2%}     {r['r_is']['profit']:+10.2f} {r['r_is']['wr']:>6.2%}")

    # Summary
    passes = sum(1 for r in rows if r["ok_oos"])
    print(f"\n=== SUMMARY ===")
    print(f"PAYOUT {PAYOUT:.2f} BE {BE:.2%} | IS 70% OOS 30% | Kelly(0.25, 2%, 1$) | Wilson 95%")
    print(f"Configs tested: {len(rows)}")
    print(f'PASS OOS (trades>=50 & Wilson>BE & profit>0): {passes}/{len(rows)}')
    if passes == 0:
        best = max(rows, key=lambda x: x["w_oos"])
        print(f"NO config passes OOS. Best OOS Wilson: {fmt_cfg(best)}")
        print(f"  OOS Wilson {best['w_oos']:.2%} vs BE {best['BE']:.2%} gap {best['w_oos']-best['BE']:+.2%} n={best['r_oos']['trades']} WR={best['r_oos']['wr']:.2%} profit={best['r_oos']['profit']:+.2f}")
        print(f"  IS profit={best['r_is']['profit']:+.2f} Wilson {best['w_is']:.2%}")
    else:
        print(f"PASS configs:")
        for r in rows:
            if r["ok_oos"]:
                print(f"  {fmt_cfg(r)} | OOS Wilson {r['w_oos']:.2%} > BE {r['BE']:.2%} | n={r['r_oos']['trades']} WR={r['r_oos']['wr']:.2%} profit={r['r_oos']['profit']:+.2f}")


if __name__ == "__main__":
    main()