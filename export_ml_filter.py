#!/usr/bin/env python3
"""
export_ml_filter.py

Extração de Pesos e Serialização do Modelo XGBoost (tau=0.62).
Reproduz com fidelidade numérica estrita os resultados do notebook
transcendence_ml_analysis.ipynb sobre data/EURUSD_M15_histdata.csv:
  - 53 features técnicas e cíclicas (zero lookahead)
  - Split temporal 80/20
  - Regularized XGBClassifier + StandardScaler
  - Calibração de threshold tau = 0.62 -> Precision = 65.96% (47 trades)
  - Serialização em models/xgb_filter.pkl e models/xgb_filter.json
"""
import os
import sys
import json
import pickle
import warnings
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
    roc_auc_score, average_precision_score
)

def train_and_export():
    warnings.filterwarnings('ignore')
    np.random.seed(42)

    data_path = os.path.join(os.path.dirname(__file__), 'data', 'EURUSD_M15_histdata.csv')
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Arquivo de dados não encontrado: {data_path}")

    print(f"[ML EXPORT] Carregando candles de: {data_path}")
    df_raw = pd.read_csv(data_path)
    first_ts = float(df_raw["time"].iloc[0])
    unit = "ms" if first_ts > 1e11 else "s"
    df_raw["datetime"] = pd.to_datetime(df_raw["time"], unit=unit, utc=True)
    df_raw = df_raw.sort_values("datetime").reset_index(drop=True)

    # 1. Sinais Determinísticos e Target
    df_sig = df_raw.copy()
    N_DC = 20
    df_sig["dc_up_20"] = df_sig["high"].shift(1).rolling(N_DC).max()
    df_sig["dc_lo_20"] = df_sig["low"].shift(1).rolling(N_DC).min()

    df_sig["sig_df_dir"] = np.where(df_sig["close"] > df_sig["dc_up_20"], -1,
                            np.where(df_sig["close"] < df_sig["dc_lo_20"], 1, 0))

    P_BB = 20
    MULT_BB = 2.0
    bb_sma = df_sig["close"].rolling(P_BB).mean()
    bb_std = df_sig["close"].rolling(P_BB).std()
    df_sig["bb_upper"] = bb_sma + MULT_BB * bb_std
    df_sig["bb_lower"] = bb_sma - MULT_BB * bb_std

    df_sig["sig_bb_dir"] = np.where(df_sig["close"] > df_sig["bb_upper"], -1,
                            np.where(df_sig["close"] < df_sig["bb_lower"], 1, 0))

    df_sig["sig_agreement"] = ((df_sig["sig_df_dir"] == df_sig["sig_bb_dir"]) & (df_sig["sig_df_dir"] != 0)).astype(int)
    df_sig["sig_confluence_dir"] = np.where((df_sig["sig_df_dir"] == 1) & (df_sig["bb_upper"] == 1), 1,  # fallback safety
                                   np.where((df_sig["sig_df_dir"] == 1) & (df_sig["sig_bb_dir"] == 1), 1,
                                   np.where((df_sig["sig_df_dir"] == -1) & (df_sig["sig_bb_dir"] == -1), -1, 0)))
    # Match exact notebook cell 5:
    df_sig["sig_confluence_dir"] = np.where((df_sig["sig_df_dir"] == 1) & (df_sig["sig_bb_dir"] == 1), 1,
                                   np.where((df_sig["sig_df_dir"] == -1) & (df_sig["sig_bb_dir"] == -1), -1, 0))

    cond_call = ((df_sig["sig_df_dir"] == 1) | (df_sig["sig_bb_dir"] == 1)) & (df_sig["sig_df_dir"] != -1) & (df_sig["sig_bb_dir"] != -1)
    cond_put = ((df_sig["sig_df_dir"] == -1) | (df_sig["sig_bb_dir"] == -1)) & (df_sig["sig_df_dir"] != 1) & (df_sig["sig_bb_dir"] != 1)
    df_sig["candidate_signal"] = np.where(cond_call, "call", np.where(cond_put, "put", "none"))

    HORIZON = 4
    df_sig["future_close"] = df_sig["close"].shift(-HORIZON)
    df_sig["target"] = np.where(
        df_sig["candidate_signal"] == "call",
        (df_sig["future_close"] > df_sig["close"]).astype(float),
        np.where(
            df_sig["candidate_signal"] == "put",
            (df_sig["future_close"] < df_sig["close"]).astype(float),
            np.nan
        )
    )

    # 2. Engenharia de Features
    df_feat = df_sig.copy()
    hour = df_feat["datetime"].dt.hour
    dow = df_feat["datetime"].dt.dayofweek
    minute = df_feat["datetime"].dt.minute
    tod_min = hour * 60 + minute

    df_feat["sin_hour"] = np.sin(2 * np.pi * hour / 24.0)
    df_feat["cos_hour"] = np.cos(2 * np.pi * hour / 24.0)
    df_feat["sin_dow"] = np.sin(2 * np.pi * dow / 7.0)
    df_feat["cos_dow"] = np.cos(2 * np.pi * dow / 7.0)
    df_feat["sin_tod"] = np.sin(2 * np.pi * tod_min / 1440.0)
    df_feat["cos_tod"] = np.cos(2 * np.pi * tod_min / 1440.0)

    df_feat["session_asian"] = ((hour >= 0) & (hour < 8)).astype(int)
    df_feat["session_london"] = ((hour >= 8) & (hour < 16)).astype(int)
    df_feat["session_ny"] = ((hour >= 13) & (hour < 21)).astype(int)
    df_feat["session_overlap"] = ((hour >= 13) & (hour < 16)).astype(int)
    df_feat["is_weekend"] = (dow >= 5).astype(int)

    for p in [5, 10, 20, 50]:
        sma = df_feat["close"].rolling(p).mean()
        std = df_feat["close"].rolling(p).std()
        df_feat[f"dist_sma_{p}"] = (df_feat["close"] - sma) / sma
        df_feat[f"slope_sma_{p}"] = (sma - sma.shift(1)) / (sma.shift(1) + 1e-9)
        df_feat[f"vol_ratio_{p}"] = std / (sma + 1e-9)
        df_feat[f"_sma_{p}"] = sma
        df_feat[f"_std_{p}"] = std

    df_feat["sma_spread_5_20"] = (df_feat["_sma_5"] - df_feat["_sma_20"]) / df_feat["_sma_20"]
    df_feat["sma_spread_10_50"] = (df_feat["_sma_10"] - df_feat["_sma_50"]) / df_feat["_sma_50"]
    df_feat["sma_spread_20_50"] = (df_feat["_sma_20"] - df_feat["_sma_50"]) / df_feat["_sma_50"]

    df_feat["vol_shock_5_50"] = df_feat["_std_5"] / (df_feat["_std_50"] + 1e-9)
    bb_range = df_feat["bb_upper"] - df_feat["bb_lower"] + 1e-9
    df_feat["bb_width"] = bb_range / df_feat["_sma_20"]
    df_feat["bb_pct_b"] = (df_feat["close"] - df_feat["bb_lower"]) / bb_range
    df_feat["bb_pen_upper"] = np.maximum(0.0, (df_feat["close"] - df_feat["bb_upper"]) / df_feat["bb_upper"])
    df_feat["bb_pen_lower"] = np.maximum(0.0, (df_feat["bb_lower"] - df_feat["close"]) / df_feat["bb_lower"])

    for n in [10, 20, 40, 60]:
        dc_up = df_feat["high"].shift(1).rolling(n).max()
        dc_lo = df_feat["low"].shift(1).rolling(n).min()
        dc_mid = (dc_up + dc_lo) / 2.0
        dc_rng = dc_up - dc_lo + 1e-9

        df_feat[f"dc_width_{n}"] = (dc_up - dc_lo) / dc_mid
        df_feat[f"dc_pct_{n}"] = (df_feat["close"] - dc_lo) / dc_rng
        if n in [10, 20]:
            df_feat[f"dc_break_upper_{n}"] = np.maximum(0.0, (df_feat["close"] - dc_up) / dc_up)
            df_feat[f"dc_break_lower_{n}"] = np.maximum(0.0, (dc_lo - df_feat["close"]) / dc_lo)

    bar_rng = df_feat["high"] - df_feat["low"] + 1e-9
    df_feat["body_ratio"] = (df_feat["close"] - df_feat["open"]).abs() / bar_rng
    df_feat["upper_wick_ratio"] = (df_feat["high"] - df_feat[["open", "close"]].max(axis=1)) / bar_rng
    df_feat["lower_wick_ratio"] = (df_feat[["open", "close"]].min(axis=1) - df_feat["low"]) / bar_rng
    df_feat["ret_1"] = df_feat["close"].pct_change(1)
    df_feat["ret_3"] = df_feat["close"].pct_change(3)
    df_feat["ret_5"] = df_feat["close"].pct_change(5)

    aux_cols = [c for c in df_feat.columns if c.startswith("_") or c in ["dc_up_20", "dc_lo_20", "bb_upper", "bb_lower"]]
    df_feat = df_feat.drop(columns=aux_cols)

    WARMUP_BARS = 60
    df_valid = df_feat.iloc[WARMUP_BARS:].copy()
    events_df = df_valid.dropna(subset=["target"]).copy()
    events_df["target"] = events_df["target"].astype(int)

    ignore_cols = {"time", "datetime", "open", "high", "low", "close", "future_close", "candidate_signal", "target"}
    feature_cols = [c for c in events_df.columns if c not in ignore_cols]
    assert len(feature_cols) == 53, f"Esperado 53 features, obtido {len(feature_cols)}"

    SPLIT_RATIO = 0.80
    split_idx = int(len(events_df) * SPLIT_RATIO)
    train_df = events_df.iloc[:split_idx].copy()
    test_df = events_df.iloc[split_idx:].copy()

    X_train = train_df[feature_cols]
    y_train = train_df["target"]
    X_test = test_df[feature_cols]
    y_test = test_df["target"]

    print(f"[ML EXPORT] Treino: {len(X_train)} amostras | Teste: {len(X_test)} amostras")

    # Fit standalone scaler on X_train (para serialização conforme R1)
    standalone_scaler = StandardScaler()
    standalone_scaler.fit(X_train)

    # Executa CV sequencial conforme notebook para avançar geradores de pseudo-aleatoriedade
    tscv = TimeSeriesSplit(n_splits=5)
    def run_cv(pipeline):
        for tr_idx, val_idx in tscv.split(X_train):
            pipeline.fit(X_train.iloc[tr_idx], y_train.iloc[tr_idx])
            _ = pipeline.predict(X_train.iloc[val_idx])

    lr_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000, random_state=42))
    ])
    run_cv(lr_pipeline)

    rf_pipeline = Pipeline([
        ("model", RandomForestClassifier(
            n_estimators=200, max_depth=6, min_samples_leaf=20,
            max_features="sqrt", random_state=42, n_jobs=-1
        ))
    ])
    run_cv(rf_pipeline)
    rf_pipeline.fit(X_train, y_train)

    xgb_pipeline = Pipeline([
        ("model", XGBClassifier(
            n_estimators=200, max_depth=2, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=2.0,
            eval_metric="logloss", random_state=42
        ))
    ])
    run_cv(xgb_pipeline)
    xgb_pipeline.fit(X_train, y_train)

    # Fit final do modelo XGBoost
    print("[ML EXPORT] Treinando modelo XGBoost com hiperparâmetros calibrados...")
    xgb_model_full = XGBClassifier(
        n_estimators=200,
        max_depth=2,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=2.0,
        eval_metric="logloss",
        random_state=42
    )
    xgb_model_full.fit(X_train, y_train)

    # Avaliação no Holdout Test Set
    test_probs = xgb_model_full.predict_proba(X_test)[:, 1]
    preds_62 = (test_probs >= 0.62).astype(int)
    n_trades_62 = int(preds_62.sum())
    prec_62 = float(precision_score(y_test, preds_62, zero_division=0) * 100)
    rec_62 = float(recall_score(y_test, preds_62, zero_division=0) * 100)
    f1_62 = float(f1_score(y_test, preds_62, zero_division=0))

    print(f"[ML EXPORT] Validação Holdout Test Set (tau=0.62):")
    print(f"  - Trades Executados:  {n_trades_62} ({n_trades_62/len(X_test)*100:.2f}%)")
    print(f"  - Precision (Winrate): {prec_62:.2f}%")
    print(f"  - Recall:              {rec_62:.2f}%")
    print(f"  - F1-Score:            {f1_62:.4f}")

    assert n_trades_62 == 47, f"Falha na validação de trades: esperado 47, obtido {n_trades_62}"
    assert abs(prec_62 - 65.96) < 0.05, f"Falha na validação de precisão: esperado 65.96%, obtido {prec_62:.2f}%"
    print("[ML EXPORT] Verificação de integridade formal PASSED (Trades=47, Precision=65.96%).")

    # Serialização
    models_dir = os.path.join(os.path.dirname(__file__), 'models')
    os.makedirs(models_dir, exist_ok=True)

    pkl_path = os.path.join(models_dir, 'xgb_filter.pkl')
    json_model_path = os.path.join(models_dir, 'xgb_filter.json')
    meta_path = os.path.join(models_dir, 'metadata.json')

    artifact = {
        'model': xgb_model_full,
        'scaler': standalone_scaler,
        'feature_cols': feature_cols,
        'threshold': 0.62,
        'meta': {
            'model_type': 'XGBClassifier',
            'n_features': len(feature_cols),
            'threshold': 0.62,
            'holdout_trades': n_trades_62,
            'holdout_precision': round(prec_62, 2),
            'holdout_recall': round(rec_62, 2),
            'holdout_f1': round(f1_62, 4),
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'scaler': {
                'mean': standalone_scaler.mean_.tolist(),
                'scale': standalone_scaler.scale_.tolist(),
                'var': standalone_scaler.var_.tolist(),
            },
        }
    }

    with open(pkl_path, 'wb') as f:
        pickle.dump(artifact, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"[ML EXPORT] Artefato serializado em: {pkl_path}")

    # Salva modelo nativo em json
    xgb_model_full.save_model(json_model_path)
    print(f"[ML EXPORT] Modelo nativo salvo em: {json_model_path}")

    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(artifact['meta'], f, indent=2)
    print(f"[ML EXPORT] Metadados salvos em: {meta_path}")

    return pkl_path, artifact['meta']

if __name__ == '__main__':
    train_and_export()
