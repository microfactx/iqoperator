"""Backtest hipótese adaptada H010: macro 1D+H4, micro M15+M5, entrada M15.

Setup (interpretação documentada em research/h010/BACKTEST_PLAN.md):
- Viés macro SNIPER: exige D1 e H4 de acordo (close vs EMA).
- Gatilho M15: RSI em zona (call < OS, put > OB).
- Confirmação M5: último M5 fechado na direção do sinal.
- Expiração em grade: 15/30/45/60min. Payout 0.87 (BE 53.48%).
- IS (70%) p/ seleção, OOS (30%) p/ veredito. Timestamps, sem lookahead.

Uso:
  py backtest_h010.py --grid-is 1
  py backtest_h010.py --expiry 2 --rsi 14 --split 1
"""
import argparse
import bisect
import csv
import math
import sys
from collections import deque
from datetime import datetime, timezone

from backtest import rsi_list, ema_list
from kelly import kelly_fraction_stake

PAYOUT = 0.87
BREAKEVEN = 1 / (1 + PAYOUT)
M15_MS = 900_000


def load_tf(path: str):
    t, o, c = [], [], []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                v = int(float(r["time"]))
            except ValueError:
                continue
            # normaliza precisão: s (10d) -> ms; us (16d) -> ms; ms (13d) mantém
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
    return bisect.bisect_right(close_times, entry_close_ms) - 1


def simulate(m15, h4, d1, m5, balance, expiry_bars, rsi_per, ob, os_,
             macro_ema, prior=0.58, fraction=0.25, max_risk=0.02,
             min_stake=1.0, lookback=50, prior_weight=20.0,
             m5_confirm=True, bias_mode="agree",
             i0=0, i1=None):
    m15t, m15o, m15c = m15
    h4t, _, h4c = h4
    d1t, _, d1c = d1
    m5t, m5o, m5c = m5
    n = len(m15c)
    i1 = i1 or n - 1 - 4
    rsi = rsi_list(m15c, rsi_per)
    h4e = ema_list(h4c, macro_ema)
    d1e = ema_list(d1c, macro_ema)
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
                continue  # conflito macro: sem trade
        else:  # agree: sniper, exige D1+H4 alinhados
            long_bias = h4_long and d1_long
            short_bias = h4_short and d1_short
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
        mon = datetime.fromtimestamp(entry_close / 1000, tz=timezone.utc).strftime("%Y-%m")
        monthly[mon] = monthly.get(mon, 0.0) + profit
        rows.append({"i": i, "signal": signal, "profit": round(profit, 2)})

    tot = wins + losses
    wr = wins / tot if tot else 0.0
    return {"trades": tot, "wins": wins, "losses": losses, "ties": ties,
            "winrate": wr, "start": balance, "end": round(bal, 2),
            "profit": round(bal - balance, 2),
            "max_dd": round(max_dd, 4), "monthly": monthly, "rows": rows}


def wilson_lower(wins, n, z=1.96):
    if not n:
        return 0.0
    p = wins / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - m) / d


def show(r, label=""):
    pre = f"[{label}] " if label else ""
    print(f"{pre}Trades {r['trades']} W/L {r['wins']}/{r['losses']} "
          f"WR {r['winrate']:.2%} Lucro {r['profit']:+.2f} MaxDD {r['max_dd']:.2%}")


def verdict(r):
    n, wr = r["trades"], r["winrate"]
    low = wilson_lower(r["wins"], n)
    checks = [(f"trades >= 50 ({n})", n >= 50),
              (f"Wilson inf.95% {low:.2%} > BE {BREAKEVEN:.2%}", low > BREAKEVEN),
              (f"lucro OOS > 0 ({r['profit']:+.2f})", r["profit"] > 0)]
    print("[VEREDITO OOS]")
    ok_all = True
    for label, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
        ok_all = ok_all and ok
    print("  => EDGE VALIDADO" if ok_all else "  => SEM EDGE")
    return ok_all


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m15", default="data/BTCUSDT_M15_1y.csv")
    ap.add_argument("--m5", default="data/BTCUSDT_M5_1y.csv")
    ap.add_argument("--h4", default="data/BTCUSDT_H4_1y.csv")
    ap.add_argument("--d1", default="data/BTCUSDT_D1_1y.csv")
    ap.add_argument("--balance", type=float, default=1000.0)
    ap.add_argument("--expiry", type=int, default=2)
    ap.add_argument("--rsi", type=int, default=14)
    ap.add_argument("--ob", type=float, default=70)
    ap.add_argument("--os", type=float, default=30)
    ap.add_argument("--macro-ema", type=int, default=50)
    ap.add_argument("--m5-confirm", type=int, default=1)
    ap.add_argument("--bias-mode", default="agree", choices=["agree", "either"])
    ap.add_argument("--grid-is", type=int, default=0)
    ap.add_argument("--split", type=int, default=0)
    a = ap.parse_args()

    for p in (a.m15, a.m5, a.h4, a.d1):
        import os
        if not os.path.exists(p):
            sys.exit(f"[ERRO] faltando {p}")
    m15 = load_tf(a.m15)
    m5, h4, d1 = load_tf(a.m5), load_tf(a.h4), load_tf(a.d1)
    print(f"[DATA] M15:{len(m15[0])} M5:{len(m5[0])} H4:{len(h4[0])} D1:{len(d1[0])}")

    base = dict(balance=a.balance, ob=a.ob, os_=a.os, macro_ema=a.macro_ema,
                m5_confirm=bool(a.m5_confirm), bias_mode=a.bias_mode)
    cut = int(len(m15[0]) * 0.70)

    if a.grid_is:
        print(f"== IS (70%, {cut} candles M15) ==")
        gbase = dict(balance=a.balance)
        ranked = []
        total = 2 * 3 * 3 * 2 * 2 * 2
        done = 0
        for exp in (1, 2):
            for per in (8, 10, 14):
                for ob, os_ in ((70, 30), (75, 25), (65, 35)):
                    for mema in (21, 50):
                        for m5c in (True, False):
                            for bias in ("agree", "either"):
                                r = simulate(m15, h4, d1, m5, expiry_bars=exp,
                                             rsi_per=per, ob=ob, os_=os_,
                                             macro_ema=mema, m5_confirm=m5c,
                                             bias_mode=bias, i0=0, i1=cut, **gbase)
                                done += 1
                                tag = (f"exp={exp*15}m RSI{per} {os_}/{ob} "
                                       f"mEMA{mema} m5={int(m5c)} {bias}")
                                print(f"[{done}/{total}] {tag}: n={r['trades']} "
                                      f"WR={r['winrate']:.2%} lucro={r['profit']:+.2f}")
                                ranked.append((tag, dict(exp=exp, per=per, ob=ob,
                                                         os_=os_, mema=mema, m5c=m5c,
                                                         bias=bias), r))
        ranked.sort(key=lambda x: x[2]["profit"], reverse=True)
        print("\n[TOP5 IS]")
        for tag, _, r in ranked[:5]:
            print(f"  {tag}: lucro={r['profit']:+.2f} WR={r['winrate']:.2%} n={r['trades']}")
        print("\n== OOS 30% do TOP3 ==")
        for tag, kw, _ in ranked[:3]:
            r_oos = simulate(m15, h4, d1, m5, expiry_bars=kw["exp"],
                             rsi_per=kw["per"], ob=kw["ob"], os_=kw["os_"],
                             macro_ema=kw["mema"], m5_confirm=kw["m5c"],
                             bias_mode=kw["bias"], i0=cut, i1=len(m15[0]),
                             **gbase)
            print(f"\n[TOP IS] {tag}")
            show(r_oos, "OOS")
            verdict(r_oos)
        return

    r = simulate(m15, h4, d1, m5, expiry_bars=a.expiry, rsi_per=a.rsi, **base)
    show(r, f"FULL exp={a.expiry*15}m RSI{a.rsi}")
    months = sorted(r["monthly"].items())
    pos = sum(1 for _, v in months if v > 0)
    print(f"[MESES] {pos}/{len(months)} positivos")
    if a.split:
        r_is = simulate(m15, h4, d1, m5, expiry_bars=a.expiry, rsi_per=a.rsi,
                        i0=0, i1=cut, **base)
        r_oos = simulate(m15, h4, d1, m5, expiry_bars=a.expiry, rsi_per=a.rsi,
                         i0=cut, i1=len(m15[0]), **base)
        show(r_is, "IS 70%")
        show(r_oos, "OOS 30%")
        ok = verdict(r_oos)
        months = sorted(r_oos["monthly"].items())
        pos = sum(1 for _, v in months if v > 0)
        print(f"[MESES OOS] {pos}/{len(months)} positivos: " +
              ", ".join(f"{m}:{v:+.0f}" for m, v in months))
        return ok


if __name__ == "__main__":
    main()
