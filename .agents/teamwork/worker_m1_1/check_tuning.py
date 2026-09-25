import json

with open("transcendence_ml_analysis.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

# Cell 22 is index 21
cell22 = nb["cells"][21]
for out in cell22.get("outputs", []):
    data = out.get("data", {})
    if "text/html" in data:
        print("HTML table in Cell 22 output:")
        print(data["text/html"][:3000])
