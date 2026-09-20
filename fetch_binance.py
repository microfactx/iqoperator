"""Baixa candles M15 reais de BTCUSDT via API pública Binance (sem chave). Só stdlib."""
import argparse
import csv
import json
import os
import urllib.request

BASE = "https://data-api.binance.vision"


def get_klines(symbol="BTCUSDT", interval="15m", limit=1000, end_time=None):
    url = f"{BASE}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    if end_time:
        url += f"&endTime={end_time}"
    req = urllib.request.Request(url, headers={"User-Agent": "iqrobot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--out", default="data/BTCUSDT_M15_real.csv")
    a = ap.parse_args()

    pages, end_time = [], None
    while sum(len(p) for p in pages) < a.n:
        kl = get_klines(limit=min(1000, a.n - sum(len(p) for p in pages)), end_time=end_time)
        if not kl:
            break
        pages.append(kl)
        end_time = kl[0][0] - 1
        if len(kl) < 1000:
            break

    klines = [k for p in reversed(pages) for k in p][-a.n:]
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close"])
        for k in klines:
            w.writerow([k[0], k[1], k[2], k[3], k[4]])
    import datetime
    t0 = datetime.datetime.fromtimestamp(klines[0][0] / 1000).strftime("%Y-%m-%d")
    t1 = datetime.datetime.fromtimestamp(klines[-1][0] / 1000).strftime("%Y-%m-%d")
    print(f"[OK] {len(klines)} candles M15 {t0} -> {t1} em {a.out}")


if __name__ == "__main__":
    main()
