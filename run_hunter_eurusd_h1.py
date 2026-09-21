"""Hunter EURUSD H1 (agregado de M15 histdata 40000 -> 10000 H1).
Grade: boll p=20,50 mult=1.5,2.0 exp=60/120m; donchian n=20,40,60 exp=60/120m; RSI per=7,14,21 bandas 70/30,75/25 exp=60/120m.
Payout 0.90 BE 52.63%. IS 70% OOS 30%. Retorne top 3 IS e OOS Wilson."""
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


def aggregate_to_h1(d):
    """Aggregate M15 data to H1 (4 bars = 1 hour)"""
    t, o, h, l, c = d["t"], d["o"], d["h"], d["l"], d["c"]
    n = len(c)
    n_h1 = n // 4
    t_h1 = t[::4][:n_h1]
    o_h1 = o[::4][:n_h1]
    c_h1 = c[3::4][:n_h1]
    h_h1 = []
    l_h1 = []
    for i in range(n_h1):
        start = i * 4
        h_h1.append(max(h[start:start+4]))
        l_h1.append(min(l[start:start+4]))
    return {"t": t_h1, "o": o_h1, "h": h_h1, "l": l_h1, "c": c_h1}


def sma(xs, p):
    out, s = [None] * len(xs), 0.0
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
        w = xs[i - p + 1 : i + 1]
        m = sum(w) / p
        out[i] = math.sqrt(sum((x - m) ** 2 for x in w) / p)
    return out


def rsi_list(xs, period):
    gains = [0.0] * len(xs)
    losses = [0.0] * len(xs)
    for i in range(1, len(xs)):
        diff = xs[i] - xs[i-1]
        if diff >= 0:
            gains[i] = diff
        else:
            losses[i] = -diff
    avg_gain = [None] * len(xs)
    avg_loss = [None] * len(xs)
    for i in range(period, len(xs)):
        if i == period:
            avg_gain[i] = sum(gains[i-period+1:i+1]) / period
            avg_loss[i] = sum(losses[i-period+1:i+1]) / period
        else:
            avg_gain[i] = (avg_gain[i-1] * (period-1) + gains[i]) / period
            avg_loss[i] = (avg_loss[i-1] * (period-1) + losses[i]) / period
    rsi = [None] * len(xs)
    for i in range(period, len(xs)):
        if avg_loss[i] == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain[i] / avg_loss[i]
            rsi[i] = 100 - (100 / (1 + rs))
    return rsi


# Bollinger
def fam_boll(d, p, mult):
    c = d["c"]
    basis, sd = sma(c, p), stdev(c, p)
    sig = []
    for i in range(p, len(c) - 1):
        if basis[i] is None:
            continue
        if c[i] < basis[i] - mult * sd[i]:
            sig.append((i, "call"))
        elif c[i] > basis[i] + mult * sd[i]:
            sig.append((i, "put"))
    return sig


# Donchian
def fam_donchian(d, n):
    h, l, c = d["h"], d["l"], d["c"]
    sig = []
    for i in range(n, len(c) - 1):
        hi = max(h[i - n : i])
        lo = min(l[i - n : i])
        if c[i] > hi:
            sig.append((i, "call"))
        elif c[i] < lo:
            sig.append((i, "put"))
    return sig


# RSI
def fam_rsi(d, per, upper, lower):
    c = d["c"]
    rsi = rsi_list(c, per)
    sig = []
    for i in range(per, len(c) - 1):
        r = rsi[i]
        if r is None:
            continue
        if r < lower:
            sig.append((i, "call"))
        elif r > upper:
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
    PAYOUT = 0.90
    BE = 1 / (1 + PAYOUT)

    d_m15 = load_m15("data/EURUSD_M15_histdata.csv")
    d = aggregate_to_h1(d_m15)
    c = d["c"]
    n_total = len(c)
    cut = int(n_total * 0.70)
    print(f"[DATA] EURUSD_M15_histdata: 40000 M15 -> {n_total} H1 | IS:0..{cut-1} ({cut}) OOS:{cut}..{n_total-1} ({n_total-cut})")
    print(f"[PAYOUT] {PAYOUT:.2f} BE {BE:.2%}")

    # Parameters per user request
    P_LIST = (20, 50)
    MULT_LIST = (1.5, 2.0)
    N_LIST = (20, 40, 60)
    RSI_PER_LIST = (7, 14, 21)
    RSI_BANDS = ((70, 30), (75, 25))
    EXPIRIES = (4, 8)  # 60m = 4 H1 bars, 120m = 8 H1 bars

    rows = []

    # Bollinger
    for p in P_LIST:
        for mult in MULT_LIST:
            sig_all = fam_boll(d, p=p, mult=mult)
            sig_is = [(i, s) for i, s in sig_all if i < cut]
            sig_oos = [(i, s) for i, s in sig_all if i >= cut]
            for exp in EXPIRIES:
                r_is = run(sig_is, c, 1000.0, exp, PAYOUT)
                r_oos = run(sig_oos, c, 1000.0, exp, PAYOUT)
                w_is = wilson(r_is["wins"], r_is["trades"])
                w_oos = wilson(r_oos["wins"], r_oos["trades"])
                exp_m = exp * 15
                checks = (r_oos["trades"] >= 50, w_oos > BE, r_oos["profit"] > 0)
                ok_oos = all(checks)
                rows.append({
                    "type": "boll",
                    "p": p, "mult": mult, "exp": exp, "exp_m": exp_m,
                    "r_is": r_is, "r_oos": r_oos,
                    "w_is": w_is, "w_oos": w_oos,
                    "ok_oos": ok_oos, "BE": BE,
                })

    # Donchian
    for n in N_LIST:
        sig_all = fam_donchian(d, n=n)
        sig_is = [(i, s) for i, s in sig_all if i < cut]
        sig_oos = [(i, s) for i, s in sig_all if i >= cut]
        for exp in EXPIRIES:
            r_is = run(sig_is, c, 1000.0, exp, PAYOUT)
            r_oos = run(sig_oos, c, 1000.0, exp, PAYOUT)
            w_is = wilson(r_is["wins"], r_is["trades"])
            w_oos = wilson(r_oos["wins"], r_oos["trades"])
            exp_m = exp * 15
            checks = (r_oos["trades"] >= 50, w_oos > BE, r_oos["profit"] > 0)
            ok_oos = all(checks)
            rows.append({
                "type": "donchian",
                "n": n, "exp": exp, "exp_m": exp_m,
                "r_is": r_is, "r_oos": r_oos,
                "w_is": w_is, "w_oos": w_oos,
                "ok_oos": ok_oos, "BE": BE,
            })

    # RSI
    for per in RSI_PER_LIST:
        for upper, lower in RSI_BANDS:
            sig_all = fam_rsi(d, per=per, upper=upper, lower=lower)
            sig_is = [(i, s) for i, s in sig_all if i < cut]
            sig_oos = [(i, s) for i, s in sig_all if i >= cut]
            for exp in EXPIRIES:
                r_is = run(sig_is, c, 1000.0, exp, PAYOUT)
                r_oos = run(sig_oos, c, 1000.0, exp, PAYOUT)
                w_is = wilson(r_is["wins"], r_is["trades"])
                w_oos = wilson(r_oos["wins"], r_oos["trades"])
                exp_m = exp * 15
                checks = (r_oos["trades"] >= 50, w_oos > BE, r_oos["profit"] > 0)
                ok_oos = all(checks)
                rows.append({
                    "type": "rsi",
                    "per": per, "upper": upper, "lower": lower, "exp": exp, "exp_m": exp_m,
                    "r_is": r_is, "r_oos": r_oos,
                    "w_is": w_is, "w_oos": w_oos,
                    "ok_oos": ok_oos, "BE": BE,
                })

    print(f"\n[CONFIG TESTADAS] {len(rows)}")

    # Top 3 IS by profit
    rows_sorted = sorted(rows, key=lambda x: x["r_is"]["profit"], reverse=True)
    print(f"\n=== TOP 3 IS por LUCRO ===")
    print(f"{'#':<3} {'cfg':<40} {'IS profit':<10} {'IS n':<6} {'IS WR':<7} {'IS Wilson':<10} {'OOS profit':<11} {'OOS n':<6} {'OOS WR':<7} {'OOS Wilson':<11} {'vs BE':<9} {'OOS verdict'}")
    for idx, r in enumerate(rows_sorted[:3], 1):
        if r["type"] == "boll":
            cfg = f'boll p={r["p"]} m={r["mult"]} exp={r["exp_m"]}m'
        elif r["type"] == "donchian":
            cfg = f'donchian n={r["n"]} exp={r["exp_m"]}m'
        else:
            cfg = f'rsi per={r["per"]} {r["upper"]}/{r["lower"]} exp={r["exp_m"]}m'
        is_ = r["r_is"]
        oos = r["r_oos"]
        print(
            f'{idx:<3} {cfg:<40} {is_["profit"]:+8.2f}  {is_["trades"]:<6} {is_["wr"]:.2%}  {r["w_is"]:.2%}     {oos["profit"]:+8.2f}   {oos["trades"]:<6} {oos["wr"]:.2%}  {r["w_oos"]:.2%}     {r["w_oos"]-r["BE"]:+.2%}   {"PASS" if r["ok_oos"] else "FAIL"}'
        )

    # Top 3 OOS by Wilson
    rows_oos_wilson = sorted(rows, key=lambda x: x["w_oos"], reverse=True)
    print(f"\n=== TOP 3 OOS por WILSON ===")
    print(f"{'#':<3} {'cfg':<40} {'OOS Wilson':<11} {'OOS n':<6} {'OOS WR':<7} {'OOS profit':<11} {'vs BE':<9} {'IS profit':<10} {'IS Wilson':<10} {'OOS verdict'}")
    for idx, r in enumerate(rows_oos_wilson[:3], 1):
        if r["type"] == "boll":
            cfg = f'boll p={r["p"]} m={r["mult"]} exp={r["exp_m"]}m'
        elif r["type"] == "donchian":
            cfg = f'donchian n={r["n"]} exp={r["exp_m"]}m'
        else:
            cfg = f'rsi per={r["per"]} {r["upper"]}/{r["lower"]} exp={r["exp_m"]}m'
        print(
            f'{idx:<3} {cfg:<40} {r["w_oos"]:.2%}       {r["r_oos"]["trades"]:<6} {r["r_oos"]["wr"]:.2%}  {r["r_oos"]["profit"]:+8.2f}   {r["w_oos"]-r["BE"]:+.2%}   {r["r_is"]["profit"]:+8.2f}   {r["w_is"]:.2%}     {"PASS" if r["ok_oos"] else "FAIL"}'
        )

    # Top 3 OOS by profit
    rows_oos_profit = sorted(rows, key=lambda x: x["r_oos"]["profit"], reverse=True)
    print(f"\n=== TOP 3 OOS por LUCRO OOS ===")
    print(f"{'#':<3} {'cfg':<40} {'OOS profit':<11} {'OOS n':<6} {'OOS WR':<7} {'OOS Wilson':<11} {'IS profit':<10} {'IS WR':<7}")
    for idx, r in enumerate(rows_oos_profit[:3], 1):
        if r["type"] == "boll":
            cfg = f'boll p={r["p"]} m={r["mult"]} exp={r["exp_m"]}m'
        elif r["type"] == "donchian":
            cfg = f'donchian n={r["n"]} exp={r["exp_m"]}m'
        else:
            cfg = f'rsi per={r["per"]} {r["upper"]}/{r["lower"]} exp={r["exp_m"]}m'
        print(
            f'{idx:<3} {cfg:<40} {r["r_oos"]["profit"]:+8.2f}   {r["r_oos"]["trades"]:<6} {r["r_oos"]["wr"]:.2%}  {r["w_oos"]:.2%}     {r["r_is"]["profit"]:+8.2f}   {r["r_is"]["wr"]:.2%}'
        )

    # Summary
    passes = sum(1 for r in rows if r["ok_oos"])
    print(f"\n=== SUMÁRIO ===")
    print(f"PAYOUT {PAYOUT:.2f} BE {BE:.2%} | IS 70% OOS 30%")
    print(f"Configs testadas: {len(rows)} (Bollinger: {len(P_LIST)*len(MULT_LIST)*len(EXPIRIES)}, Donchian: {len(N_LIST)*len(EXPIRIES)}, RSI: {len(RSI_PER_LIST)*len(RSI_BANDS)*len(EXPIRIES)})")
    print(f'PASS OOS (trades>=50 & Wilson>BE & lucro>0): {passes}/{len(rows)}')
    if passes == 0:
        best = max(rows, key=lambda x: x["w_oos"])
        if best["type"] == "boll":
            cfg = f'boll p={best["p"]} m={best["mult"]} exp={best["exp_m"]}m'
        elif best["type"] == "donchian":
            cfg = f'donchian n={best["n"]} exp={best["exp_m"]}m'
        else:
            cfg = f'rsi per={best["per"]} {best["upper"]}/{best["lower"]} exp={best["exp_m"]}m'
        print(f'NENHUM config passa OOS. Melhor OOS Wilson: {cfg}')
        print(
            f'  OOS Wilson {best["w_oos"]:.2%} vs BE {best["BE"]:.2%} gap {best["w_oos"]-best["BE"]:+.2%} n={best["r_oos"]["trades"]} WR={best["r_oos"]["wr"]:.2%} lucro={best["r_oos"]["profit"]:+.2f}'
        )
        print(f'  IS lucro={best["r_is"]["profit"]:+.2f} Wilson {best["w_is"]:.2%}')


if __name__ == "__main__":
    main()