import test_pipeline as tp
import json

with open("transcendence_ml_analysis.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

# Let's inspect feature columns in notebook
print("Columns in test_pipeline:", len(tp.feature_cols))
