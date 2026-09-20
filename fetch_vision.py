"""Baixa ZIPs mensais do data.binance.vision e converte p/ nosso CSV (time,open,high,low,close). Só stdlib."""
import argparse
import csv
import io
import os
import urllib.request
import zipfile

BASE = "https://data.binance.vision/data/spot/monthly/klines"


def months_13():
    ms = []
    y, m = 2024, 9
    for _ in range(12):
        ms.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return ms


def fetch_month(symbol, interval, month):
    url = f"{BASE}/{symbol}/{interval}/{symbol}-{interval}-{month}.zip"
    req = urllib.request.Request(url, headers={"User-Agent": "iqrobot/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    zf = zipfile.ZipFile(io.BytesIO(data))
    name = zf.namelist()[0]
    with zf.open(name) as f:
        text = io.TextIOWrapper(f, encoding="utf-8")
        return list(csv.reader(text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--interval", default="15m")
    ap.add_argument("--out", default="data/BTCUSDT_M15_2024y.csv")
    a = ap.parse_args()

    rows = []
    for month in months_13():
        try:
            raw = fetch_month(a.symbol, a.interval, month)
        except Exception as e:
            print(f"[AVISO] {month}: {e}")
            continue
        for r in raw:
            # open_time,open,high,low,close,...
            rows.append([r[0], r[1], r[2], r[3], r[4]])
        print(f"[OK] {month}: {len(raw)} candles")
    rows.sort(key=lambda r: int(r[0]))
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close"])
        w.writerows(rows)
    print(f"[OK] total {len(rows)} candles -> {a.out}")


if __name__ == "__main__":
    main()
