import check_exact as ce
from xgboost import XGBClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score

X_train, y_train = ce.X_train, ce.y_train
X_test, y_test = ce.X_test, ce.y_test

xgb = XGBClassifier(
    n_estimators=250, 
    max_depth=2, 
    learning_rate=0.05, 
    subsample=0.8, 
    colsample_bytree=0.8, 
    reg_alpha=5.0, 
    reg_lambda=2.0, 
    eval_metric="logloss", 
    random_state=42
)
xgb.fit(X_train, y_train)
probs = xgb.predict_proba(X_test)[:, 1]

print("=== XGBoost (max_depth=2, lr=0.05, reg_alpha=5.0) ===")
for th in [0.50, 0.52, 0.54, 0.56, 0.58, 0.60, 0.62]:
    preds = (probs >= th).astype(int)
    n = preds.sum()
    if n > 0:
        prec = precision_score(y_test, preds, zero_division=0)
        rec = recall_score(y_test, preds, zero_division=0)
        f1 = f1_score(y_test, preds, zero_division=0)
        acc = accuracy_score(y_test, preds)
        ev_80 = prec * 0.80 - (1 - prec) * 1.0
        ev_87 = prec * 0.87 - (1 - prec) * 1.0
        print(f"th={th:.2f} | trades={n:4d} | prec={prec*100:5.2f}% | rec={rec*100:5.2f}% | f1={f1:.4f} | acc={acc*100:5.2f}% | EV80=${ev_80:+.4f} | EV87=${ev_87:+.4f}")
