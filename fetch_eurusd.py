"""Fetch EURUSD M15 via yfinance (max 60d) para grade IS/OOS."""
import yfinance as yf, csv, os
from datetime import datetime, timezone
df=yf.download("EURUSD=X", period="60d", interval="15m", progress=False, auto_adjust=False)
if df.empty: raise SystemExit("yfinance vazio")
df=df.dropna()
# yfinance multi-index cols
if isinstance(df.columns, type(yf.download("EURUSD=X", period="1d", interval="1d", progress=False).columns)):
    df.columns=df.columns.get_level_values(0)
df=df.reset_index()
out="data/EURUSD_M15_yf.csv"
os.makedirs("data",exist_ok=True)
with open(out,"w",newline="",encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["time","open","high","low","close"])
    for _,r in df.iterrows():
        ts=int(r["Datetime"].timestamp()*1000)
        w.writerow([ts, r["Open"], r["High"], r["Low"], r["Close"]])
print(f"[OK] {len(df)} candles EURUSD M15 60d -> {out}")
