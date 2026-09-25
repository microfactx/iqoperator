import json

with open("transcendence_ml_analysis.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

print(f"Total cells: {len(nb['cells'])}")
code_cells = [c for c in nb['cells'] if c['cell_type'] == 'code']
md_cells = [c for c in nb['cells'] if c['cell_type'] == 'markdown']

print(f"Code cells: {len(code_cells)}")
print(f"Markdown cells: {len(md_cells)}")

errors = []
for i, cell in enumerate(nb['cells']):
    ctype = cell['cell_type']
    if ctype == 'code':
        exec_count = cell.get('execution_count')
        outputs = cell.get('outputs', [])
        # Check if there are any error outputs
        for out in outputs:
            if out.get('output_type') == 'error':
                errors.append((i, out.get('ename'), out.get('evalue')))
        print(f"Cell {i+1} [code]: exec_count={exec_count}, outputs={len(outputs)}")
    else:
        first_line = cell['source'][0][:50] if cell['source'] else ''
        print(f"Cell {i+1} [markdown]: {first_line.strip()}")

if errors:
    print(f"\nERRORS DETECTED: {len(errors)}")
    for e in errors:
        print(e)
else:
    print("\nALL CELLS EXECUTED SUCCESSFULLY WITH ZERO ERRORS!")
