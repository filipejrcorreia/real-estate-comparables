import os, openpyxl, subprocess

# Show running streamlit
r = subprocess.run(["pgrep", "-a", "-f", "streamlit"], capture_output=True, text=True)
print("Running:", r.stdout.strip())

# The xlsm is right here in the project directory
BASE = os.path.dirname(os.path.abspath(__file__))
f = os.path.join(BASE, "FINAL COMPARABLE SPREADSHEET 2026.xlsm")
print(f"\nFile exists: {os.path.exists(f)}")
print(f"File size:   {os.path.getsize(f):,} bytes\n")

print("--- Normal mode (read_only=False) ---")
wb = openpyxl.load_workbook(f, data_only=True, keep_vba=False)
ws = wb.active
print("ws.dimensions:", ws.dimensions)
print("ws.max_row:   ", ws.max_row)
rows = list(ws.iter_rows(values_only=True))
nonempty = [r for r in rows if any(v is not None for v in r)]
print("total rows from iter_rows:", len(rows))
print("non-empty rows:", len(nonempty))

print("\n--- read_only=True ---")
wb2 = openpyxl.load_workbook(f, read_only=True, data_only=True, keep_vba=False)
ws2 = wb2.active
print("ws2.dimensions:", ws2.dimensions)
rows2 = list(ws2.iter_rows(values_only=True))
nonempty2 = [r for r in rows2 if any(v is not None for v in r)]
print("total rows from iter_rows:", len(rows2))
print("non-empty rows:", len(nonempty2))

print("\n--- All sheet names (normal mode) ---")
wb3 = openpyxl.load_workbook(f, data_only=True, keep_vba=False)
print(wb3.sheetnames)
for name in wb3.sheetnames:
    ws3 = wb3[name]
    r3 = [r for r in ws3.iter_rows(values_only=True) if any(v is not None for v in r)]
    print(f"  Sheet '{name}': {len(r3)} non-empty rows")
