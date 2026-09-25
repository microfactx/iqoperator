import json

with open("transcendence_ml_analysis.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

# Cell 24 is index 23
cell24 = nb["cells"][23]
for out in cell24.get("outputs", []):
    data = out.get("data", {})
    if "text/html" in data:
        print("HTML table found in Cell 24 output:")
        print(data["text/html"][:2000])
