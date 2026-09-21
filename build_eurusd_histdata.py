"""Build EURUSD M15 from histdata 1m zips (sem IQOption) — agrega 2024+2025."""
import csv, os, zipfile, glob
from datetime import datetime, timezone
from collections import defaultdict

zips = ["DAT_ASCII_EURUSD_M1_2024.zip", "DAT_ASCII_EURUSD_M1_2025.zip"]
rows=[]
for z in zips:
    if not os.path.exists(z):
        print(f"missing {z}"); continue
    with zipfile.ZipFile(z) as zf:
        name = [n for n in zf.namelist() if n.lower().endswith(".csv")][0]
        with zf.open(name) as f:
            for line in f:
                s=line.decode("utf-8").strip()
                if not s: continue
                # 20120201 000000;1.3066;1.3066;1.30656;1.30656;0
                parts=s.split(";")
                if len(parts)<5: continue
                dt_str, o,h,l,c = parts[0], parts[1], parts[2], parts[3], parts[4]
                # EST -> approx UTC+5, but keep as is for backtest (relative)
                dt=datetime.strptime(dt_str, "%Y%m%d %H%M%S")
                # treat as UTC for simplicity
                ts=int(dt.replace(tzinfo=timezone.utc).timestamp()*1000)
                rows.append((ts, float(o), float(h), float(l), float(c)))

rows.sort(key=lambda x: x[0])
print(f"1m rows total {len(rows)}")

# aggregate to 15m: bucket = floor(ts / 900000)*900000
buckets=defaultdict(list)
for ts,o,h,l,c in rows:
    b = ts // 900000 * 900000
    buckets[b].append((o,h,l,c))

out=[]
for b in sorted(buckets):
    vals=buckets[b]
    o=vals[0][0]; c=vals[-1][3]; h=max(v[1] for v in vals); l=min(v[2] for v in vals)
    out.append([b, o,h,l,c])

# keep last 12 months ~35000 M15
out=out[-40000:]
os.makedirs("data", exist_ok=True)
with open("data/EURUSD_M15_histdata.csv","w",newline="",encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["time","open","high","low","close"])
    w.writerows(out)
print(f"[OK] M15 rows {len(out)} -> data/EURUSD_M15_histdata.csv  {datetime.fromtimestamp(out[0][0]/1000)} -> {datetime.fromtimestamp(out[-1][0]/1000)}")
