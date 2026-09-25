import check_exact as ce
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score, roc_auc_score, average_precision_score
import numpy as np

X_train, y_train = ce.X_train, ce.y_train
tscv = TimeSeriesSplit(n_splits=5)

model = XGBClassifier(
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

metrics = {"precision": [], "recall": [], "f1": [], "accuracy": [], "roc_auc": [], "pr_auc": []}
for fold, (train_idx, val_idx) in enumerate(tscv.split(X_train)):
    X_tr, y_tr = X_train.iloc[train_idx], y_train.iloc[train_idx]
    X_val, y_val = X_train.iloc[val_idx], y_train.iloc[val_idx]
    model.fit(X_tr, y_tr)
    preds = model.predict(X_val)
    probs = model.predict_proba(X_val)[:, 1]
    metrics["precision"].append(precision_score(y_val, preds, zero_division=0))
    metrics["recall"].append(recall_score(y_val, preds, zero_division=0))
    metrics["f1"].append(f1_score(y_val, preds, zero_division=0))
    metrics["accuracy"].append(accuracy_score(y_val, preds))
    metrics["roc_auc"].append(roc_auc_score(y_val, probs))
    metrics["pr_auc"].append(average_precision_score(y_val, probs))

print("=== XGBoost CV Results ===")
print(f"Precision: {np.mean(metrics['precision'])*100:.2f}% +/- {np.std(metrics['precision'])*100:.2f}%")
print(f"Recall:    {np.mean(metrics['recall'])*100:.2f}% +/- {np.std(metrics['recall'])*100:.2f}%")
print(f"F1-Score:  {np.mean(metrics['f1']):.4f} +/- {np.std(metrics['f1']):.4f}")
print(f"Accuracy:  {np.mean(metrics['accuracy'])*100:.2f}% +/- {np.std(metrics['accuracy'])*100:.2f}%")
print(f"ROC-AUC:   {np.mean(metrics['roc_auc']):.4f}")
print(f"PR-AUC:    {np.mean(metrics['pr_auc']):.4f}")
