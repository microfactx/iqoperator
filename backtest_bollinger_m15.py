"""Hunter BTC M15 1y: Bollinger Bands
p=10,20,30,50 mult=1.2,1.5,2.0,2.5 exp=15/30/60m payout 0.87/0.90
IS 70% -> rank por lucro Kelly, OOS 30% -> veredito Wilson > BE + lucro>0
"""
import csv, math, os, sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kelly import kelly_fraction_stake
from backtest import ema_list

def load_m15(path):
    t,o,h,l,c=[],[],[],[],[]
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try: v=int(float(r["time"]))
            except: continue
            if v >= 10**15: v//=1000
            elif v < 10_000_000_000: v*=1000
            t.append(v); o.append(float(r["open"])); h.append(float(r["high"])); l.append(float(r["low"])); c.append(float(r["close"]))
    return {"t":t,"o":o,"h":h,"l":l,"c":c}

def sma(xs, p):
    out=[None]*len(xs); s=0.0
    for i,x in enumerate(xs):
        s+=x
        if i>=p: s-=xs[i-p]
        if i>=p-1: out[i]=s/p
    return out

def std_dev(xs, p):
    """Rolling standard deviation"""
    out=[None]*len(xs)
    for i in range(p-1, len(xs)):
        window = xs[i-p+1:i+1]
        if len(window) == p:
            mean = sum(window)/p
            var = sum((x-mean)**2 for x in window)/p
            out[i] = math.sqrt(var)
    return out

def bollinger_signals(d, p, mult):
    """Bollinger Bands: CALL when close < lower band, PUT when close > upper band"""
    c = d["c"]
    basis = sma(c, p)
    std = std_dev(c, p)
    sig = []
    for i in range(p, len(c)-1):
        if basis[i] is None or std[i] is None or std[i] == 0:
            continue
        upper = basis[i] + mult * std[i]
        lower = basis[i] - mult * std[i]
        if c[i] < lower:
            sig.append((i, "call"))
        elif c[i] > upper:
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
        wins += won
        losses += (not won)
        peak = max(peak, bal)
        max_dd = max(max_dd, (peak - bal) / peak if peak else 0)
    tot = wins + losses
    return {"trades": tot, "wins": wins, "wr": wins/tot if tot else 0.0,
            "profit": round(bal - balance, 2), "bal": round(bal, 2), "max_dd": round(max_dd, 4)}

def wilson(wins, n, z=1.96):
    if not n: return 0.0
    p = wins / n
    d = 1 + z*z / n
    return (p + z*z/(2*n) - z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / d

path = "data/BTCUSDT_M15_1y.csv"
d = load_m15(path)
n = len(d["c"])
cut = int(n * 0.70)
print(f"[DATA] {path} n={n} IS:{cut} OOS:{n-cut} ({cut/n:.0%}/{1-cut/n:.0%})")
print(f"[RANGE] {d['t'][0]} -> {d['t'][-1]}")

periods = [10, 20, 30, 50]
mults = [1.2, 1.5, 2.0, 2.5]
exps = [1, 2, 4]  # 15, 30, 60m in bars
payouts = [0.87, 0.90]

all_results = []
for p in periods:
    for m in mults:
        for exp in exps:
            signals = bollinger_signals(d, p, m)
            sig_is = [(i, s) for i, s in signals if i < cut]
            sig_oos = [(i, s) for i, s in signals if i >= cut]
            for payout in payouts:
                r_is = run(sig_is, d["c"], 1000.0, exp, payout)
                r_oos = run(sig_oos, d["c"], 1000.0, exp, payout)
                be = 1 / (1 + payout)
                w_low_is = wilson(r_is["wins"], r_is["trades"])
                w_low_oos = wilson(r_oos["wins"], r_oos["trades"])
                ok_oos = (r_oos["trades"] >= 50 and w_low_oos > be and r_oos["profit"] > 0)
                all_results.append({
                    "p": p, "mult": m, "exp": exp, "exp_m": exp * 15, "payout": payout, "be": be,
                    "is_trades": r_is["trades"], "is_wr": r_is["wr"], "is_profit": r_is["profit"],
                    "is_dd": r_is["max_dd"], "is_wlow": w_low_is, "is_wins": r_is["wins"],
                    "oos_trades": r_oos["trades"], "oos_wr": r_oos["wr"], "oos_profit": r_oos["profit"],
                    "oos_dd": r_oos["max_dd"], "oos_wlow": w_low_oos, "oos_wins": r_oos["wins"],
                    "oos_ok": ok_oos
                })

# ---- Ranking IS por payout ----
for payout in payouts:
    be = 1 / (1 + payout)
    print(f"\n{'='*110}")
    print(f" PAYOUT {payout} (BE {be:.2%}) — RANKING IS (70%) POR LUCRO KELLY — TOP 15 de {len([r for r in all_results if r['payout']==payout])} configs")
    print(f"{'='*110}")
    subset = [r for r in all_results if r["payout"] == payout]
    subset_sorted = sorted(subset, key=lambda x: x["is_profit"], reverse=True)
    header = f"{'#':<3} {'p':<4} {'mult':<5} {'exp':<6} {'IS n':<6} {'IS WR':<7} {'IS Wlow':<8} {'IS lucro':<9} {'IS DD':<7} | {'OOS n':<6} {'OOS WR':<7} {'OOS Wlow':<8} {'OOS lucro':<10} {'OOS DD':<7} VERED"
    print(header)
    print("-" * len(header))
    for idx, r in enumerate(subset_sorted[:15], 1):
        ver = "PASS" if r["oos_ok"] else "FAIL"
        print(f"{idx:<3} {r['p']:<4} {r['mult']:<5} {r['exp_m']:<6} {r['is_trades']:<6} {r['is_wr']:<7.2%} {r['is_wlow']:<8.2%} {r['is_profit']:<9.2f} {r['is_dd']:<7.2%} | {r['oos_trades']:<6} {r['oos_wr']:<7.2%} {r['oos_wlow']:<8.2%} {r['oos_profit']:<10.2f} {r['oos_dd']:<7.2%} {ver}")

    # TOP IS filtrado trades >= 50
    print(f"\n  [TOP IS filtrado trades>=50 payout {payout}]")
    filt = [r for r in subset_sorted if r["is_trades"] >= 50]
    for idx, r in enumerate(filt[:5], 1):
        ver = "PASS" if r["oos_ok"] else "FAIL"
        print(f"   {idx}. p{r['p']} mult{r['mult']} exp{r['exp_m']}m | IS n={r['is_trades']} WR={r['is_wr']:.2%} (Wlow {r['is_wlow']:.2%} vs BE {be:.2%}) lucro {r['is_profit']:+.2f} DD {r['is_dd']:.2%}  -> OOS n={r['oos_trades']} WR={r['oos_wr']:.2%} Wlow {r['oos_wlow']:.2%} lucro {r['oos_profit']:+.2f} {ver}")

# ---- Ranking global OOS ----
print(f"\n{'='*110}")
print(" RANKING OOS (ordem por lucro OOS) — TOP 10 GLOBAL (ambos payouts)")
print(f"{'='*110}")
global_sorted = sorted(all_results, key=lambda x: x["oos_profit"], reverse=True)
for idx, r in enumerate(global_sorted[:10], 1):
    print(f"{idx}. p{r['p']} m{r['mult']} exp{r['exp_m']}m payout{r['payout']} | OOS lucro {r['oos_profit']:+.2f} n={r['oos_trades']} WR={r['oos_wr']:.2%} Wlow {r['oos_wlow']:.2%} BE {r['be']:.2%} | IS lucro {r['is_profit']:+.2f} WR {r['is_wr']:.2%}")

# ---- Resumo edge válido ----
print(f"\n{'='*110}")
print(" RESUMO VEREDITO OOS (n>=50 & Wlow>BE & lucro>0)")
print(f"{'='*110}")
valid = [r for r in all_results if r["oos_ok"]]
print(f"Configs válidas OOS: {len(valid)}/{len(all_results)}")
for r in sorted(valid, key=lambda x: x["oos_profit"], reverse=True)[:10]:
    print(f"  VALID p{r['p']} m{r['mult']} exp{r['exp_m']}m payout{r['payout']} OOS lucro {r['oos_profit']:+.2f} WR {r['oos_wr']:.2%} Wlow {r['oos_wlow']:.2%} BE {r['be']:.2%} n={r['oos_trades']} | IS lucro {r['is_profit']:+.2f} WR {r['is_wr']:.2%}")

# ---- tabela CSV ----
import csv as csvm
with open("data/hunter_bollinger_m15_top.csv", "w", newline="", encoding="utf-8") as f:
    w = csvm.writer(f)
    w.writerow(["p", "mult", "exp_m", "payout", "be",
                "is_trades", "is_wr", "is_wlow", "is_profit", "is_dd",
                "oos_trades", "oos_wr", "oos_wlow", "oos_profit", "oos_dd", "veredito"])
    for r in sorted(all_results, key=lambda x: x["is_profit"], reverse=True):
        w.writerow([r["p"], r["mult"], r["exp_m"], r["payout"], round(r["be"], 4),
                    r["is_trades"], round(r["is_wr"], 4), round(r["is_wlow"], 4), r["is_profit"], r["is_dd"],
                    r["oos_trades"], round(r["oos_wr"], 4), round(r["oos_wlow"], 4), r["oos_profit"], r["oos_dd"],
                    "PASS" if r["oos_ok"] else "FAIL"])
print("\n[CSV] data/hunter_bollinger_m15_top.csv gerado")