"""Hunter BTC M15 1y - Donchian Fade exhaustive search
n=10,15,20,30,40,60,100 exp 15/30/45/60m payout 0.87/0.90
Usa motor de research/grid_families.py (Kelly, Wilson, IS 70% / OOS 30%)
"""
import os, sys, math, csv
from collections import deque
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kelly import kelly_fraction_stake
from research.grid_families import load_m15, fam_donchian_fade, wilson

# params solicitados
N_LIST = (10, 15, 20, 30, 40, 60, 100)
EXPIRIES = (1, 2, 3, 4)  # 15m, 30m, 45m, 60m em M15
PAYOUTS = (0.87, 0.90)
DATA = "data/BTCUSDT_M15_1y.csv"

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
    return {"trades": tot, "wins": wins, "wr": wins/tot if tot else 0.0,
            "profit": round(bal - balance, 2), "max_dd": round(max_dd,4)}

def main():
    d = load_m15(DATA)
    c = d["c"]
    n_total = len(c)
    cut = int(n_total*0.70)
    print(f"[DATA] {DATA}: {n_total} M15 | IS:0..{cut-1} ({cut}) OOS:{cut}..{n_total-1} ({n_total-cut})")
    print(f"[GRID] n={N_LIST} exp={EXPIRIES} payout={PAYOUTS}")
    total_configs = len(N_LIST)*len(EXPIRIES)*len(PAYOUTS)
    print(f"[CONTAGEM] configs={total_configs}")
    for payout in PAYOUTS:
        BE = 1/(1+payout)
        print(f"\n{'='*80}")
        print(f"PAYOUT {payout:.2f}  BE {BE:.2%}  (z=1.96 Wilson)")
        print(f"{'='*80}")
        rows = []
        for n in N_LIST:
            sig_all = fam_donchian_fade(d, n=n)
            sig_is_all = [(i,s) for i,s in sig_all if i < cut]
            sig_oos_all = [(i,s) for i,s in sig_all if i >= cut]
            for exp in EXPIRIES:
                r_is = run(sig_is_all, c, 1000.0, exp, payout)
                r_oos = run(sig_oos_all, c, 1000.0, exp, payout)
                w_is = wilson(r_is["wins"], r_is["trades"])
                w_oos = wilson(r_oos["wins"], r_oos["trades"])
                exp_m = exp*15
                checks = (r_oos["trades"]>=50, w_oos>BE, r_oos["profit"]>0)
                ok_oos = all(checks)
                rows.append({
                    "n":n,"exp":exp,"exp_m":exp_m,
                    "r_is":r_is,"r_oos":r_oos,"w_is":w_is,"w_oos":w_oos,
                    "ok_oos":ok_oos,"BE":BE
                })
        # ordena por lucro IS desc
        rows_sorted = sorted(rows, key=lambda x: x["r_is"]["profit"], reverse=True)

        print(f"\n[TOP 5 IS por LUCRO] payout={payout:.2f}")
        header = "{:<3} {:<30} {:<10} {:<6} {:<7} {:<10} {:<11} {:<6} {:<7} {:<11} {:<9} {}"
        print(header.format("#", "cfg", "IS profit", "IS n", "IS WR", "IS Wilson", "OOS profit", "OOS n", "OOS WR", "OOS Wilson", "vs BE", "OOS verdict"))
        for idx, r in enumerate(rows_sorted[:5],1):
            cfg = f"donchian_fade n={r['n']} exp={r['exp_m']}m"
            is_ = r["r_is"]; oos=r["r_oos"]
            print(header.format(idx, cfg, f"{is_['profit']:+.2f}", is_["trades"], f"{is_['wr']:.2%}", f"{r['w_is']:.2%}", f"{oos['profit']:+.2f}", oos["trades"], f"{oos['wr']:.2%}", f"{r['w_oos']:.2%}", f"{r['w_oos']-r['BE']:+.2%}", "PASS" if r["ok_oos"] else "FAIL"))

        # Top5 OOS por Wilson (melhor lower bound)
        rows_oos_wilson = sorted(rows, key=lambda x: x["w_oos"], reverse=True)
        print(f"\n[TOP 5 OOS por WILSON] payout={payout:.2f}")
        header2 = "{:<3} {:<30} {:<11} {:<6} {:<7} {:<11} {:<9} {:<10} {:<10} {}"
        print(header2.format("#", "cfg", "OOS Wilson", "OOS n", "OOS WR", "OOS profit", "vs BE", "IS profit", "IS Wilson", "OOS verdict"))
        for idx, r in enumerate(rows_oos_wilson[:5],1):
            cfg = f"donchian_fade n={r['n']} exp={r['exp_m']}m"
            print(header2.format(idx, cfg, f"{r['w_oos']:.2%}", r["r_oos"]["trades"], f"{r['r_oos']['wr']:.2%}", f"{r['r_oos']['profit']:+.2f}", f"{r['w_oos']-r['BE']:+.2%}", f"{r['r_is']['profit']:+.2f}", f"{r['w_is']:.2%}", "PASS" if r["ok_oos"] else "FAIL"))

        # Sumario
        passes = sum(1 for r in rows if r["ok_oos"])
        print(f"\n[SUMARIO payout={payout:.2f}] PASS OOS (trades>=50 & Wilson>BE & lucro>0): {passes}/{len(rows)}")
        if passes==0:
            print("  -> NENHUM config sobrevive a IS->OOS com criterio Wilson. Melhor OOS Wilson:")
            best = max(rows, key=lambda x: x["w_oos"])
            print(f"     n={best['n']} exp={best['exp_m']}m | OOS Wilson {best['w_oos']:.2%} vs BE {best['BE']:.2%} gap {best['w_oos']-best['BE']:+.2%} n={best['r_oos']['trades']} WR={best['r_oos']['wr']:.2%} lucro={best['r_oos']['profit']:+.2f} | IS lucro={best['r_is']['profit']:+.2f} Wilson {best['w_is']:.2%}")
            print("  -> VEREDICTO OOS: FAIL - Wilson nao supera BE")
        else:
            print("  -> VEREDICTO OOS: PASS - Existem configs com Wilson > BE")

if __name__=="__main__":
    main()