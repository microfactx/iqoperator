import json
import numpy as np
import pandas as pd

# Load test_df from executed notebook
# Or let's see what is inside check_higher_thresholds vs check_tuning:
with open("transcendence_ml_analysis.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

# Cell 22 code:
print("Cell 22 code snippet:")
print("".join(nb["cells"][21]["source"][:30]))
