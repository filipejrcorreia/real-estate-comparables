"""
conftest.py – shared pytest fixtures
"""

import sqlite3
import sys

import pandas as pd
import pytest

# ── DDL (copy of build_db.CREATE_DDL, minus the DROP) ────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS comparables (
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
"""

# ── Sample rows ──────────────────────────────────────────────────────────────
SAMPLE_ROWS = [
    # (property_name, address, parish, parish_normalized, price_sold, sale_date,
    #  sale_year, sale_month, sq_ft, beds, baths, lot_size_raw, lot_size_acres,
    #  no_units, arv, assessment, property_type, property_type_normalized,
    #  guest, pool, waterfront, listed, zone, notes, country)
    ("Sunrise Villa",  "1 Ocean Road",     "Pembroke",  "Pembroke",     980000, "2024-03-15", 2024, 3, 2500, 4, 3, "0.25", 0.25, 1, 48000, 120000, "House",       "House",       "N", "Y", "N", "N", "110", None, "Bermuda"),
    ("Harbour View",   "5 Harbour Lane",   "Paget",     "Paget",        650000, "2024-07-20", 2024, 7, 1800, 3, 2, "0.15", 0.15, 1, 36000, 90000,  "Condominium", "Condominium", "Y", "N", "Y", "N", "120", None, "Bermuda"),
    ("Sea Breeze",     "12 Bay Street",    "Warwick",   "Warwick",     1200000, "2023-11-05", 2023, 11, 3200, 5, 4, "0.50", 0.50, 2, 72000, 180000, "House",       "House",       "N", "Y", "Y", "Y", "130", None, "Bermuda"),
    ("The Cottage",    "3 Garden Close",   "Sandys",    "Sandys",       420000, "2023-06-10", 2023, 6,  900, 2, 1, None,  None, 1, 18000,  42000, "Apartment",   "Apartment",   "N", "N", "N", "N", "110", None, "Bermuda"),
    ("Commercial Bld", "9 Main Street",    "Hamilton",  "Hamilton",    1500000, "2025-01-18", 2025, 1, None, 0, 0, "1.00", 1.00, 5, 60000, 350000, "Commercial",  "Commercial",  "N", "N", "N", "Y", "060", None, "Bermuda"),
    ("No Price Prop",  "7 Mystery Lane",   "Devonshire","Devonshire",     None, None,         None, None,1400, 3, 2, None,  None, 1, 30000,  80000, "House",       "House",       "N", "N", "N", "N", "110", None, "Bermuda"),
]


@pytest.fixture(scope="session")
def test_db_path(tmp_path_factory):
    """Create a temp SQLite file populated with SAMPLE_ROWS once per session."""
    db_path = tmp_path_factory.mktemp("db") / "test_comparables.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    conn.executemany(
        """
        INSERT INTO comparables (
            property_name, address, parish, parish_normalized,
            price_sold, sale_date, sale_year, sale_month,
            sq_ft, beds, baths, lot_size_raw, lot_size_acres,
            no_units, arv, assessment,
            property_type, property_type_normalized,
            guest, pool, waterfront, listed, zone, notes, country
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        SAMPLE_ROWS,
    )
    conn.commit()
    conn.close()
    return str(db_path)


@pytest.fixture()
def mem_db(test_db_path):
    """Fresh connection per test so tests can close() without destroying data."""
    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    try:
        conn.close()
    except Exception:
        pass


@pytest.fixture()
def sample_df():
    """Pandas DataFrame matching the columns returned by app.query()."""
    return pd.DataFrame(
        {
            "id":            [1, 2, 3, 4, 5, 6],
            "property_name": ["Sunrise Villa", "Harbour View", "Sea Breeze",
                               "The Cottage", "Commercial Bld", "No Price Prop"],
            "address":       ["1 Ocean Road", "5 Harbour Lane", "12 Bay Street",
                               "3 Garden Close", "9 Main Street", "7 Mystery Lane"],
            "parish":        ["Pembroke", "Paget", "Warwick", "Sandys", "Hamilton", "Devonshire"],
            "type":          ["House", "Condominium", "House", "Apartment", "Commercial", "House"],
            "price_sold":    [980000, 650000, 1200000, 420000, 1500000, None],
            "sale_date":     ["2024-03-15", "2024-07-20", "2023-11-05",
                               "2023-06-10", "2025-01-18", None],
            "sq_ft":         [2500, 1800, 3200, 900, None, 1400],
            "beds":          [4, 3, 5, 2, 0, 3],
            "baths":         [3, 2, 4, 1, 0, 2],
            "lot_size":      ["0.25", "0.15", "0.50", None, "1.00", None],
            "lot_size_acres":[0.25, 0.15, 0.50, None, 1.00, None],
            "units":         [1, 1, 2, 1, 5, 1],
            "arv":           [48000, 36000, 72000, 18000, 60000, 30000],
            "assessment":    [120000, 90000, 180000, 42000, 350000, 80000],
            "guest":         ["N", "Y", "N", "N", "N", "N"],
            "pool":          ["Y", "N", "Y", "N", "N", "N"],
            "waterfront":    ["N", "Y", "Y", "N", "N", "N"],
            "listed":        ["N", "N", "Y", "N", "Y", "N"],
            "zone":          ["110", "120", "130", "110", "060", "110"],
            "notes":         [None, None, None, None, None, None],
            "country":       ["Bermuda"] * 6,
        }
    )
