"""Backtest offline RSI M15 + Kelly — só stdlib (sem pandas).

Uso:
  py backtest.py --synthetic 2000 --balance 1000 --payout 0.8
  py backtest.py --csv data/BTCUSD_M15.csv --balance 1000 --payout 0.8
  py backtest.py --csv data/BTCUSD_M15.csv --grid 1
  py backtest.py --fetch 1000 --csv data/BTCUSD_M15.csv   (precisa .env com login)

CSV esperado: time,open,high,low,close  (time em epoch ou ISO; só close é obrigatório)
Resultado binária M15: expiração = 1 candle. CALL ganha se close[i+1] > close[i].
"""
import argparse
import csv
import math
import os
import random
import sys
import time
from collections import deque

from kelly import kelly_fraction_stake


def rsi_list(closes: list[float], period: int = 14) -> list[float | None]:
    """RSI Wilder puro-python. Retorna lista alinhada (None p/ aquecimento)."""
    out: list[float | None] = [None] * len(closes)
    if len(closes) < period + 1:
        return out
    gains, losses = [], []
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains) / period
    al = sum(losses) / period
    out[period] = 100 - 100 / (1 + ag / al) if al > 0 else 100.0
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (period - 1) + max(d, 0)) / period
        al = (al * (period - 1) + max(-d, 0)) / period
        out[i] = 100 - 100 / (1 + ag / al) if al > 0 else 100.0
    return out


def load_csv(path: str) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        if "close" not in (rd.fieldnames or []):
            raise ValueError(f"{path} precisa de coluna 'close' (achado: {rd.fieldnames})")
        for r in rd:
            try:
                rows.append({"time": r.get("time", ""), "close": float(r["close"])})
            except (ValueError, TypeError):
                continue
    return rows


def ema_list(closes: list[float], span: int) -> list[float]:
    k = 2 / (span + 1)
    out = [closes[0]]
    for c in closes[1:]:
        out.append(c * k + out[-1] * (1 - k))
    return out


def simulate(rows: list[dict], balance: float, payout: float, period: int,
             ob: float, os_: float, require_exit: bool, prior: float,
             fraction: float, max_risk: float, min_stake: float,
             lookback: int, prior_weight: float, mode: str = "reversion",
             trend: int = 0, htf: int = 4, htf_ema: int = 50,
             htf_rule: str = "bt") -> dict:
    closes = [r["close"] for r in rows]
    rsi = rsi_list(closes, period)
    ema = ema_list(closes, trend) if trend > 0 else None
    h1_close: list[float] = []
    if mode == "mtf_pullback":
        for k in range(len(closes) // htf):
            h1_close.append(closes[k * htf + htf - 1])
        h1_ema = ema_list(h1_close, htf_ema)
    bal = balance
    peak = balance
    max_dd = 0.0
    history: deque[bool] = deque(maxlen=lookback)
    trades = []
    wins = losses = ties = 0

    for i in range(period + 1, len(closes) - 1):
        rp, rl = rsi[i - 1], rsi[i]
        if rp is None or rl is None:
            continue
        signal = None
        if mode == "mtf_pullback":
            # viés H1 (última barra 100% fechada ANTES do candle M15 (sem lookahead)
            if htf_rule == "live":
                # replica o bot ao vivo: iloc[-2] sobre H1 com barra formando = K-1
                k_max = (i - 3) // htf - 1
            else:
                k_max = (i - htf) // htf
            if k_max < htf_ema or k_max >= len(h1_close):
                continue
            bias_long = h1_close[k_max] > h1_ema[k_max]
            bias_short = h1_close[k_max] < h1_ema[k_max]
            if require_exit:
                if bias_long and rp <= os_ < rl:
                    signal = "call"
                elif bias_short and rp >= ob > rl:
                    signal = "put"
            else:
                if bias_long and rl < os_:
                    signal = "call"
                elif bias_short and rl > ob:
                    signal = "put"
        elif mode == "momentum":
            # continuação de tendência: rompeu p/ cima do OB -> call; p/ baixo do OS -> put
            if require_exit:
                if rp <= ob < rl:
                    signal = "call"
                elif rp >= os_ > rl:
                    signal = "put"
            else:
                if rl > ob:
                    signal = "call"
                elif rl < os_:
                    signal = "put"
        elif require_exit:
            if rp <= os_ < rl:
                signal = "call"
            elif rp >= ob > rl:
                signal = "put"
        else:
            if rl < os_:
                signal = "call"
            elif rl > ob:
                signal = "put"
        if not signal:
            continue
        if ema is not None:
            # só a favor da tendência: call acima da EMA, put abaixo
            if signal == "call" and closes[i] <= ema[i]:
                continue
            if signal == "put" and closes[i] >= ema[i]:
                continue

        n = len(history)
        p = (prior * prior_weight + sum(1 for w in history if w)) / (prior_weight + n) if n else prior
        stake, kfull = kelly_fraction_stake(bal, payout, p, fraction, max_risk, min_stake)
        entry, nxt = closes[i], closes[i + 1]
        if nxt == entry:
            ties += 1
            profit = 0.0
            won = None
        elif (signal == "call" and nxt > entry) or (signal == "put" and nxt < entry):
            wins += 1
            won = True
            profit = stake * payout
        else:
            losses += 1
            won = False
            profit = -stake
        bal += profit
        if won is not None:
            history.append(won)
        peak = max(peak, bal)
        dd = (peak - bal) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
        trades.append({"i": i, "signal": signal, "rsi": round(rl, 2),
                       "stake": stake, "profit": round(profit, 2),
                       "balance": round(bal, 2), "p": round(p, 4), "kelly": kfull})

    tot = wins + losses
    return {"trades": tot, "wins": wins, "losses": losses, "ties": ties,
            "winrate": wins / tot if tot else 0.0,
            "start": balance, "end": round(bal, 2),
            "profit": round(bal - balance, 2),
            "roi": (bal - balance) / balance if balance else 0.0,
            "max_dd": round(max_dd, 4), "rows": trades}


def cmd_synthetic(path: str, n: int):
    random.seed(42)
    price = 60000.0
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close"])
        t = int(time.time()) - n * 900
        for _ in range(n):
            o = price
            drift = random.gauss(0, 80)
            c = max(o + drift, 1000)
            h, l = max(o, c) + abs(random.gauss(0, 30)), min(o, c) - abs(random.gauss(0, 30))
            w.writerow([t, round(o, 2), round(h, 2), round(l, 2), round(c, 2)])
            price, t = c, t + 900
    print(f"[OK] sintético: {path} ({n} candles M15)")


def cmd_fetch(n: int, path: str):
    from dotenv import load_dotenv
    load_dotenv()
    email, pwd = os.getenv("IQ_EMAIL", ""), os.getenv("IQ_PASSWORD", "")
    asset = os.getenv("IQ_ASSET", "BTCUSD")
    if not email or not pwd:
        sys.exit("[ERRO] IQ_EMAIL/IQ_PASSWORD no .env")
    from iqoptionapi.stable_api import IQ_Option
    api = IQ_Option(email, pwd)
    ok, reason = api.connect()
    if not ok:
        sys.exit(f"[ERRO] connect: {reason}")
    candles = api.get_candles(asset, 900, n, time.time())
    if not candles:
        sys.exit("[ERRO] sem candles")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close"])
        for c in candles:
            w.writerow([c.get("from", ""), c.get("open", ""), c.get("max", ""),
                        c.get("min", ""), c.get("close", "")])
    print(f"[OK] {len(candles)} candles -> {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/BTCUSD_M15.csv")
    ap.add_argument("--balance", type=float, default=1000.0)
    ap.add_argument("--payout", type=float, default=0.80)
    ap.add_argument("--period", type=int, default=14)
    ap.add_argument("--ob", type=float, default=70)
    ap.add_argument("--os", type=float, default=30)
    ap.add_argument("--require-exit", type=int, default=1)
    ap.add_argument("--prior", type=float, default=0.58)
    ap.add_argument("--fraction", type=float, default=0.25)
    ap.add_argument("--max-risk", type=float, default=0.02)
    ap.add_argument("--min", type=float, default=1.0)
    ap.add_argument("--lookback", type=int, default=50)
    ap.add_argument("--prior-weight", type=float, default=20.0)
    ap.add_argument("--out", default="")
    ap.add_argument("--grid", type=int, default=0)
    ap.add_argument("--mode", default="reversion", choices=["reversion", "momentum", "mtf_pullback"])
    ap.add_argument("--trend", type=int, default=0)
    ap.add_argument("--htf", type=int, default=4)
    ap.add_argument("--htf-ema", type=int, default=50)
    ap.add_argument("--htf-rule", default="bt", choices=["bt", "live"])
    ap.add_argument("--split", type=int, default=0)
    ap.add_argument("--synthetic", type=int, default=0)
    ap.add_argument("--fetch", type=int, default=0)
    a = ap.parse_args()

    if a.synthetic:
        cmd_synthetic(a.csv, a.synthetic)
    if a.fetch:
        cmd_fetch(a.fetch, a.csv)
        return
    if not os.path.exists(a.csv):
        sys.exit(f"[ERRO] CSV não achado: {a.csv} (use --synthetic 2000 ou --fetch 1000)")

    rows = load_csv(a.csv)
    base = dict(balance=a.balance, payout=a.payout, require_exit=bool(a.require_exit),
                prior=a.prior, fraction=a.fraction, max_risk=a.max_risk,
                min_stake=a.min, lookback=a.lookback, prior_weight=a.prior_weight,
                mode=a.mode, trend=a.trend, htf=a.htf, htf_ema=a.htf_ema,
                htf_rule=a.htf_rule)

    def show(r, label=""):
        pre = f"[{label}] " if label else ""
        print(f"{pre}Trades: {r['trades']} | W/L/T: {r['wins']}/{r['losses']}/{r['ties']} | "
              f"WR: {r['winrate']:.2%} | Lucro: {r['profit']:+.2f} | "
              f"{r['start']:.2f}->{r['end']:.2f} ({r['roi']:+.2%}) | MaxDD: {r['max_dd']:.2%}")

    if a.split:
        mid = len(rows) // 2
        r1 = simulate(rows[:mid], period=a.period, ob=a.ob, os_=a.os, **base)
        r2 = simulate(rows[mid:], period=a.period, ob=a.ob, os_=a.os, **base)
        rf = simulate(rows, period=a.period, ob=a.ob, os_=a.os, **base)
        show(r1, "1ª metade")
        show(r2, "2ª metade")
        show(rf, "total")
        be = 1 / (1 + a.payout)
        n, wr = rf["trades"], rf["winrate"]
        se = math.sqrt(wr * (1 - wr) / n) if n else 1.0
        lower = wr - 1.96 * se
        checks = [(f"trades >= 200 ({n})", n >= 200),
                  (f"WR inf.95% {lower:.2%} > breakeven {be:.2%}", lower > be),
                  (f"lucro 1ª metade > 0 ({r1['profit']:+.2f})", r1["profit"] > 0),
                  (f"lucro 2ª metade > 0 ({r2['profit']:+.2f})", r2["profit"] > 0)]
        print("\n[VEREDITO anti-ilusão]")
        ok_all = True
        for label, ok in checks:
            print(f"  {'PASS' if ok else 'FAIL'}  {label}")
            ok_all = ok_all and ok
        print("  => EDGE VALIDADO" if ok_all else "  => SEM EDGE (não opera real)")
        return

    if a.grid:
        best = None
        for per in (10, 14, 21):
            for ob in (65, 70, 75):
                for os_ in (25, 30, 35):
                    r = simulate(rows, period=per, ob=ob, os_=os_, **base)
                    tag = f"[{a.mode}] RSI{per} {os_}/{ob}: trades={r['trades']} wr={r['winrate']:.2f} lucro={r['profit']:+.2f} dd={r['max_dd']:.1%}"
                    print(tag)
                    if r["trades"] >= 20 and (best is None or r["profit"] > best[1]["profit"]):
                        best = (f"RSI{per} {os_}/{ob}", r)
        if best:
            print(f"\n[MELHOR] {best[0]} lucro={best[1]['profit']:+.2f} wr={best[1]['winrate']:.2f}")
        return

    r = simulate(rows, period=a.period, ob=a.ob, os_=a.os, **base)
    print(f"Trades: {r['trades']} | W/L/T: {r['wins']}/{r['losses']}/{r['ties']} | "
          f"WR: {r['winrate']:.2%} | Lucro: {r['profit']:+.2f} | "
          f"{r['start']:.2f}->{r['end']:.2f} ({r['roi']:+.2%}) | MaxDD: {r['max_dd']:.2%}")
    if a.out and r["rows"]:
        with open(a.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(r["rows"][0].keys()))
            w.writeheader()
            w.writerows(r["rows"])
        print(f"[OK] trades -> {a.out}")


if __name__ == "__main__":
    main()
