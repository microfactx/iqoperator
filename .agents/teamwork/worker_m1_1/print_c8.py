import json

with open("transcendence_ml_analysis.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

# Cell 8 output text:
print(nb["cells"][7]["outputs"][0]["text"])
