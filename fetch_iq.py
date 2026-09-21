"""Fetch M15 via IQOption API (usa credenciais do .env/Railway) — fiel ao feed do bot."""
import argparse, csv, os, time
from dotenv import load_dotenv
load_dotenv()
from iqoptionapi.stable_api import IQ_Option

ap=argparse.ArgumentParser()
ap.add_argument("--asset", default="EURUSD")
ap.add_argument("--interval", type=int, default=900)
ap.add_argument("--n", type=int, default=35000)
ap.add_argument("--out", default="data/EURUSD_M15_iq.csv")
a=ap.parse_args()
email=os.getenv("IQ_EMAIL"); pwd=os.getenv("IQ_PASSWORD")
if not email or not pwd: raise SystemExit("IQ_EMAIL/PASSWORD no .env")
api=IQ_Option(email,pwd)
ok,reason=api.connect()
if not ok: raise SystemExit(f"connect fail: {reason}")
api.change_balance("PRACTICE")
candles=api.get_candles(a.asset, a.interval, a.n, time.time())
if not candles: raise SystemExit("sem candles")
os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
with open(a.out,"w",newline="",encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["time","open","high","low","close"])
    for c in candles:
        w.writerow([c.get("from",""), c.get("open",""), c.get("max",""), c.get("min",""), c.get("close","")])
print(f"[OK] {len(candles)} candles {a.asset} M15 -> {a.out}")
