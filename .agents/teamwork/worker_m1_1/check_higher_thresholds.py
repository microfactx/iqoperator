import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score

# Load from inspect_features
import test_pipeline as tp
from xgboost import XGBClassifier

X_train, y_train = tp.X_train, tp.y_train
X_test, y_test = tp.X_test, tp.y_test

xgb_model_full = XGBClassifier(
    n_estimators=300, 
    max_depth=3, 
    learning_rate=0.03, 
    subsample=0.7, 
    colsample_bytree=0.7, 
    reg_alpha=1.0, 
    reg_lambda=2.0, 
    eval_metric="logloss", 
    random_state=42
)
xgb_model_full.fit(X_train, y_train)
test_probs = xgb_model_full.predict_proba(X_test)[:, 1]

for th in [0.60, 0.61, 0.62, 0.63, 0.64, 0.65, 0.66]:
    preds = (test_probs >= th).astype(int)
    n = preds.sum()
    if n > 0:
        prec = (y_test[preds == 1] == 1).mean()
        rec = (y_test[preds == 1] == 1).sum() / (y_test == 1).sum()
        f1 = f1_score(y_test, preds, zero_division=0)
        ev_80 = prec * 0.80 - (1 - prec) * 1.0
        ev_87 = prec * 0.87 - (1 - prec) * 1.0
        print(f"th={th:.2f} | trades={n:4d} | prec={prec*100:5.2f}% | recall={rec*100:5.2f}% | f1={f1:.4f} | EV_80=${ev_80:+.4f} | EV_87=${ev_87:+.4f}")
