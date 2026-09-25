import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# Load the test_pipeline data
import test_pipeline as tp

X_train, y_train = tp.X_train, tp.y_train
X_test, y_test = tp.X_test, tp.y_test

scaler = StandardScaler()
X_tr_s = scaler.fit_transform(X_train)
X_te_s = scaler.transform(X_test)

xgb = XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.03, subsample=0.7, colsample_bytree=0.7, reg_alpha=1.0, reg_lambda=2.0, eval_metric="logloss", random_state=42)
xgb.fit(X_train, y_train)

# Feature importances
importances = pd.Series(xgb.feature_importances_, index=tp.feature_cols).sort_values(ascending=False)
print("Top 15 XGBoost Features:")
print(importances.head(15))

probs = xgb.predict_proba(X_test)[:, 1]
print("\nTuned XGBoost Test Set Performance Across Thresholds:")
for th in [0.50, 0.52, 0.54, 0.55, 0.56, 0.57, 0.58, 0.59, 0.60, 0.62]:
    preds = (probs >= th).astype(int)
    n = preds.sum()
    if n > 0:
        prec = (y_test[preds == 1] == 1).mean()
        rec = (y_test[preds == 1] == 1).sum() / (y_test == 1).sum()
        print(f"th={th:.2f} | trades={n:4d} | prec={prec*100:5.2f}% | recall={rec*100:5.2f}%")
