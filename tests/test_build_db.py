"""
test_build_db.py – Unit & integration tests for build_db.py
============================================================
Run:  pytest tests/test_build_db.py -v
"""

import sqlite3
import tempfile
import os
from datetime import datetime
from pathlib import Path

import pytest

# Ensure project root is on path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_db import (
    normalize_parish,
    normalize_type,
    parse_lot_size,
    clean_yn,
    to_real,
    to_int,
    build_database,
    CREATE_DDL,
)


# ═══════════════════════════════════════════════════════════════════════════════
# normalize_parish
# ═══════════════════════════════════════════════════════════════════════════════

class TestNormalizeParish:
    def test_none_returns_none(self):
        assert normalize_parish(None) is None

    def test_exact_match_lowercase(self):
        assert normalize_parish("pembroke") == "Pembroke"

    def test_case_insensitive(self):
        assert normalize_parish("PEMBROKE") == "Pembroke"
        assert normalize_parish("Pembroke") == "Pembroke"

    def test_leading_trailing_whitespace(self):
        assert normalize_parish("  Paget  ") == "Paget"

    def test_typo_wawrick_mapped_to_warwick(self):
        assert normalize_parish("Wawrick") == "Warwick"

    def test_smiths_variants(self):
        assert normalize_parish("Smiths")   == "Smith's"
        assert normalize_parish("Smith's")  == "Smith's"

    def test_st_georges_variants(self):
        assert normalize_parish("St. George's") == "St. George's"
        assert normalize_parish("St. Georges")  == "St. George's"
        assert normalize_parish("St Georges")   == "St. George's"

    def test_town_of_st_george_variants(self):
        assert normalize_parish("Town of St George")   == "Town of St. George"
        assert normalize_parish("Town of St. George")  == "Town of St. George"
        assert normalize_parish("Town of St. Georges") == "Town of St. George"

    def test_city_of_hamilton_with_trailing_space(self):
        # "City of Hamilton " comes from the real spreadsheet
        assert normalize_parish("City of Hamilton ") == "City of Hamilton"

    def test_unknown_value_returned_as_is(self):
        # Values not in the map are returned stripped
        assert normalize_parish("  New Country  ") == "New Country"

    def test_hamilton_parish_vs_hamilton(self):
        assert normalize_parish("Hamilton Parish") == "Hamilton Parish"
        assert normalize_parish("Hamilton")        == "Hamilton"


# ═══════════════════════════════════════════════════════════════════════════════
# normalize_type
# ═══════════════════════════════════════════════════════════════════════════════

class TestNormalizeType:
    def test_none_returns_none(self):
        assert normalize_type(None) is None

    def test_typo_resturant(self):
        assert normalize_type("Resturant") == "Restaurant"
        assert normalize_type("resturant") == "Restaurant"

    def test_condominum_typo(self):
        assert normalize_type("Condominum") == "Condominium"

    def test_house_apt_aliases(self):
        assert normalize_type("House/Apt")       == "House/Apartment"
        assert normalize_type("House/apartment") == "House/Apartment"
        assert normalize_type("house/apt")       == "House/Apartment"

    def test_shop_maps_to_commercial(self):
        assert normalize_type("Shop") == "Commercial"

    def test_multi_unit_variants(self):
        assert normalize_type("Multi-unit")           == "Multi-Unit"
        assert normalize_type("Multi-Unit Apartment") == "Multi-Unit Apartment"
        assert normalize_type("Multi-unit apartments")== "Multi-Unit Apartment"

    def test_case_insensitive_and_stripped(self):
        assert normalize_type("  HOUSE  ") == "House"

    def test_unknown_value_returned_as_is(self):
        assert normalize_type("Unique Custom Type") == "Unique Custom Type"


# ═══════════════════════════════════════════════════════════════════════════════
# parse_lot_size
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseLotSize:
    def test_none(self):
        raw, acres = parse_lot_size(None)
        assert raw is None
        assert acres is None

    def test_plain_float(self):
        raw, acres = parse_lot_size(0.37)
        assert raw == "0.37"
        assert acres == pytest.approx(0.37, rel=1e-4)

    def test_plain_int(self):
        raw, acres = parse_lot_size(1)
        assert acres == pytest.approx(1.0, rel=1e-4)

    def test_ha_with_acres_suffix(self):
        # "0.087 Ha (0.215 Ac)"
        raw, acres = parse_lot_size("0.087 Ha (0.215 Ac)")
        assert raw == "0.087 Ha (0.215 Ac)"
        assert acres == pytest.approx(0.215, rel=1e-4)

    def test_acres_text(self):
        raw, acres = parse_lot_size("1.30 Acres")
        assert acres == pytest.approx(1.30, rel=1e-4)

    def test_acre_singular(self):
        raw, acres = parse_lot_size("1.023 Acres")
        assert acres == pytest.approx(1.023, rel=1e-4)

    def test_ha_only_converted(self):
        # 1 Ha = 2.47105 Acres
        raw, acres = parse_lot_size("1.446 Ha (3.574 Ac)")
        # Should prefer the bracket figure
        assert acres == pytest.approx(3.574, rel=1e-4)

    def test_pure_ha_with_no_bracket(self):
        raw, acres = parse_lot_size("2 Ha")
        assert acres == pytest.approx(2 * 2.47105, rel=1e-4)

    def test_unparseable_text_returns_none_acres(self):
        raw, acres = parse_lot_size("some description")
        assert raw == "some description"
        assert acres is None

    def test_zero_numeric(self):
        raw, acres = parse_lot_size(0)
        assert acres == pytest.approx(0.0, rel=1e-4)


# ═══════════════════════════════════════════════════════════════════════════════
# clean_yn
# ═══════════════════════════════════════════════════════════════════════════════

class TestCleanYn:
    def test_none(self):
        assert clean_yn(None) is None

    def test_y_variants(self):
        for v in ("Y", "y", "YES", "yes", "1", "TRUE", "True"):
            assert clean_yn(v) == "Y", f"Expected 'Y' for {v!r}"

    def test_n_variants(self):
        for v in ("N", "n", "NO", "no", "0", "FALSE", "False"):
            assert clean_yn(v) == "N", f"Expected 'N' for {v!r}"

    def test_backtick_unknown(self):
        # A stray backtick that appeared in the real data
        assert clean_yn("`") is None

    def test_whitespace_stripped(self):
        assert clean_yn("  Y  ") == "Y"
        assert clean_yn("  N  ") == "N"


# ═══════════════════════════════════════════════════════════════════════════════
# to_real / to_int
# ═══════════════════════════════════════════════════════════════════════════════

class TestToReal:
    def test_none(self):
        assert to_real(None) is None

    def test_integer(self):
        assert to_real(42) == pytest.approx(42.0)

    def test_float(self):
        assert to_real(3.14) == pytest.approx(3.14)

    def test_numeric_string(self):
        assert to_real("1500000") == pytest.approx(1_500_000.0)

    def test_text_returns_none(self):
        assert to_real("res 2") is None
        assert to_real("N/A")  is None
        assert to_real("")     is None

    def test_zero(self):
        assert to_real(0) == pytest.approx(0.0)


class TestToInt:
    def test_none(self):
        assert to_int(None) is None

    def test_integer(self):
        assert to_int(5) == 5

    def test_float_truncated(self):
        assert to_int(2.9) == 2

    def test_numeric_string(self):
        assert to_int("4") == 4

    def test_text_returns_none(self):
        assert to_int("res 2") is None
        assert to_int("abc")   is None

    def test_zero(self):
        assert to_int(0) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# build_database – integration test with a real temp Excel file
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildDatabase:
    """Full integration test: create a minimal .xlsm, run build_database(), check DB."""

    def _make_xlsx(self, path: Path):
        """Write a minimal spreadsheet with 3 data rows to the given path."""
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"

        headers = [
            "Property Name", "Address", "Parish", "Price Sold", "Date",
            "Sq. ft.", "Bed ", "Bath", "Lot Size", "No. Units",
            "ARV", "Assessment", "Type", "Guest", "Pool",
            "Waterfront", "Listed", "Zone", "Notes",
        ]
        ws.append(headers)

        ws.append([
            "Test House", "1 Test Road", "Pembroke", 750000,
            datetime(2024, 5, 1), 2000, 3, 2, "0.25", 1,
            36000, 90000, "House", "N", "Y",
            "N", "N", "110", None,
        ])
        ws.append([
            "Test Condo", "2 Condo Lane", "Smiths", 500000,
            datetime(2023, 8, 15), 1200, 2, 1, None, 1,
            24000, 60000, "Condominium", "Y", "N",
            "Y", "N", "120", "Corner unit",
        ])
        ws.append([
            # A row with non-numeric sq_ft (the original bug scenario)
            "Bad Sqft Row", "3 Weird Lane", "Warwick", 300000,
            datetime(2023, 3, 3), "res 2", 1, 1, None, 1,
            15000, 40000, "Apartment", "N", "N",
            "N", "N", "110", None,
        ])

        # Save as .xlsm by changing the extension but using regular xlsx format
        wb.save(str(path))

    def test_full_pipeline(self, tmp_path):
        import importlib
        import build_db as bdb

        excel_path = tmp_path / "FINAL COMPARABLE SPREADSHEET 2026.xlsm"
        db_path    = tmp_path / "comparables.db"
        self._make_xlsx(excel_path)

        # Monkey-patch module paths to point to tmp_path
        orig_excel = bdb.EXCEL_FILE
        orig_db    = bdb.DB_FILE
        bdb.EXCEL_FILE = str(excel_path)
        bdb.DB_FILE    = str(db_path)
        try:
            bdb.build_database()
        finally:
            bdb.EXCEL_FILE = orig_excel
            bdb.DB_FILE    = orig_db

        assert db_path.exists(), "Database file was not created"

        conn = sqlite3.connect(str(db_path))
        cur  = conn.cursor()

        # 3 rows inserted (none are fully blank)
        cur.execute("SELECT COUNT(*) FROM comparables")
        assert cur.fetchone()[0] == 3

        # Parish normalisation applied
        cur.execute("SELECT parish_normalized FROM comparables WHERE property_name='Test House'")
        assert cur.fetchone()[0] == "Pembroke"

        cur.execute("SELECT parish_normalized FROM comparables WHERE property_name='Test Condo'")
        assert cur.fetchone()[0] == "Smith's"   # "Smiths" → "Smith's"

        # Type normalisation
        cur.execute("SELECT property_type_normalized FROM comparables WHERE property_name='Test House'")
        assert cur.fetchone()[0] == "House"

        # Non-numeric sq_ft stored as NULL (not crashing)
        cur.execute("SELECT sq_ft FROM comparables WHERE property_name='Bad Sqft Row'")
        assert cur.fetchone()[0] is None

        # Date fields parsed correctly
        cur.execute("SELECT sale_year, sale_month FROM comparables WHERE property_name='Test House'")
        row = cur.fetchone()
        assert row[0] == 2024
        assert row[1] == 5

        # pool / guest flags cleaned
        cur.execute("SELECT pool, guest FROM comparables WHERE property_name='Test House'")
        row = cur.fetchone()
        assert row[0] == "Y"
        assert row[1] == "N"

        conn.close()

    def test_missing_excel_raises(self, tmp_path):
        import build_db as bdb
        orig_excel = bdb.EXCEL_FILE
        bdb.EXCEL_FILE = str(tmp_path / "nonexistent.xlsm")
        try:
            with pytest.raises(FileNotFoundError):
                bdb.build_database()
        finally:
            bdb.EXCEL_FILE = orig_excel
