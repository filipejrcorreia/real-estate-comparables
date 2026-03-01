#!/usr/bin/env python3
"""
build_db.py
-----------
Reads a comparables Excel spreadsheet (.xlsm / .xlsx) and loads every record
into a local SQLite database (comparables.db).

Usage:
    python3 build_db.py                          # uses default file path
    python3 build_db.py path/to/spreadsheet.xlsm # custom file path
    python3 build_db.py --db custom.db path/to/spreadsheet.xlsm
"""

import argparse
import os
import re
import sqlite3
import sys
from datetime import datetime

import openpyxl

# ── File paths ────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE = os.path.join(BASE_DIR, "FINAL COMPARABLE SPREADSHEET 2026.xlsm")
DB_FILE    = os.path.join(BASE_DIR, "comparables.db")

# ── Normalisation maps ────────────────────────────────────────────────────────
PARISH_MAP = {
    "pembroke":              "Pembroke",
    "hamilton parish":       "Hamilton Parish",
    "hamilton":              "Hamilton",
    "southampton":           "Southampton",
    "sandys":                "Sandys",
    "st. george's":          "St. George's",
    "st. georges":           "St. George's",
    "st georges":            "St. George's",
    "st. david's":           "St. David's",
    "town of st george":     "Town of St. George",
    "town of st. george":    "Town of St. George",
    "town of st. georges":   "Town of St. George",
    "paget":                 "Paget",
    "smith's":               "Smith's",
    "smiths":                "Smith's",
    "devonshire":            "Devonshire",
    "warwick":               "Warwick",
    "wawrick":               "Warwick",
    "city of hamilton":      "City of Hamilton",
}

TYPE_MAP = {
    "multi-unit":                   "Multi-Unit",
    "multi-unit apartment":         "Multi-Unit Apartment",
    "multi-unit apartments":        "Multi-Unit Apartment",
    "condominium":                  "Condominium",
    "condominum":                   "Condominium",
    "house":                        "House",
    "house/apt":                    "House/Apartment",
    "house/apartment":              "House/Apartment",
    "house/cottage":                "House/Cottage",
    "land":                         "Land",
    "commercial":                   "Commercial",
    "townhouse":                    "Townhouse",
    "mixed-use":                    "Mixed-Use",
    "fractional":                   "Fractional",
    "apartment":                    "Apartment",
    "hotel condo (residential)":    "Hotel Condo (Residential)",
    "hotel condo":                  "Hotel Condo",
    "hotel":                        "Hotel",
    "tourist apartments":           "Tourist Apartments",
    "tourist apartment":            "Tourist Apartments",
    "duplex":                       "Duplex",
    "shop":                         "Commercial",
    "nursery school":               "Other / Commercial",
    "200b office":                  "Office",
    "office":                       "Office",
    "warehouse":                    "Warehouse",
    "workshop":                     "Workshop",
    "resturant":                    "Restaurant",
    "restaurant":                   "Restaurant",
}


def normalize_parish(val: str | None) -> str | None:
    if val is None:
        return None
    return PARISH_MAP.get(val.strip().lower(), val.strip())


def normalize_type(val: str | None) -> str | None:
    if val is None:
        return None
    return TYPE_MAP.get(val.strip().lower(), val.strip())


def parse_lot_size(val) -> tuple[str | None, float | None]:
    """Return (raw_text, numeric_acres).  Various input formats handled."""
    if val is None:
        return None, None
    raw = str(val).strip()
    # Pure number – treat as numeric (likely acres or ha as entered)
    try:
        num = float(raw)
        return raw, round(num, 4)
    except ValueError:
        pass
    # "0.087 Ha (0.215 Ac)"  →  take the acres figure
    m = re.search(r'\(([0-9.]+)\s*Ac\)', raw, re.IGNORECASE)
    if m:
        return raw, round(float(m.group(1)), 4)
    # "1.30 Acres"
    m = re.search(r'([0-9.]+)\s*Acres?', raw, re.IGNORECASE)
    if m:
        return raw, round(float(m.group(1)), 4)
    # "X Ha" → convert to acres
    m = re.search(r'([0-9.]+)\s*Ha\b', raw, re.IGNORECASE)
    if m:
        return raw, round(float(m.group(1)) * 2.47105, 4)
    return raw, None


def clean_yn(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip().upper()
    if s in ("Y", "YES", "1", "TRUE"):
        return "Y"
    if s in ("N", "NO", "0", "FALSE"):
        return "N"
    return None


def to_real(val) -> float | None:
    """Return float if val is numeric, else None."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def to_int(val) -> int | None:
    """Return int if val is numeric, else None."""
    if val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


# ── DDL ───────────────────────────────────────────────────────────────────────
CREATE_DDL = """
DROP TABLE IF EXISTS comparables;
CREATE TABLE comparables (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    property_name            TEXT,
    address                  TEXT,
    parish                   TEXT,
    parish_normalized        TEXT,
    price_sold               REAL,
    sale_date                TEXT,
    sale_year                INTEGER,
    sale_month               INTEGER,
    sq_ft                    REAL,
    beds                     INTEGER,
    baths                    REAL,
    lot_size_raw             TEXT,
    lot_size_acres           REAL,
    no_units                 INTEGER,
    arv                      REAL,
    assessment               REAL,
    property_type            TEXT,
    property_type_normalized TEXT,
    guest                    TEXT,
    pool                     TEXT,
    waterfront               TEXT,
    listed                   TEXT,
    zone                     TEXT,
    notes                    TEXT,
    country                  TEXT DEFAULT 'Bermuda'
);
CREATE INDEX idx_parish   ON comparables(parish_normalized);
CREATE INDEX idx_type     ON comparables(property_type_normalized);
CREATE INDEX idx_date     ON comparables(sale_date);
CREATE INDEX idx_price    ON comparables(price_sold);
CREATE INDEX idx_sq_ft    ON comparables(sq_ft);
CREATE INDEX idx_year     ON comparables(sale_year);
"""


# ── Main ─────────────────────────────────────────────────────────────────────
def build_database():
    if not os.path.exists(EXCEL_FILE):
        raise FileNotFoundError(f"Excel file not found: {EXCEL_FILE}")

    print(f"Loading: {EXCEL_FILE}")
    wb = openpyxl.load_workbook(EXCEL_FILE, read_only=True, keep_vba=False)
    ws = wb["Sheet1"]

    all_rows = [r for r in ws.iter_rows(values_only=True)
                if any(v is not None for v in r)]
    header   = all_rows[0]
    data     = all_rows[1:]
    print(f"Rows to process: {len(data)}")

    # Map column name → index (first 19 named columns)
    col = {name: idx for idx, name in enumerate(header) if name}

    def g(row, name, default=None):
        idx = col.get(name)
        if idx is None:
            return default
        v = row[idx]
        return v if v is not None else default

    conn = sqlite3.connect(DB_FILE)
    cur  = conn.cursor()
    cur.executescript(CREATE_DDL)

    inserted = skipped = 0
    for row in data:
        # Skip rows with no meaningful data
        parish_raw = g(row, "Parish")
        price      = g(row, "Price Sold")
        prop_name  = g(row, "Property Name")
        if parish_raw is None and price is None and prop_name is None:
            skipped += 1
            continue

        # Date
        sale_date_val = g(row, "Date")
        if isinstance(sale_date_val, datetime):
            sale_date_str = sale_date_val.strftime("%Y-%m-%d")
            sale_year     = sale_date_val.year
            sale_month    = sale_date_val.month
        else:
            sale_date_str = None
            sale_year     = None
            sale_month    = None

        lot_raw, lot_acres = parse_lot_size(g(row, "Lot Size"))

        cur.execute(
            """
            INSERT INTO comparables (
                property_name, address,
                parish, parish_normalized,
                price_sold, sale_date, sale_year, sale_month,
                sq_ft, beds, baths,
                lot_size_raw, lot_size_acres,
                no_units, arv, assessment,
                property_type, property_type_normalized,
                guest, pool, waterfront, listed,
                zone, notes, country
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                prop_name,
                g(row, "Address"),
                parish_raw,
                normalize_parish(parish_raw),
                to_real(price),
                sale_date_str, sale_year, sale_month,
                to_real(g(row, "Sq. ft.")),
                to_int(g(row, "Bed ")),
                to_real(g(row, "Bath")),
                lot_raw, lot_acres,
                to_int(g(row, "No. Units")),
                to_real(g(row, "ARV")),
                to_real(g(row, "Assessment")),
                g(row, "Type"),
                normalize_type(g(row, "Type")),
                clean_yn(g(row, "Guest")),
                clean_yn(g(row, "Pool")),
                clean_yn(g(row, "Waterfront")),
                clean_yn(g(row, "Listed")),
                g(row, "Zone"),
                g(row, "Notes"),
                "Bermuda",
            ),
        )
        inserted += 1

    conn.commit()
    conn.close()
    print(f"Done: {inserted} records inserted, {skipped} blank rows skipped.")
    print(f"Database saved to: {DB_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import a comparables Excel spreadsheet into SQLite."
    )
    parser.add_argument(
        "excel",
        nargs="?",
        default=None,
        metavar="SPREADSHEET",
        help="Path to the .xlsm / .xlsx file (default: %(default)s)",
    )
    parser.add_argument(
        "--db",
        default=None,
        metavar="DATABASE",
        help="Path for the output SQLite file (default: comparables.db)",
    )
    args = parser.parse_args()

    if args.excel:
        EXCEL_FILE = os.path.abspath(args.excel)
    if args.db:
        DB_FILE = os.path.abspath(args.db)

    if not os.path.exists(EXCEL_FILE):
        print(f"Error: spreadsheet not found at:\n  {EXCEL_FILE}")
        print()
        print("Usage:  python3 build_db.py path/to/spreadsheet.xlsm")
        sys.exit(1)

    build_database()
