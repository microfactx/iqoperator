"""Grade de famílias novas (linhas diferentes de RSI): IS -> OOS -> ano fresco.

Famílias: donchian breakout, bollinger reversão, stretch ATR, ignição momentum, wick rejection.
Motor único: mesmo Kelly, mesmo outcome binário, payout 0.87 (BE 53.48%).
Conta global de configs p/ consciência de mineração de dados.

Uso:
  py research/grid_families.py            (IS + OOS, todas as famílias)
  py research/grid_families.py --confirm  (só confirma vencedores OOS no ano fresco)
"""
import argparse
import csv
import math
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kelly import kelly_fraction_stake

PAYOUT = 0.87
BE = 1 / (1 + PAYOUT)
TOTAL_CONFIGS = [0]


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
            o.append(float(r["open"])); h.append(float(r["high"]))
            l.append(float(r["low"])); c.append(float(r["close"]))
    return {"t": t, "o": o, "h": h, "l": l, "c": c}


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
        w = xs[i - p + 1:i + 1]
        m = sum(w) / p
        out[i] = math.sqrt(sum((x - m) ** 2 for x in w) / p)
    return out


def atr(h, l, c, p):
    trs = [h[0] - l[0]]
    for i in range(1, len(c)):
        trs.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    out, s = [None] * len(c), sum(trs[:p]) / p
    out[p - 1] = s
    for i in range(p, len(c)):
        s = (s * (p - 1) + trs[i]) / p
        out[i] = s
    return out


# ---- famílias: cada uma retorna lista de (índice, 'call'/'put') ----
def fam_donchian(d, n, **kw):
    h, l, c = d["h"], d["l"], d["c"]
    sig = []
    for i in range(n, len(c) - 1):
        hi = max(h[i - n:i])
        lo = min(l[i - n:i])
        if c[i] > hi:
            sig.append((i, "call"))
        elif c[i] < lo:
            sig.append((i, "put"))
    return sig


def fam_boll(d, p, mult, **kw):
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


def fam_stretch(d, p, mult, **kw):
    c = d["c"]
    basis = sma(c, p)
    va = atr(d["h"], d["l"], c, 14)
    sig = []
    for i in range(max(p, 14), len(c) - 1):
        if basis[i] is None or va[i] is None:
            continue
        if c[i] < basis[i] - mult * va[i]:
            sig.append((i, "call"))
        elif c[i] > basis[i] + mult * va[i]:
            sig.append((i, "put"))
    return sig


def fam_ignition(d, n, **kw):
    c = d["c"]
    sig = []
    for i in range(n, len(c) - 1):
        up = all(c[j] > c[j - 1] for j in range(i - n + 1, i + 1))
        dn = all(c[j] < c[j - 1] for j in range(i - n + 1, i + 1))
        if up:
            sig.append((i, "call"))
        elif dn:
            sig.append((i, "put"))
    return sig


def fam_wick(d, thr, **kw):
    o, h, l, c = d["o"], d["h"], d["l"], d["c"]
    sig = []
    for i in range(1, len(c) - 1):
        rng = h[i] - l[i]
        if rng <= 0:
            continue
        body = abs(c[i] - o[i])
        upper = (h[i] - max(o[i], c[i])) / rng
        lower = (min(o[i], c[i]) - l[i]) / rng
        # rejeição de baixo + corpo pequeno -> call; de cima -> put
        if lower >= thr and body / rng < 0.5:
            sig.append((i, "call"))
        elif upper >= thr and body / rng < 0.5:
            sig.append((i, "put"))
    return sig


def fam_donchian_fade(d, n, **kw):
    """Fade do rompimento: toca a banda e volta (oposto do breakout)."""
    h, l, c = d["h"], d["l"], d["c"]
    sig = []
    for i in range(n, len(c) - 1):
        hi = max(h[i - n:i])
        lo = min(l[i - n:i])
        if c[i] > hi:
            sig.append((i, "put"))
        elif c[i] < lo:
            sig.append((i, "call"))
    return sig


def fam_boll_atr(d, p, mult, regime, **kw):
    c = d["c"]
    basis, sd = sma(c, p), stdev(c, p)
    va = atr(d["h"], d["l"], c, 14)
    vals = [x for x in va if x is not None]
    med = sorted(vals)[len(vals) // 2]
    sig = []
    for i in range(max(p, 14), len(c) - 1):
        if basis[i] is None or va[i] is None:
            continue
        hot = va[i] > med
        if regime == "high" and not hot:
            continue
        if regime == "low" and hot:
            continue
        if c[i] < basis[i] - mult * sd[i]:
            sig.append((i, "call"))
        elif c[i] > basis[i] + mult * sd[i]:
            sig.append((i, "put"))
    return sig


def fam_rsi_boll(d, per, **kw):
    from backtest import rsi_list
    c = d["c"]
    rsi = rsi_list(c, per)
    basis, sd = sma(c, 20), stdev(c, 20)
    sig = []
    for i in range(20, len(c) - 1):
        r = rsi[i]
        if r is None or (isinstance(r, float) and math.isnan(r)):
            continue
        if basis[i] is None:
            continue
        if r < 30 and c[i] < basis[i] - 2.0 * sd[i]:
            sig.append((i, "call"))
        elif r > 70 and c[i] > basis[i] + 2.0 * sd[i]:
            sig.append((i, "put"))
    return sig


def fam_wick_trend(d, thr, use_trend, **kw):
    o, h, l, c = d["o"], d["h"], d["l"], d["c"]
    tr = sma(c, 50)
    sig = []
    for i in range(50, len(c) - 1):
        rng = h[i] - l[i]
        if rng <= 0:
            continue
        body = abs(c[i] - o[i])
        upper = (h[i] - max(o[i], c[i])) / rng
        lower = (min(o[i], c[i]) - l[i]) / rng
        if use_trend:
            if lower >= thr and body / rng < 0.5 and c[i] > tr[i]:
                sig.append((i, "call"))
            elif upper >= thr and body / rng < 0.5 and c[i] < tr[i]:
                sig.append((i, "put"))
        else:
            if lower >= thr and body / rng < 0.5:
                sig.append((i, "call"))
            elif upper >= thr and body / rng < 0.5:
                sig.append((i, "put"))
    return sig


FAMILIES = {
    "donchian": (fam_donchian, [{"n": n} for n in (20, 40, 60)]),
    "boll": (fam_boll, [{"p": p, "mult": m} for p in (20, 50) for m in (1.5, 2.0)]),
    "stretch": (fam_stretch, [{"p": p, "mult": m} for p in (50, 200) for m in (1.5, 2.0, 2.5)]),
    "ignition": (fam_ignition, [{"n": n} for n in (3, 4, 5)]),
    "wick": (fam_wick, [{"thr": t} for t in (0.4, 0.5, 0.6)]),
}

WAVE2 = {
    "donchian_fade": (fam_donchian_fade, [{"n": n} for n in (20, 40, 60)]),
    "boll_atr": (fam_boll_atr, [{"p": 20, "mult": 2.0, "regime": r} for r in ("high", "low")]),
    "rsi_boll": (fam_rsi_boll, [{"per": p} for p in (10, 14)]),
    "wick_trend": (fam_wick_trend, [{"thr": 0.5, "use_trend": u} for u in (True, False)]),
}
EXPIRIES = (1, 2)


def run(signals, closes, balance, expiry):
    bal, peak, max_dd = balance, balance, 0.0
    hist: deque[bool] = deque(maxlen=50)
    wins = losses = 0
    for i, side in signals:
        if i + expiry >= len(closes):
            continue
        n = len(hist)
        p = (0.58 * 20 + sum(1 for w in hist if w)) / (20 + n) if n else 0.58
        stake, _ = kelly_fraction_stake(bal, PAYOUT, p, 0.25, 0.02, 1.0)
        entry, nxt = closes[i], closes[i + expiry]
        if nxt == entry:
            continue
        won = (side == "call") == (nxt > entry)
        bal += stake * PAYOUT if won else -stake
        hist.append(won)
        wins, losses = wins + won, losses + (not won)
        peak = max(peak, bal)
        max_dd = max(max_dd, (peak - bal) / peak if peak else 0)
    tot = wins + losses
    return {"trades": tot, "wins": wins, "wr": wins / tot if tot else 0.0,
            "profit": round(bal - balance, 2), "max_dd": round(max_dd, 4)}


def wilson(wins, n, z=1.96):
    if not n:
        return 0.0
    p = wins / n
    d = 1 + z * z / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


def verdict(r):
    low = wilson(r["wins"], r["trades"])
    checks = [(f"trades >= 50 ({r['trades']})", r["trades"] >= 50),
              (f"Wilson {low:.2%} > BE {BE:.2%}", low > BE),
              (f"lucro > 0 ({r['profit']:+.2f})", r["profit"] > 0)]
    return all(ok for _, ok in checks), checks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", type=int, default=0)
    ap.add_argument("--wave", default="2", choices=["1", "2"])
    ap.add_argument("--y1", default="data/BTCUSDT_M15_1y.csv")
    ap.add_argument("--y0", default="data/BTCUSDT_M15_2024y.csv")
    a = ap.parse_args()

    d1 = load_m15(a.y1)
    cut = int(len(d1["c"]) * 0.70)
    print(f"[DATA] ano1: {len(d1['c'])} M15 | IS:{cut} OOS:{len(d1['c'])-cut}")
    fams = WAVE2 if a.wave == "2" else FAMILIES
    winners = []
    for fam, (fn, grid) in fams.items():
        best = None
        for kw in grid:
            for exp in EXPIRIES:
                TOTAL_CONFIGS[0] += 1
                sig_all = fn(d1, **kw)
                sig_is = [(i, s) for i, s in sig_all if i < cut]
                r = run(sig_is, d1["c"], 1000.0, exp)
                tag = f"{fam} {kw} exp={exp*15}m"
                print(f"  {tag}: n={r['trades']} WR={r['wr']:.2%} lucro={r['profit']:+.2f}")
                if r["trades"] >= 25 and (best is None or r["profit"] > best[2]["profit"]):
                    best = (tag, (kw, exp), r)
        print(f"[TOP-IS {fam}] {best[0]}: lucro={best[2]['profit']:+.2f} "
              f"WR={best[2]['wr']:.2%} n={best[2]['trades']}")
        (kw, exp) = best[1]
        sig_oos = [(i, s) for i, s in fn(d1, **kw) if i >= cut]
        r_oos = run(sig_oos, d1["c"], 1000.0, exp)
        ok, checks = verdict(r_oos)
        print(f"[OOS {fam}] n={r_oos['trades']} WR={r_oos['wr']:.2%} "
              f"lucro={r_oos['profit']:+.2f} => {'PASS' if ok else 'FAIL'}")
        for label, good in checks:
            print(f"    {'PASS' if good else 'FAIL'}  {label}")
        if ok:
            winners.append((fam, best[0], kw, exp))
    print(f"\n[CONFIGS TESTADAS (acumulado sessão): {TOTAL_CONFIGS[0]}]")
    print(f"[VENCEDORAS OOS: {len(winners)}]")

    if a.confirm and winners and os.path.exists(a.y0):
        d0 = load_m15(a.y0)
        print(f"\n== CONFIRMAÇÃO ANO FRESCO ({len(d0['c'])} M15) ==")
        for fam, tag, kw, exp in winners:
            fn = fams[fam][0]
            sig = fn(d0, **kw)
            r = run(sig, d0["c"], 1000.0, exp)
            ok, checks = verdict(r)
            print(f"[FRESCO {fam}] {tag}: n={r['trades']} WR={r['wr']:.2%} "
                  f"lucro={r['profit']:+.2f} => {'GREEN' if ok else 'FAIL'}")
            for label, good in checks:
                print(f"    {'PASS' if good else 'FAIL'}  {label}")


if __name__ == "__main__":
    main()
