import json

with open("transcendence_ml_analysis.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

for i, cell in enumerate(nb["cells"]):
    if cell["cell_type"] == "code":
        print(f"\n==========================================")
        print(f"CELL {i+1} OUTPUTS (count={cell.get('execution_count')}):")
        print(f"==========================================")
        for out in cell.get("outputs", []):
            if out.get("output_type") == "stream":
                print("".join(out.get("text", [])))
            elif out.get("output_type") == "execute_result":
                data = out.get("data", {})
                if "text/plain" in data:
                    print("".join(data["text/plain"]))
            elif out.get("output_type") == "display_data":
                data = out.get("data", {})
                if "text/plain" in data:
                    print("".join(data["text/plain"]))
                if "image/png" in data:
                    print(f"[PNG Image Generated: {len(data['image/png'])} base64 bytes]")
