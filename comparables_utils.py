"""
comparables_utils.py
--------------------
Pure-Python helpers shared between app.py and the test suite.
No Streamlit dependency — safe to import anywhere.
"""

import io
import sqlite3
from datetime import date, datetime

import pandas as pd


# ── Currency formatter ────────────────────────────────────────────────────────

def fmt_currency(val) -> str:
    if pd.isna(val):
        return ""
    return f"${val:,.0f}"


# ── Summary statistics ────────────────────────────────────────────────────────

def summary_stats(df: pd.DataFrame) -> dict:
    prices = df["price_sold"].dropna()
    sqfts  = df["sq_ft"].dropna()
    return {
        "count":      len(df),
        "with_price": len(prices),
        "min_price":  prices.min()    if len(prices) else None,
        "max_price":  prices.max()    if len(prices) else None,
        "avg_price":  prices.mean()   if len(prices) else None,
        "med_price":  prices.median() if len(prices) else None,
        "avg_sqft":   sqfts.mean()    if len(sqfts)  else None,
        "price_per_sqft": (
            prices / df.loc[prices.index, "sq_ft"].replace(0, pd.NA)
        ).dropna().mean() if len(prices) else None,
    }


# ── CSV export ────────────────────────────────────────────────────────────────

def to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


# ── Excel export ──────────────────────────────────────────────────────────────

def to_excel(df: pd.DataFrame, stats: dict) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        wb = writer.book

        hdr_fmt   = wb.add_format({"bold": True, "bg_color": "#1F3864",
                                   "font_color": "white", "border": 1})
        money_fmt = wb.add_format({"num_format": "$#,##0", "border": 1})
        title_fmt = wb.add_format({"bold": True, "font_size": 14,
                                   "font_color": "#1F3864"})
        label_fmt = wb.add_format({"bold": True})

        # ── Sheet 1: Comparables ─────────────────────────────────────────────
        df_export = df.copy()
        df_export.to_excel(writer, index=False, sheet_name="Comparables",
                           startrow=2)
        ws1 = writer.sheets["Comparables"]
        ws1.write(0, 0, "Comparable Sales – Export", title_fmt)
        ws1.write(1, 0,
                  f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  "
                  f"Records: {stats['count']}")

        for col_num, col_name in enumerate(df_export.columns):
            ws1.write(2, col_num, col_name, hdr_fmt)

        col_map = {c: i for i, c in enumerate(df_export.columns)}
        ws1.set_column(col_map.get("price_sold", 4),
                       col_map.get("price_sold", 4), 14, money_fmt)
        ws1.set_column(col_map.get("arv", 12),
                       col_map.get("arv", 12), 14, money_fmt)
        ws1.set_column(col_map.get("assessment", 13),
                       col_map.get("assessment", 13), 16, money_fmt)
        ws1.set_column(0, 0, 24)
        ws1.set_column(1, 1, 28)
        ws1.set_column(2, 2, 18)
        ws1.set_column(5, 5, 12)
        ws1.set_column(14, 14, 22)
        ws1.freeze_panes(3, 0)

        # ── Sheet 2: Summary ─────────────────────────────────────────────────
        ws2 = wb.add_worksheet("Summary")
        ws2.set_column(0, 0, 28)
        ws2.set_column(1, 1, 20)
        ws2.write(0, 0, "Summary Statistics", title_fmt)
        ws2.write(1, 0,
                  f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        rows_s = [
            ("Total Records",           stats["count"],          None),
            ("Records with Sale Price", stats["with_price"],     None),
            ("Minimum Sale Price",      stats["min_price"],      "$#,##0"),
            ("Maximum Sale Price",      stats["max_price"],      "$#,##0"),
            ("Average Sale Price",      stats["avg_price"],      "$#,##0"),
            ("Median Sale Price",       stats["med_price"],      "$#,##0"),
            ("Average Sq. Ft.",         stats["avg_sqft"],       "#,##0.0"),
            ("Avg Price / Sq. Ft.",     stats["price_per_sqft"], "$#,##0.00"),
        ]
        for i, (label, value, num_fmt) in enumerate(rows_s, start=3):
            ws2.write(i, 0, label, label_fmt)
            if value is None:
                ws2.write(i, 1, "N/A")
            elif num_fmt:
                ws2.write(i, 1, value, wb.add_format({"num_format": num_fmt}))
            else:
                ws2.write(i, 1, value)

        if not df.empty:
            ws2.write(13, 0, "Records by Parish", title_fmt)
            parish_counts = df["parish"].value_counts().reset_index()
            parish_counts.columns = ["Parish", "Count"]
            parish_counts.to_excel(writer, index=False,
                                   sheet_name="Summary", startrow=14)

            ws2.write(14 + len(parish_counts) + 2, 0,
                      "Records by Property Type", title_fmt)
            type_counts = df["type"].value_counts().reset_index()
            type_counts.columns = ["Type", "Count"]
            type_counts.to_excel(writer, index=False, sheet_name="Summary",
                                  startrow=14 + len(parish_counts) + 3)

    return buf.getvalue()


# ── Query builder ─────────────────────────────────────────────────────────────

def build_query_sql(filters: dict) -> tuple[str, list]:
    """Return (sql_string, params_list) for the given filter dict."""
    conditions: list[str] = ["1=1"]
    params: list = []

    def add(cond, *vals):
        conditions.append(cond)
        params.extend(vals)

    if filters.get("search"):
        add("(property_name LIKE ? OR address LIKE ?)",
            f"%{filters['search']}%", f"%{filters['search']}%")

    if filters.get("parishes"):
        ph = ",".join("?" * len(filters["parishes"]))
        add(f"parish_normalized IN ({ph})", *filters["parishes"])

    if filters.get("types"):
        ph = ",".join("?" * len(filters["types"]))
        add(f"property_type_normalized IN ({ph})", *filters["types"])

    if filters.get("zones"):
        ph = ",".join("?" * len(filters["zones"]))
        add(f"zone IN ({ph})", *filters["zones"])

    if filters.get("country"):
        add("country = ?", filters["country"])

    if filters.get("price_min") is not None:
        add("price_sold >= ?", filters["price_min"])
    if filters.get("price_max") is not None:
        add("price_sold <= ?", filters["price_max"])

    if filters.get("date_from"):
        dt = filters["date_from"]
        add("sale_date >= ?",
            dt.strftime("%Y-%m-%d") if isinstance(dt, (date, datetime)) else str(dt))
    if filters.get("date_to"):
        dt = filters["date_to"]
        add("sale_date <= ?",
            dt.strftime("%Y-%m-%d") if isinstance(dt, (date, datetime)) else str(dt))

    if filters.get("sqft_min") is not None:
        add("sq_ft >= ?", filters["sqft_min"])
    if filters.get("sqft_max") is not None:
        add("sq_ft <= ?", filters["sqft_max"])

    if filters.get("lot_min") is not None:
        add("lot_size_acres >= ?", filters["lot_min"])
    if filters.get("lot_max") is not None:
        add("lot_size_acres <= ?", filters["lot_max"])

    if filters.get("beds_min") is not None:
        add("beds >= ?", filters["beds_min"])
    if filters.get("beds_max") is not None:
        add("beds <= ?", filters["beds_max"])
    if filters.get("baths_min") is not None:
        add("baths >= ?", filters["baths_min"])

    if filters.get("units_min") is not None:
        add("no_units >= ?", filters["units_min"])
    if filters.get("units_max") is not None:
        add("no_units <= ?", filters["units_max"])

    for flag in ("pool", "guest", "waterfront", "listed"):
        val = filters.get(flag)
        if val and val != "All":
            add(f"{flag} = ?", val)

    sql = (
        "SELECT id, property_name, address, parish_normalized AS parish, "
        "       price_sold, sale_date, sq_ft, beds, baths, "
        "       lot_size_raw AS lot_size, lot_size_acres, "
        "       no_units AS units, arv, assessment, "
        "       property_type_normalized AS type, "
        "       guest, pool, waterfront, listed, zone, notes, country "
        "FROM comparables "
        f"WHERE {' AND '.join(conditions)} "
        "ORDER BY sale_date DESC"
    )
    return sql, params


def run_query(conn: sqlite3.Connection, filters: dict) -> pd.DataFrame:
    """Execute a filter query against an open SQLite connection."""
    sql, params = build_query_sql(filters)
    return pd.read_sql_query(sql, conn, params=params)
