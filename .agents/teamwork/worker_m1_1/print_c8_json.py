import json

with open("transcendence_ml_analysis.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

print(json.dumps(nb["cells"][7]["outputs"], indent=2))
