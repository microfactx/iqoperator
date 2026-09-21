"""Hunter BTC M15 RSI zones grid search.
RSI periods: 7, 10, 14, 21
Bands: 70/30, 65/35, 75/25, 80/20
With/without EMA50 (macro_ema=50 or None)
Expiry: 15, 30, 60m (1, 2, 4 bars)
Payout: 0.87, 0.90
IS 70% / OOS 30% split, ranked by IS Kelly profit, verified by OOS Wilson.
"""
import csv
import math
import sys
from collections import deque

from backtest import rsi_list, ema_list
from kelly import kelly_fraction_stake

# Data paths
M15_PATH = "data/BTCUSDT_M15_1y.csv"
M5_PATH = "data/BTCUSDT_M5_1y.csv"
H4_PATH = "data/BTCUSDT_H4_1y.csv"
D1_PATH = "data/BTCUSDT_D1_1y.csv"

# Grid parameters
RSI_PERIODS = [7, 10, 14, 21]
BANDS = [(70, 30), (65, 35), (75, 25), (80, 20)]
MACRO_EMAS = [50, None]  # None = sem EMA50 macro
EXPIRY_BARS = [1, 2, 4]  # 15m, 30m, 60m
PAYOUTS = [0.87, 0.90]

# Fixed params
BALANCE = 1000.0
FRACTION = 0.25
MAX_RISK = 0.02
MIN_STAKE = 1.0
LOOKBACK = 50
PRIOR = 0.58
PRIOR_WEIGHT = 20.0
M5_CONFIRM = True
BIAS_MODE = "agree"  # "agree" = D1+H4 alinhados (sniper)
M15_MS = 900_000

# Wilson 95%
Z = 1.96


def load_tf(path: str):
    t, o, c = [], [], []
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
            o.append(float(r.get("open", r["close"])))
            c.append(float(r["close"]))
    return t, o, c


def last_closed(close_times, entry_close_ms):
    """Índice da última barra 100% fechada até entry (close <= entry). -1 se nenhuma."""
    import bisect
    return bisect.bisect_right(close_times, entry_close_ms) - 1


def wilson_lower(wins, n, z=Z):
    if not n:
        return 0.0
    p = wins / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - m) / d


def simulate(m15, h4, d1, m5, balance, expiry_bars, rsi_per, ob, os_,
             macro_ema, prior=PRIOR, fraction=FRACTION, max_risk=MAX_RISK,
             min_stake=MIN_STAKE, lookback=LOOKBACK, prior_weight=PRIOR_WEIGHT,
             m5_confirm=M5_CONFIRM, bias_mode=BIAS_MODE,
             i0=0, i1=None):
    m15t, m15o, m15c = m15
    h4t, _, h4c = h4
    d1t, _, d1c = d1
    m5t, m5o, m5c = m5
    n = len(m15c)
    i1 = i1 or n - 1 - 4
    
    rsi = rsi_list(m15c, rsi_per)
    
    # Macro EMAs only if macro_ema is specified
    if macro_ema is not None:
        h4e = ema_list(h4c, macro_ema)
        d1e = ema_list(d1c, macro_ema)
    else:
        h4e = d1e = None
    
    h4ct = [x + 4 * 3600_000 for x in h4t]
    d1ct = [x + 86400_000 for x in d1t]
    m5ct = [x + 300_000 for x in m5t]

    bal, peak, max_dd = balance, balance, 0.0
    history: deque[bool] = deque(maxlen=lookback)
    wins = losses = ties = 0
    monthly: dict[str, float] = {}
    rows = []

    for i in range(max(i0, rsi_per + 1), min(i1, n - expiry_bars)):
        rl = rsi[i]
        if rl is None or math.isnan(rl):
            continue
        entry_close = m15t[i] + M15_MS
        kh = last_closed(h4ct, entry_close)
        kd = last_closed(d1ct, entry_close)
        
        # Check macro bias if EMA is enabled
        long_bias = short_bias = False
        if macro_ema is not None:
            if kh < macro_ema or kd < macro_ema:
                continue
            h4_long = h4c[kh] > h4e[kh]
            h4_short = h4c[kh] < h4e[kh]
            d1_long = d1c[kd] > d1e[kd]
            d1_short = d1c[kd] < d1e[kd]
            if bias_mode == "either":
                long_bias = h4_long or d1_long
                short_bias = h4_short or d1_short
                if long_bias and short_bias:
                    continue
            else:  # agree
                long_bias = h4_long and d1_long
                short_bias = h4_short and d1_short
        else:
            # Sem filtro macro: permite ambos os lados
            long_bias = short_bias = True

        if long_bias and rl < os_:
            signal = "call"
        elif short_bias and rl > ob:
            signal = "put"
        else:
            continue
        
        if m5_confirm:
            km = last_closed(m5ct, entry_close)
            if km < 0:
                continue
            if signal == "call" and not (m5c[km] > m5o[km]):
                continue
            if signal == "put" and not (m5c[km] < m5o[km]):
                continue

        nn = len(history)
        p = (prior * prior_weight + sum(1 for w in history if w)) / (prior_weight + nn) if nn else prior
        stake, kfull = kelly_fraction_stake(bal, PAYOUT, p, fraction, max_risk, min_stake)
        entry, nxt = m15c[i], m15c[i + expiry_bars]
        if nxt == entry:
            ties += 1
            won = None
            profit = 0.0
        elif (signal == "call" and nxt > entry) or (signal == "put" and nxt < entry):
            wins += 1
            won = True
            profit = stake * PAYOUT
        else:
            losses += 1
            won = False
            profit = -stake
        bal += profit
        if won is not None:
            history.append(won)
        peak = max(peak, bal)
        max_dd = max(max_dd, (peak - bal) / peak if peak else 0)
        mon = __import__('datetime').datetime.fromtimestamp(entry_close / 1000, tz=__import__('datetime').timezone.utc).strftime("%Y-%m")
        monthly[mon] = monthly.get(mon, 0.0) + profit
        rows.append({"i": i, "signal": signal, "profit": round(profit, 2)})

    tot = wins + losses
    wr = wins / tot if tot else 0.0
    return {"trades": tot, "wins": wins, "losses": losses, "ties": ties,
            "winrate": wr, "start": balance, "end": round(bal, 2),
            "profit": round(bal - balance, 2),
            "max_dd": round(max_dd, 4), "monthly": monthly, "rows": rows}


def main():
    # Verify data files exist
    import os
    for p in (M15_PATH, M5_PATH, H4_PATH, D1_PATH):
        if not os.path.exists(p):
            sys.exit(f"[ERRO] faltando {p}")
    
    m15 = load_tf(M15_PATH)
    m5 = load_tf(M5_PATH)
    h4 = load_tf(H4_PATH)
    d1 = load_tf(D1_PATH)
    print(f"[DATA] M15:{len(m15[0])} M5:{len(m5[0])} H4:{len(h4[0])} D1:{len(d1[0])}")

    cut = int(len(m15[0]) * 0.70)
    print(f"[SPLIT] IS 70% = {cut} candles | OOS 30% = {len(m15[0]) - cut} candles")

    all_results = []
    total_configs = len(RSI_PERIODS) * len(BANDS) * len(MACRO_EMAS) * len(EXPIRY_BARS) * len(PAYOUTS)
    print(f"[GRID] Total configs: {total_configs}")
    
    done = 0
    for payout in PAYOUTS:
        global PAYOUT
        PAYOUT = payout
        BE = 1 / (1 + payout)
        
        for rsi_per in RSI_PERIODS:
            for ob, os_ in BANDS:
                for macro_ema in MACRO_EMAS:
                    for exp in EXPIRY_BARS:
                        done += 1
                        # IS
                        r_is = simulate(m15, h4, d1, m5, BALANCE, exp, rsi_per, ob, os_,
                                        macro_ema, i0=0, i1=cut)
                        # OOS
                        r_oos = simulate(m15, h4, d1, m5, BALANCE, exp, rsi_per, ob, os_,
                                         macro_ema, i0=cut, i1=len(m15[0]))
                        
                        is_wlow = wilson_lower(r_is["wins"], r_is["trades"])
                        oos_wlow = wilson_lower(r_oos["wins"], r_oos["trades"])
                        
                        oos_ok = (r_oos["trades"] >= 50 and oos_wlow > BE and r_oos["profit"] > 0)
                        
                        macro_str = f"EMA{macro_ema}" if macro_ema else "noMacro"
                        tag = f"RSI{rsi_per} {os_}/{ob} {macro_str} exp{exp*15}m"
                        
                        all_results.append({
                            "tag": tag,
                            "rsi_per": rsi_per,
                            "ob": ob,
                            "os_": os_,
                            "macro_ema": macro_ema,
                            "exp": exp,
                            "exp_m": exp * 15,
                            "payout": payout,
                            "be": BE,
                            "is_trades": r_is["trades"],
                            "is_wins": r_is["wins"],
                            "is_wr": r_is["winrate"],
                            "is_wlow": is_wlow,
                            "is_profit": r_is["profit"],
                            "is_dd": r_is["max_dd"],
                            "oos_trades": r_oos["trades"],
                            "oos_wins": r_oos["wins"],
                            "oos_wr": r_oos["winrate"],
                            "oos_wlow": oos_wlow,
                            "oos_profit": r_oos["profit"],
                            "oos_dd": r_oos["max_dd"],
                            "oos_ok": oos_ok,
                        })
                        
                        if done % 50 == 0:
                            print(f"  [{done}/{total_configs}] completed...")

    # Sort by IS profit (Kelly)
    all_results.sort(key=lambda x: x["is_profit"], reverse=True)

    # Print results per payout
    for payout in PAYOUTS:
        BE = 1 / (1 + payout)
        subset = [r for r in all_results if r["payout"] == payout]
        subset.sort(key=lambda x: x["is_profit"], reverse=True)
        
        print(f"\n{'='*120}")
        print(f" PAYOUT {payout} (BE {BE:.2%}) — RANKING IS (70%) POR LUCRO KELLY — TOP 20 de {len(subset)} configs")
        print(f"{'='*120}")
        header = f"{'#':<3} {'Config':<35} {'IS n':<6} {'IS WR':<7} {'IS Wlow':<8} {'IS Lucro':<10} {'IS DD':<7} | {'OOS n':<6} {'OOS WR':<7} {'OOS Wlow':<8} {'OOS Lucro':<11} {'OOS DD':<7} VERED"
        print(header)
        print("-" * len(header))
        for idx, r in enumerate(subset[:20], 1):
            ver = "PASS" if r["oos_ok"] else "FAIL"
            print(f"{idx:<3} {r['tag']:<35} {r['is_trades']:<6} {r['is_wr']:<7.2%} {r['is_wlow']:<8.2%} {r['is_profit']:<+10.2f} {r['is_dd']:<7.2%} | "
                  f"{r['oos_trades']:<6} {r['oos_wr']:<7.2%} {r['oos_wlow']:<8.2%} {r['oos_profit']:<+11.2f} {r['oos_dd']:<7.2%} {ver}")

        # Also show filtered IS trades >= 50
        print(f"\n  [TOP IS filtrado trades>=50 payout {payout}]")
        filt = [r for r in subset if r["is_trades"] >= 50]
        for idx, r in enumerate(filt[:10], 1):
            ver = "PASS" if r["oos_ok"] else "FAIL"
            print(f"   {idx}. {r['tag']} | IS n={r['is_trades']} WR={r['is_wr']:.2%} (Wlow {r['is_wlow']:.2%} vs BE {BE:.2%}) lucro {r['is_profit']:+.2f} DD {r['is_dd']:.2%}  -> OOS n={r['oos_trades']} WR={r['oos_wr']:.2%} Wlow {r['oos_wlow']:.2%} lucro {r['oos_profit']:+.2f} {ver}")

    # Global OOS ranking
    print(f"\n{'='*120}")
    print(" RANKING OOS GLOBAL (ordem por lucro OOS) — TOP 15 (ambos payouts)")
    print(f"{'='*120}")
    global_sorted = sorted(all_results, key=lambda x: x["oos_profit"], reverse=True)
    for idx, r in enumerate(global_sorted[:15], 1):
        print(f"{idx:>2}. {r['tag']:<35} payout {r['payout']} | OOS lucro {r['oos_profit']:+.2f} n={r['oos_trades']} WR={r['oos_wr']:.2%} Wlow {r['oos_wlow']:.2%} BE {r['be']:.2%} | IS lucro {r['is_profit']:+.2f} WR {r['is_wr']:.2%}")

    # Valid OOS summary
    print(f"\n{'='*120}")
    print(" RESUMO VEREDITO OOS VÁLIDO (n>=50 & Wlow>BE & lucro>0)")
    print(f"{'='*120}")
    valid = [r for r in all_results if r["oos_ok"]]
    print(f"Configs válidas OOS: {len(valid)}/{len(all_results)}")
    for r in sorted(valid, key=lambda x: x["oos_profit"], reverse=True)[:15]:
        print(f"  VALID {r['tag']:<35} payout {r['payout']} | OOS lucro {r['oos_profit']:+.2f} WR {r['oos_wr']:.2%} Wlow {r['oos_wlow']:.2%} BE {r['be']:.2%} n={r['oos_trades']} | IS lucro {r['is_profit']:+.2f} WR {r['is_wr']:.2%}")

    # Save CSV
    with open("data/hunter_rsi_zones_top.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tag", "rsi_per", "ob", "os_", "macro_ema", "exp_m", "payout", "be",
                    "is_trades", "is_wr", "is_wlow", "is_profit", "is_dd",
                    "oos_trades", "oos_wr", "oos_wlow", "oos_profit", "oos_dd", "veredito"])
        for r in sorted(all_results, key=lambda x: x["is_profit"], reverse=True):
            w.writerow([r["tag"], r["rsi_per"], r["ob"], r["os_"], 
                       r["macro_ema"] if r["macro_ema"] else "None", r["exp_m"], r["payout"], round(r["be"], 4),
                       r["is_trades"], round(r["is_wr"], 4), round(r["is_wlow"], 4), r["is_profit"], r["is_dd"],
                       r["oos_trades"], round(r["oos_wr"], 4), round(r["oos_wlow"], 4), r["oos_profit"], r["oos_dd"],
                       "PASS" if r["oos_ok"] else "FAIL"])
    print("\n[CSV] data/hunter_rsi_zones_top.csv gerado")


if __name__ == "__main__":
    main()