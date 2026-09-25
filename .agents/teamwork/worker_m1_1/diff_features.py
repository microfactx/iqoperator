import test_pipeline as tp
import pandas as pd

# Let's check features in test_pipeline
print("Features in test_pipeline:")
print(sorted(tp.feature_cols))

# Let's inspect build_notebook.py features
import build_notebook
# run cell8_code inside a dict
g = {"df_sig": tp.df, "np": tp.np, "pd": pd, "WARMUP_BARS": 60}
exec(build_notebook.cell8_code, g)
print("Features in build_notebook:")
print(sorted(g["feature_cols"]))

diff = set(tp.feature_cols) ^ set(g["feature_cols"])
print("Difference:", diff)
