"""
test_pipeline.py - Validate the complete data processing, feature engineering,
and modeling pipeline before assembling transcendence_ml_analysis.ipynb.
"""
import sys
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    precision_score, recall_score, f1_score, accuracy_score,
    roc_auc_score, average_precision_score, confusion_matrix
)

print("Starting pipeline test...")
df = pd.read_csv("data/EURUSD_M15_histdata.csv")
print(f"Loaded {len(df)} candles.")

# 1. Timestamps
first_time = float(df["time"].iloc[0])
unit = "ms" if first_time > 1e11 else "s"
df["datetime"] = pd.to_datetime(df["time"], unit=unit, utc=True)
df = df.sort_values("datetime").reset_index(drop=True)

# 2. Features
hour = df["datetime"].dt.hour
dow = df["datetime"].dt.dayofweek
minute = df["datetime"].dt.minute
tod_min = hour * 60 + minute

df["sin_hour"] = np.sin(2 * np.pi * hour / 24.0)
df["cos_hour"] = np.cos(2 * np.pi * hour / 24.0)
df["sin_dow"] = np.sin(2 * np.pi * dow / 7.0)
df["cos_dow"] = np.cos(2 * np.pi * dow / 7.0)
df["sin_tod"] = np.sin(2 * np.pi * tod_min / 1440.0)
df["cos_tod"] = np.cos(2 * np.pi * tod_min / 1440.0)

df["session_asian"] = ((hour >= 0) & (hour < 8)).astype(int)
df["session_london"] = ((hour >= 8) & (hour < 16)).astype(int)
df["session_ny"] = ((hour >= 13) & (hour < 21)).astype(int)
df["session_overlap"] = ((hour >= 13) & (hour < 16)).astype(int)
df["is_weekend"] = (dow >= 5).astype(int)

# Multi-period SMA and StdDev
for p in [5, 10, 20, 50]:
    sma = df["close"].rolling(p).mean()
    std = df["close"].rolling(p).std()
    df[f"dist_sma_{p}"] = (df["close"] - sma) / sma
    df[f"slope_sma_{p}"] = (sma - sma.shift(1)) / (sma.shift(1) + 1e-9)
    df[f"vol_ratio_{p}"] = std / (sma + 1e-9)
    df[f"_sma_{p}"] = sma
    df[f"_std_{p}"] = std

df["sma_spread_5_20"] = (df["_sma_5"] - df["_sma_20"]) / df["_sma_20"]
df["sma_spread_10_50"] = (df["_sma_10"] - df["_sma_50"]) / df["_sma_50"]
df["sma_spread_20_50"] = (df["_sma_20"] - df["_sma_50"]) / df["_sma_50"]
df["vol_shock_5_50"] = df["_std_5"] / (df["_std_50"] + 1e-9)

# Bollinger Bands
bb_mid = df["_sma_20"]
bb_std = df["_std_20"]
bb_upper = bb_mid + 2.0 * bb_std
bb_lower = bb_mid - 2.0 * bb_std
bb_range = bb_upper - bb_lower + 1e-9

df["bb_width"] = (bb_upper - bb_lower) / bb_mid
df["bb_pct_b"] = (df["close"] - bb_lower) / bb_range
df["bb_pen_upper"] = np.maximum(0.0, (df["close"] - bb_upper) / bb_upper)
df["bb_pen_lower"] = np.maximum(0.0, (bb_lower - df["close"]) / bb_lower)

# Donchian Channels (shift 1 strictly excludes current bar)
for n in [10, 20, 40, 60]:
    dc_up = df["high"].shift(1).rolling(n).max()
    dc_lo = df["low"].shift(1).rolling(n).min()
    dc_mid = (dc_up + dc_lo) / 2.0
    dc_range = dc_up - dc_lo + 1e-9

    df[f"dc_width_{n}"] = (dc_up - dc_lo) / dc_mid
    df[f"dc_pct_{n}"] = (df["close"] - dc_lo) / dc_range
    if n in [10, 20]:
        df[f"dc_break_upper_{n}"] = np.maximum(0.0, (df["close"] - dc_up) / dc_up)
        df[f"dc_break_lower_{n}"] = np.maximum(0.0, (dc_lo - df["close"]) / dc_lo)
    if n == 20:
        df["_dc_upper_20"] = dc_up
        df["_dc_lower_20"] = dc_lo

# Candlestick morphology
rng = df["high"] - df["low"] + 1e-9
df["body_ratio"] = (df["close"] - df["open"]).abs() / rng
df["upper_wick_ratio"] = (df["high"] - df[["open", "close"]].max(axis=1)) / rng
df["lower_wick_ratio"] = (df[["open", "close"]].min(axis=1) - df["low"]) / rng
df["ret_1"] = df["close"].pct_change(1)
df["ret_3"] = df["close"].pct_change(3)
df["ret_5"] = df["close"].pct_change(5)

# Deterministic Signals
df["sig_df_dir"] = np.where(df["close"] > df["_dc_upper_20"], -1,
                    np.where(df["close"] < df["_dc_lower_20"], 1, 0))
df["sig_bb_dir"] = np.where(df["close"] > bb_upper, -1,
                    np.where(df["close"] < bb_lower, 1, 0))

df["sig_agreement"] = ((df["sig_df_dir"] == df["sig_bb_dir"]) & (df["sig_df_dir"] != 0)).astype(int)
df["sig_confluence_dir"] = np.where((df["sig_df_dir"] == 1) & (df["sig_bb_dir"] == 1), 1,
                           np.where((df["sig_df_dir"] == -1) & (df["sig_bb_dir"] == -1), -1, 0))

# Candidate Trade Signals
cond_call = ((df["sig_df_dir"] == 1) | (df["sig_bb_dir"] == 1)) & (df["sig_df_dir"] != -1) & (df["sig_bb_dir"] != -1)
cond_put = ((df["sig_df_dir"] == -1) | (df["sig_bb_dir"] == -1)) & (df["sig_df_dir"] != 1) & (df["sig_bb_dir"] != 1)
df["candidate_signal"] = np.where(cond_call, "call", np.where(cond_put, "put", "none"))

# Target (Horizon = 4 bars, 1 hour)
df["future_close"] = df["close"].shift(-4)
df["target"] = np.where(
    df["candidate_signal"] == "call",
    (df["future_close"] > df["close"]).astype(float),
    np.where(
        df["candidate_signal"] == "put",
        (df["future_close"] < df["close"]).astype(float),
        np.nan
    )
)

aux_cols = [c for c in df.columns if c.startswith("_")]
df = df.drop(columns=aux_cols)

# Drop warmup and tail
valid_df = df.iloc[60:].copy()
events = valid_df.dropna(subset=["target"]).copy()
events["target"] = events["target"].astype(int)

ignore_cols = {"time", "datetime", "open", "high", "low", "close", "future_close", "candidate_signal", "target"}
feature_cols = [c for c in events.columns if c not in ignore_cols]

print(f"Total candidate signal events: {len(events)}")
print(f"Total features: {len(feature_cols)}")
print(f"Baseline Win Rate (All events): {events['target'].mean():.4f}")

# Train/Test Split
split_idx = int(len(events) * 0.80)
train_df = events.iloc[:split_idx].copy()
test_df = events.iloc[split_idx:].copy()

X_train = train_df[feature_cols]
y_train = train_df["target"]
X_test = test_df[feature_cols]
y_test = test_df["target"]

print(f"Train samples: {len(X_train)}, Test samples: {len(X_test)}")
print(f"Train baseline winrate: {y_train.mean():.4f}, Test baseline winrate: {y_test.mean():.4f}")

# Cross-Validation setup
tscv = TimeSeriesSplit(n_splits=5)

def evaluate_cv(model_name, model_pipeline):
    fold_precisions = []
    fold_recalls = []
    fold_f1s = []
    fold_accs = []
    fold_roc_aucs = []
    fold_pr_aucs = []

    for fold, (tr_idx, val_idx) in enumerate(tscv.split(X_train)):
        X_tr, y_tr = X_train.iloc[tr_idx], y_train.iloc[tr_idx]
        X_val, y_val = X_train.iloc[val_idx], y_train.iloc[val_idx]

        model_pipeline.fit(X_tr, y_tr)
        preds = model_pipeline.predict(X_val)
        probs = model_pipeline.predict_proba(X_val)[:, 1]

        fold_precisions.append(precision_score(y_val, preds, zero_division=0))
        fold_recalls.append(recall_score(y_val, preds, zero_division=0))
        fold_f1s.append(f1_score(y_val, preds, zero_division=0))
        fold_accs.append(accuracy_score(y_val, preds))
        fold_roc_aucs.append(roc_auc_score(y_val, probs))
        fold_pr_aucs.append(average_precision_score(y_val, probs))

    print(f"=== {model_name} (5-Fold TimeSeriesSplit CV) ===")
    print(f"Precision: {np.mean(fold_precisions):.4f} +/- {np.std(fold_precisions):.4f}")
    print(f"Recall:    {np.mean(fold_recalls):.4f} +/- {np.std(fold_recalls):.4f}")
    print(f"F1-Score:  {np.mean(fold_f1s):.4f} +/- {np.std(fold_f1s):.4f}")
    print(f"Accuracy:  {np.mean(fold_accs):.4f} +/- {np.std(fold_accs):.4f}")
    print(f"ROC-AUC:   {np.mean(fold_roc_aucs):.4f}")
    print(f"PR-AUC:    {np.mean(fold_pr_aucs):.4f}")

# Logistic Regression
lr_pipe = Pipeline([
    ("scaler", StandardScaler()),
    ("model", LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=1000, random_state=42))
])
evaluate_cv("Logistic Regression", lr_pipe)

# Random Forest
rf_pipe = Pipeline([
    ("model", RandomForestClassifier(n_estimators=200, max_depth=6, min_samples_leaf=20, max_features="sqrt", random_state=42, n_jobs=-1))
])
evaluate_cv("Random Forest", rf_pipe)

# XGBoost
xgb_pipe = Pipeline([
    ("model", XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=1.0, eval_metric="logloss", random_state=42))
])
evaluate_cv("XGBoost", xgb_pipe)

# Precision-Tuned Threshold Analysis
# Fit on full X_train
xgb_pipe.fit(X_train, y_train)
test_probs = xgb_pipe.predict_proba(X_test)[:, 1]

print("\n=== XGBoost Test Set Performance Across Thresholds ===")
print("Thresh | Trades | Precision (Win Rate) | Recall | F1-Score | EV/Trade (Payout 0.80)")
for th in [0.50, 0.52, 0.54, 0.56, 0.58, 0.60, 0.62]:
    preds_th = (test_probs >= th).astype(int)
    n_trades = preds_th.sum()
    if n_trades > 0:
        prec = precision_score(y_test, preds_th, zero_division=0)
        rec = recall_score(y_test, preds_th, zero_division=0)
        f1 = f1_score(y_test, preds_th, zero_division=0)
        ev = prec * 0.80 - (1.0 - prec) * 1.00
        print(f"{th:.2f}   | {n_trades:6d} | {prec*100:6.2f}%              | {rec*100:5.2f}% | {f1:.4f}   | ${ev:+.4f}")
