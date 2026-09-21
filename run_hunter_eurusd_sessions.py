"""Hunter EURUSD M15 histdata 40000: filtro sessão Londres 08-12 NY 13-17 overlap 08-17.
Famílias boll p=20 mult=1.5 e donchian_fade n=20 exp 15/30m.
Payout 0.90 BE 52.63%. Retorne top IS/OOS por sessão.

Uso:
  py run_hunter_eurusd_sessions.py
"""
import csv
import math
import os
import sys
from collections import Counter, deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kelly import kelly_fraction_stake

# Configurações
PAYOUT = 0.90
BE = 1 / (1 + PAYOUT)  # 52.63%
IS_RATIO = 0.70
EXPIRIES = (1, 2)  # 15m, 30m em barras M15
BALANCE = 1000.0

# Sessões UTC
SESSIONS = {
    "london": (8, 12),      # 08:00-11:59
    "ny": (13, 17),         # 13:00-16:59
    "overlap": (8, 17),     # 08:00-16:59
}


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


def filter_session(data, session_name):
    """Filtra barras que caem na sessão especificada."""
    start_h, end_h = SESSIONS[session_name]
    t, o, h, l, c = data["t"], data["o"], data["h"], data["l"], data["c"]
    idx = []
    for i, ts in enumerate(t):
        # Converter para UTC hour
        dt = ts // 1000
        hour = (dt // 3600) % 24
        if start_h <= hour < end_h:
            idx.append(i)
    if not idx:
        return {"t": [], "o": [], "h": [], "l": [], "c": [], "orig_idx": []}
    return {
        "t": [t[i] for i in idx],
        "o": [o[i] for i in idx],
        "h": [h[i] for i in idx],
        "l": [l[i] for i in idx],
        "c": [c[i] for i in idx],
        "orig_idx": idx,  # índices originais para referência
    }


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


# ---- Famílias ----

def fam_boll(d, p, mult):
    """Bollinger reversão: close < lower -> CALL, close > upper -> PUT."""
    c = d["c"]
    basis, sd = sma(c, p), stdev(c, p)
    sig = []
    for i in range(p, len(c) - 1):
        if basis[i] is None or sd[i] is None or sd[i] == 0:
            continue
        if c[i] < basis[i] - mult * sd[i]:
            sig.append((i, "call"))
        elif c[i] > basis[i] + mult * sd[i]:
            sig.append((i, "put"))
    return sig


def fam_donchian_fade(d, n):
    """Donchian Fade: toca a banda e volta (oposto do breakout).
    close > high n -> PUT; close < low n -> CALL."""
    h, l, c = d["h"], d["l"], d["c"]
    sig = []
    for i in range(n, len(c) - 1):
        hi = max(h[i - n : i])
        lo = min(l[i - n : i])
        if c[i] > hi:
            sig.append((i, "put"))
        elif c[i] < lo:
            sig.append((i, "call"))
    return sig


def run(signals, closes, balance, expiry, payout):
    """Executa backtest com Kelly."""
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


def run_session(data, session_name):
    """Executa backtest completo para uma sessão."""
    sd = filter_session(data, session_name)
    if len(sd["c"]) < 100:
        print(f"  [AVISO] {session_name}: apenas {len(sd['c'])} barras")
        return []

    n_total = len(sd["c"])
    cut = int(n_total * IS_RATIO)
    print(f"  [{session_name}] {n_total} barras M15 | IS:0..{cut-1} ({cut}) OOS:{cut}..{n_total-1} ({n_total-cut})")

    results = []

    # Bollinger p=20 mult=1.5
    print(f"  Testando Bollinger p=20 mult=1.5...")
    sig_all = fam_boll(sd, p=20, mult=1.5)
    sig_is = [(i, s) for i, s in sig_all if i < cut]
    sig_oos = [(i, s) for i, s in sig_all if i >= cut]
    for exp in EXPIRIES:
        r_is = run(sig_is, sd["c"], BALANCE, exp, PAYOUT)
        r_oos = run(sig_oos, sd["c"], BALANCE, exp, PAYOUT)
        w_is = wilson(r_is["wins"], r_is["trades"])
        w_oos = wilson(r_oos["wins"], r_oos["trades"])
        checks = (r_oos["trades"] >= 50, w_oos > BE, r_oos["profit"] > 0)
        ok_oos = all(checks)
        results.append({
            "session": session_name,
            "family": "boll",
            "params": f"p=20 mult=1.5",
            "exp": exp,
            "exp_m": exp * 15,
            "r_is": r_is,
            "r_oos": r_oos,
            "w_is": w_is,
            "w_oos": w_oos,
            "ok_oos": ok_oos,
            "BE": BE,
        })

    # Donchian Fade n=20
    print(f"  Testando Donchian Fade n=20...")
    sig_all = fam_donchian_fade(sd, n=20)
    sig_is = [(i, s) for i, s in sig_all if i < cut]
    sig_oos = [(i, s) for i, s in sig_all if i >= cut]
    for exp in EXPIRIES:
        r_is = run(sig_is, sd["c"], BALANCE, exp, PAYOUT)
        r_oos = run(sig_oos, sd["c"], BALANCE, exp, PAYOUT)
        w_is = wilson(r_is["wins"], r_is["trades"])
        w_oos = wilson(r_oos["wins"], r_oos["trades"])
        checks = (r_oos["trades"] >= 50, w_oos > BE, r_oos["profit"] > 0)
        ok_oos = all(checks)
        results.append({
            "session": session_name,
            "family": "donchian_fade",
            "params": f"n=20",
            "exp": exp,
            "exp_m": exp * 15,
            "r_is": r_is,
            "r_oos": r_oos,
            "w_is": w_is,
            "w_oos": w_oos,
            "ok_oos": ok_oos,
            "BE": BE,
        })

    return results


def print_top(results, session_name, sort_key, title, limit=3):
    """Imprime top N ordenado por sort_key."""
    filtered = [r for r in results if r["session"] == session_name]
    if not filtered:
        return
    sorted_r = sorted(filtered, key=sort_key, reverse=True)
    print(f"\n=== {session_name.upper()} - {title} (TOP {limit}) ===")
    print(f"{'#':<3} {'Config':<40} {'IS n':<6} {'IS WR':<7} {'IS Wlow':<9} {'IS P&L':<9} | {'OOS n':<6} {'OOS WR':<7} {'OOS Wlow':<9} {'OOS P&L':<9} {'vs BE':<8} {'Verdict'}")
    for idx, r in enumerate(sorted_r[:limit], 1):
        cfg = f"{r['family']} {r['params']} exp={r['exp_m']}m"
        is_ = r["r_is"]
        oos = r["r_oos"]
        print(
            f"{idx:<3} {cfg:<40} {is_['trades']:<6} {is_['wr']:.2%}  {r['w_is']:.2%}     {is_['profit']:+8.2f}   | "
            f"{oos['trades']:<6} {oos['wr']:.2%}  {r['w_oos']:.2%}     {oos['profit']:+8.2f}   "
            f"{r['w_oos']-r['BE']:+.2%}   {'PASS' if r['ok_oos'] else 'FAIL'}"
        )


def main():
    print(f"[CONFIG] PAYOUT={PAYOUT:.2f} BE={BE:.2%} IS={IS_RATIO:.0%}/OOS={1-IS_RATIO:.0%} Expiries={EXPIRIES}")
    print(f"[SESSIONS] London 08-12, NY 13-17, Overlap 08-17 (UTC)")

    # Carrega dados
    data = load_m15("data/EURUSD_M15_histdata.csv")
    print(f"[DATA] EURUSD_M15_histdata: {len(data['c'])} barras M15")

    all_results = []

    # Roda para cada sessão
    for session_name in ["london", "ny", "overlap"]:
        results = run_session(data, session_name)
        all_results.extend(results)

    # Top por sessão
    for session_name in ["london", "ny", "overlap"]:
        # Top 3 IS por lucro
        print_top(
            all_results,
            session_name,
            lambda x: x["r_is"]["profit"],
            "TOP IS por LUCRO",
        )
        # Top 3 OOS por Wilson
        print_top(
            all_results,
            session_name,
            lambda x: x["w_oos"],
            "TOP OOS por WILSON",
        )
        # Top 3 OOS por lucro
        print_top(
            all_results,
            session_name,
            lambda x: x["r_oos"]["profit"],
            "TOP OOS por LUCRO",
        )

    # Sumário global
    print(f"\n{'='*80}")
    print("SUMÁRIO GERAL")
    print(f"{'='*80}")
    passes = sum(1 for r in all_results if r["ok_oos"])
    print(f"Configs testadas: {len(all_results)} | PASS OOS: {passes}/{len(all_results)}")
    print(f"BE = {BE:.2%} | Critério OOS: trades>=50 & Wilson>BE & lucro>0")

    if passes > 0:
        print("\n[CONFIGS QUE PASSAM OOS]")
        for r in sorted([r for r in all_results if r["ok_oos"]], key=lambda x: x["r_oos"]["profit"], reverse=True):
            cfg = f"{r['session']} {r['family']} {r['params']} exp={r['exp_m']}m"
            print(f"  PASS {cfg} | OOS n={r['r_oos']['trades']} WR={r['r_oos']['wr']:.2%} Wlow={r['w_oos']:.2%} P&L={r['r_oos']['profit']:+.2f} | IS P&L={r['r_is']['profit']:+.2f}")
    else:
        print("\n[NENHUM CONFIG PASSA OOS]")
        for session_name in ["london", "ny", "overlap"]:
            filtered = [r for r in all_results if r["session"] == session_name]
            if filtered:
                best = max(filtered, key=lambda x: x["w_oos"])
                cfg = f"{best['session']} {best['family']} {best['params']} exp={best['exp_m']}m"
                print(f"  Melhor {session_name}: {cfg} | OOS Wilson={best['w_oos']:.2%} vs BE={best['BE']:.2%} gap={best['w_oos']-best['BE']:+.2%} n={best['r_oos']['trades']} P&L={best['r_oos']['profit']:+.2f}")

    # Exporta CSV
    import csv as csvm
    with open("data/hunter_eurusd_sessions_top.csv", "w", newline="", encoding="utf-8") as f:
        w = csvm.writer(f)
        w.writerow([
            "session", "family", "params", "exp_m", "payout", "be",
            "is_trades", "is_wr", "is_wlow", "is_profit", "is_dd",
            "oos_trades", "oos_wr", "oos_wlow", "oos_profit", "oos_dd", "veredito"
        ])
        for r in sorted(all_results, key=lambda x: x["r_is"]["profit"], reverse=True):
            w.writerow([
                r["session"], r["family"], r["params"], r["exp_m"], PAYOUT, round(r["BE"], 4),
                r["r_is"]["trades"], round(r["r_is"]["wr"], 4), round(r["w_is"], 4), r["r_is"]["profit"], r["r_is"]["max_dd"],
                r["r_oos"]["trades"], round(r["r_oos"]["wr"], 4), round(r["w_oos"], 4), r["r_oos"]["profit"], r["r_oos"]["max_dd"],
                "PASS" if r["ok_oos"] else "FAIL"
            ])
    print(f"\n[CSV] data/hunter_eurusd_sessions_top.csv gerado")


if __name__ == "__main__":
    main()