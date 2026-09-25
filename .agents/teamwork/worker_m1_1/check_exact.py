import pandas as pd
import numpy as np
from xgboost import XGBClassifier

df = pd.read_csv("data/EURUSD_M15_histdata.csv")
first_time = float(df["time"].iloc[0])
unit = "ms" if first_time > 1e11 else "s"
df["datetime"] = pd.to_datetime(df["time"], unit=unit, utc=True)
df = df.sort_values("datetime").reset_index(drop=True)

# Let's run exact code from build_notebook.py Cell 6 and Cell 8:
import build_notebook as bn

from sklearn.preprocessing import StandardScaler
g = {"df_raw": df, "pd": pd, "np": np, "total_candles": len(df), "StandardScaler": StandardScaler}
# Let's run cell6_code without plots:
# extract code before plt
c6 = bn.cell6_code.split("# Plot Signal")[0]
exec(c6, g)

c8 = bn.cell8_code.split("assert len(feature_cols)")[0]
exec(c8, g)

c13 = bn.cell13_code.split("print(f\"Scaled Train Mean")[0]
exec(c13, g)

X_train = g["X_train"]
y_train = g["y_train"]
X_test = g["X_test"]
y_test = g["y_test"]

print(f"X_train shape: {X_train.shape}, X_test shape: {X_test.shape}")

xgb = XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.03, subsample=0.7, colsample_bytree=0.7, reg_alpha=1.0, reg_lambda=2.0, eval_metric="logloss", random_state=42)
xgb.fit(X_train, y_train)

probs = xgb.predict_proba(X_test)[:, 1]

for th in [0.50, 0.52, 0.54, 0.56, 0.58, 0.60, 0.61, 0.62, 0.63, 0.64, 0.65]:
    preds = (probs >= th).astype(int)
    n = preds.sum()
    if n > 0:
        prec = (y_test[preds == 1] == 1).mean()
        rec = (y_test[preds == 1] == 1).sum() / (y_test == 1).sum()
        print(f"th={th:.2f} | trades={n:4d} | prec={prec*100:5.2f}% | rec={rec*100:5.2f}%")
