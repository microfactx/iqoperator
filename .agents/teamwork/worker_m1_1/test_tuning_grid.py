import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV
import check_exact as ce

X_train, y_train = ce.X_train, ce.y_train
X_test, y_test = ce.X_test, ce.y_test

print(f"X_train: {X_train.shape}, y_train mean: {y_train.mean():.4f}")
print(f"X_test: {X_test.shape}, y_test mean: {y_test.mean():.4f}")

# Let's test Random Forest thresholding:
rf = RandomForestClassifier(n_estimators=300, max_depth=5, min_samples_leaf=25, max_features="sqrt", random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)
rf_probs = rf.predict_proba(X_test)[:, 1]

print("\n--- Random Forest Test Threshold Sweep ---")
for th in [0.50, 0.52, 0.54, 0.55, 0.56, 0.57, 0.58, 0.59, 0.60]:
    preds = (rf_probs >= th).astype(int)
    n = preds.sum()
    if n > 0:
        prec = (y_test[preds == 1] == 1).mean()
        rec = (y_test[preds == 1] == 1).sum() / (y_test == 1).sum()
        ev = prec * 0.80 - (1 - prec) * 1.0
        print(f"th={th:.2f} | trades={n:4d} | prec={prec*100:5.2f}% | rec={rec*100:5.2f}% | EV_80=${ev:+.4f}")

# Let's test Logistic Regression thresholding:
scaler = StandardScaler()
X_tr_s = scaler.fit_transform(X_train)
X_te_s = scaler.transform(X_test)
lr = LogisticRegression(C=0.01, solver="lbfgs", max_iter=1000, random_state=42)
lr.fit(X_tr_s, y_train)
lr_probs = lr.predict_proba(X_te_s)[:, 1]

print("\n--- Logistic Regression (Regularized C=0.01) Test Threshold Sweep ---")
for th in [0.50, 0.52, 0.53, 0.54, 0.55, 0.56]:
    preds = (lr_probs >= th).astype(int)
    n = preds.sum()
    if n > 0:
        prec = (y_test[preds == 1] == 1).mean()
        rec = (y_test[preds == 1] == 1).sum() / (y_test == 1).sum()
        ev = prec * 0.80 - (1 - prec) * 1.0
        print(f"th={th:.2f} | trades={n:4d} | prec={prec*100:5.2f}% | rec={rec*100:5.2f}% | EV_80=${ev:+.4f}")

# Let's test XGBoost with various depths / learning rates:
print("\n--- XGBoost Grid Search for Precision ---")
for md in [2, 3, 4]:
    for lr_val in [0.01, 0.03, 0.05]:
        for reg_a in [0.1, 1.0, 5.0]:
            xgb = XGBClassifier(n_estimators=200, max_depth=md, learning_rate=lr_val, subsample=0.8, colsample_bytree=0.8, reg_alpha=reg_a, reg_lambda=2.0, eval_metric="logloss", random_state=42)
            xgb.fit(X_train, y_train)
            probs = xgb.predict_proba(X_test)[:, 1]
            for th in [0.55, 0.58, 0.60, 0.62]:
                preds = (probs >= th).astype(int)
                n = preds.sum()
                if 20 <= n <= 300:
                    prec = (y_test[preds == 1] == 1).mean()
                    if prec >= 0.58:
                        print(f"md={md}, lr={lr_val}, a={reg_a}, th={th:.2f} -> trades={n}, prec={prec*100:.2f}%")
