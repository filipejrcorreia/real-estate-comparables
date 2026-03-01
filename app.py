"""
app.py – Real Estate Comparables Search & Reporting Tool
=========================================================
Run with:
    streamlit run app.py
"""

import os
import sqlite3
import subprocess
import sys
from datetime import date, datetime

import pandas as pd
import streamlit as st

from comparables_utils import (
    fmt_currency,
    summary_stats,
    to_csv,
    to_excel,
    run_query,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE  = os.path.join(BASE_DIR, "comparables.db")

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Comparables Database",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Ensure DB exists ──────────────────────────────────────────────────────────
if not os.path.exists(DB_FILE):
    st.warning("Database not found – building it now from the Excel file…")
    result = subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, "build_db.py")],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        st.error(f"Build failed:\n{result.stderr}")
        st.stop()
    st.success("Database built successfully! Reloading…")
    st.rerun()

# ── DB helpers ────────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@st.cache_data(ttl=300)
def load_lookup_data():
    conn = get_conn()
    parishes = pd.read_sql_query(
        "SELECT DISTINCT parish_normalized v FROM comparables "
        "WHERE parish_normalized IS NOT NULL ORDER BY v",
        conn,
    )["v"].tolist()

    types = pd.read_sql_query(
        "SELECT DISTINCT property_type_normalized v FROM comparables "
        "WHERE property_type_normalized IS NOT NULL ORDER BY v",
        conn,
    )["v"].tolist()

    zones = pd.read_sql_query(
        "SELECT DISTINCT zone v FROM comparables "
        "WHERE zone IS NOT NULL AND length(trim(zone)) BETWEEN 3 AND 10 "
        "ORDER BY v",
        conn,
    )["v"].tolist()

    price_row = pd.read_sql_query(
        "SELECT MIN(price_sold) mn, MAX(price_sold) mx FROM comparables "
        "WHERE price_sold IS NOT NULL",
        conn,
    ).iloc[0]

    date_row = pd.read_sql_query(
        "SELECT MIN(sale_date) mn, MAX(sale_date) mx FROM comparables "
        "WHERE sale_date IS NOT NULL",
        conn,
    ).iloc[0]

    sqft_row = pd.read_sql_query(
        "SELECT MIN(CAST(sq_ft AS REAL)) mn, MAX(CAST(sq_ft AS REAL)) mx "
        "FROM comparables "
        "WHERE sq_ft IS NOT NULL AND typeof(sq_ft) IN ('real','integer')",
        conn,
    ).iloc[0]

    lot_row = pd.read_sql_query(
        "SELECT MIN(CAST(lot_size_acres AS REAL)) mn, MAX(CAST(lot_size_acres AS REAL)) mx "
        "FROM comparables "
        "WHERE lot_size_acres IS NOT NULL AND typeof(lot_size_acres) IN ('real','integer')",
        conn,
    ).iloc[0]

    conn.close()
    return parishes, types, zones, price_row, date_row, sqft_row, lot_row


def query(filters: dict) -> pd.DataFrame:
    """Run a filtered query against the database and return a DataFrame."""
    conn = get_conn()
    df = run_query(conn, filters)
    conn.close()
    return df


# fmt_currency, summary_stats, to_csv, to_excel imported from comparables_utils


# ═══════════════════════════════════════════════════════════════════════════════
#  UI
# ═══════════════════════════════════════════════════════════════════════════════

parishes, types, zones, price_row, date_row, sqft_row, lot_row = load_lookup_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/real-estate.png", width=56)
    st.title("Search Filters")
    st.caption("Leave a field blank to include all values.")

    # Text search
    search_text = st.text_input("🔍 Property name / address", "")

    st.divider()
    st.subheader("📍 Location")

    selected_parishes = st.multiselect("Parish / Region", parishes)
    country_opt = st.selectbox("Country", ["All", "Bermuda"])

    st.divider()
    st.subheader("🏠 Property")

    selected_types = st.multiselect("Property Type", types)
    selected_zones = st.multiselect("Zone Code", zones)

    col_g, col_p = st.columns(2)
    guest_opt      = col_g.selectbox("Guest Apt", ["All", "Y", "N"])
    pool_opt       = col_p.selectbox("Pool", ["All", "Y", "N"])
    col_w, col_l   = st.columns(2)
    waterfront_opt = col_w.selectbox("Waterfront", ["All", "Y", "N"])
    listed_opt     = col_l.selectbox("Listed", ["All", "Y", "N"])

    st.divider()
    st.subheader("💰 Price (USD)")

    try:
        price_min_v = int(float(price_row["mn"])) if price_row["mn"] not in (None, "") else 0
    except (ValueError, TypeError):
        price_min_v = 0
    try:
        price_max_v = int(float(price_row["mx"])) if price_row["mx"] not in (None, "") else 10_000_000
    except (ValueError, TypeError):
        price_max_v = 10_000_000
    price_range = st.slider(
        "Sale Price Range",
        min_value=0,
        max_value=price_max_v,
        value=(price_min_v, price_max_v),
        step=10_000,
        format="$%d",
    )

    st.divider()
    st.subheader("📅 Sale Date")

    min_date = date(2020, 1, 1)
    max_date = date.today()
    if date_row["mn"]:
        min_date = datetime.strptime(str(date_row["mn"])[:10], "%Y-%m-%d").date()
    if date_row["mx"]:
        max_date = datetime.strptime(str(date_row["mx"])[:10], "%Y-%m-%d").date()

    date_from = st.date_input("From", value=min_date,
                              min_value=min_date, max_value=max_date)
    date_to   = st.date_input("To",   value=max_date,
                              min_value=min_date, max_value=max_date)

    st.divider()
    st.subheader("📐 Size / Lot")

    try:
        sqft_max_v = int(float(sqft_row["mx"])) if sqft_row["mx"] not in (None, "") else 20_000
    except (ValueError, TypeError):
        sqft_max_v = 20_000
    sqft_range = st.slider("Sq. Ft. Range", 0, sqft_max_v,
                            (0, sqft_max_v), step=100)

    try:
        lot_max_v = round(float(lot_row["mx"]), 2) if lot_row["mx"] not in (None, "") else 10.0
    except (ValueError, TypeError):
        lot_max_v = 10.0
    lot_range  = st.slider("Lot Size (acres)", 0.0, lot_max_v,
                           (0.0, lot_max_v), step=0.01)

    st.divider()
    st.subheader("🛏 Beds / Baths / Units")

    c1, c2 = st.columns(2)
    beds_min  = c1.number_input("Beds min",  min_value=0, value=0, step=1)
    beds_max  = c2.number_input("Beds max",  min_value=0, value=10, step=1)
    baths_min = c1.number_input("Baths min", min_value=0, value=0, step=1)
    c_u1, c_u2 = st.columns(2)
    units_min = c_u1.number_input("Units min", min_value=0, value=0, step=1)
    units_max = c_u2.number_input("Units max", min_value=0, value=50, step=1)

    st.divider()
    run_search = st.button("🔎 Search", use_container_width=True, type="primary")
    clear      = st.button("↺ Reset Filters", use_container_width=True)

# ── Reset ─────────────────────────────────────────────────────────────────────
if clear:
    st.rerun()

# ── Build filters dict ────────────────────────────────────────────────────────
filters: dict = {
    "search":     search_text.strip() or None,
    "parishes":   selected_parishes or None,
    "types":      selected_types    or None,
    "zones":      selected_zones    or None,
    "country":    None if country_opt == "All" else country_opt,
    "price_min":  price_range[0] if price_range[0] > 0          else None,
    "price_max":  price_range[1] if price_range[1] < price_max_v else None,
    "date_from":  date_from,
    "date_to":    date_to,
    "sqft_min":   sqft_range[0] if sqft_range[0] > 0            else None,
    "sqft_max":   sqft_range[1] if sqft_range[1] < sqft_max_v   else None,
    "lot_min":    lot_range[0]  if lot_range[0]  > 0            else None,
    "lot_max":    lot_range[1]  if lot_range[1]  < lot_max_v    else None,
    "beds_min":   beds_min  if beds_min  > 0  else None,
    "beds_max":   beds_max  if beds_max  < 10 else None,
    "baths_min":  baths_min if baths_min > 0  else None,
    "units_min":  units_min if units_min > 0  else None,
    "units_max":  units_max if units_max < 50 else None,
    "pool":       pool_opt,
    "guest":      guest_opt,
    "waterfront": waterfront_opt,
    "listed":     listed_opt,
}

# ── Always show results (auto-search) ─────────────────────────────────────────
df = query(filters)
stats = summary_stats(df)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🏠 Real Estate Comparables Database")
st.caption(
    "Bermuda comparable sales data · "
    f"Database: **{DB_FILE.split('/')[-1]}** · "
    f"Last refreshed: run `python3 build_db.py` after updating the spreadsheet"
)

# ── KPI strip ─────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Matching Records",   f"{stats['count']:,}")
k2.metric("Avg Sale Price",
          fmt_currency(stats["avg_price"]) if stats["avg_price"] else "—")
k3.metric("Median Sale Price",
          fmt_currency(stats["med_price"]) if stats["med_price"] else "—")
k4.metric("Min Price",
          fmt_currency(stats["min_price"]) if stats["min_price"] else "—")
k5.metric("Max Price",
          fmt_currency(stats["max_price"]) if stats["max_price"] else "—")

st.divider()

# ── Tabs: Results | Charts | Export ──────────────────────────────────────────
tab_res, tab_chart, tab_export = st.tabs(
    ["📋 Results Table", "📊 Charts & Analytics", "⬇️ Export / Report"]
)

# ────────────────────────────────────────────────────────── Results Table ─────
with tab_res:
    if df.empty:
        st.info("No records match the current filters.")
    else:
        # Display columns (drop raw IDs / technical cols)
        display_cols = [
            "property_name", "address", "parish", "type",
            "price_sold", "sale_date",
            "sq_ft", "beds", "baths",
            "lot_size", "lot_size_acres", "units",
            "arv", "assessment",
            "guest", "pool", "waterfront", "listed",
            "zone", "notes", "country",
        ]
        display_cols = [c for c in display_cols if c in df.columns]
        show_df = df[display_cols].copy()

        # Friendly column names
        rename = {
            "property_name": "Property",
            "address":       "Address",
            "parish":        "Parish",
            "type":          "Type",
            "price_sold":    "Sale Price ($)",
            "sale_date":     "Date",
            "sq_ft":         "Sq. Ft.",
            "beds":          "Beds",
            "baths":         "Baths",
            "lot_size":      "Lot Size",
            "lot_size_acres":"Lot (ac)",
            "units":         "Units",
            "arv":           "ARV ($)",
            "assessment":    "Assessment",
            "guest":         "Guest",
            "pool":          "Pool",
            "waterfront":    "Waterfront",
            "listed":        "Listed",
            "zone":          "Zone",
            "notes":         "Notes",
            "country":       "Country",
        }
        show_df.rename(columns=rename, inplace=True)

        st.dataframe(
            show_df,
            use_container_width=True,
            height=520,
            column_config={
                "Sale Price ($)": st.column_config.NumberColumn(format="$%d"),
                "ARV ($)":        st.column_config.NumberColumn(format="$%d"),
                "Assessment":     st.column_config.NumberColumn(format="$%d"),
                "Lot (ac)":       st.column_config.NumberColumn(format="%.3f"),
            },
        )
        st.caption(f"Showing {len(df):,} record(s)")

# ────────────────────────────────────────────────────────── Charts ────────────
with tab_chart:
    if df.empty:
        st.info("No data to chart.")
    else:
        # Try to import plotly; fall back to st native charts
        try:
            import plotly.express as px

            c1, c2 = st.columns(2)

            # Price distribution
            price_df = df["price_sold"].dropna()
            if not price_df.empty:
                with c1:
                    st.subheader("Sale Price Distribution")
                    fig = px.histogram(price_df, nbins=30, labels={"value": "Price ($)"},
                                       color_discrete_sequence=["#1F3864"])
                    fig.update_layout(showlegend=False, margin=dict(t=20))
                    st.plotly_chart(fig, use_container_width=True)

            # Count by Parish
            parish_counts = df["parish"].value_counts().reset_index()
            parish_counts.columns = ["Parish", "Count"]
            with c2:
                st.subheader("Records by Parish")
                fig2 = px.bar(parish_counts, x="Parish", y="Count",
                              color="Parish",
                              color_discrete_sequence=px.colors.qualitative.Set2)
                fig2.update_layout(showlegend=False, margin=dict(t=20),
                                   xaxis_tickangle=-40)
                st.plotly_chart(fig2, use_container_width=True)

            c3, c4 = st.columns(2)

            # Count by Type
            type_counts = df["type"].value_counts().reset_index()
            type_counts.columns = ["Type", "Count"]
            with c3:
                st.subheader("Records by Property Type")
                fig3 = px.pie(type_counts, names="Type", values="Count",
                              hole=0.4)
                fig3.update_layout(margin=dict(t=20))
                st.plotly_chart(fig3, use_container_width=True)

            # Average price over time (by year)
            yr_df = df.dropna(subset=["price_sold", "sale_date"]).copy()
            yr_df["Year"] = pd.to_datetime(yr_df["sale_date"]).dt.year
            avg_yr = yr_df.groupby("Year")["price_sold"].median().reset_index()
            avg_yr.columns = ["Year", "Median Price"]
            if len(avg_yr) > 1:
                with c4:
                    st.subheader("Median Sale Price by Year")
                    fig4 = px.line(avg_yr, x="Year", y="Median Price",
                                   markers=True,
                                   color_discrete_sequence=["#1F3864"])
                    fig4.update_layout(margin=dict(t=20))
                    st.plotly_chart(fig4, use_container_width=True)

            # Price vs Sq Ft scatter
            scatter_df = df.dropna(subset=["price_sold", "sq_ft"])
            if not scatter_df.empty:
                st.subheader("Sale Price vs. Sq. Ft.")
                fig5 = px.scatter(
                    scatter_df, x="sq_ft", y="price_sold",
                    color="type" if "type" in scatter_df.columns else None,
                    hover_data=["property_name", "parish", "sale_date"],
                    labels={"sq_ft": "Sq. Ft.", "price_sold": "Sale Price ($)"},
                    opacity=0.7,
                )
                fig5.update_layout(margin=dict(t=20))
                st.plotly_chart(fig5, use_container_width=True)

        except ImportError:
            # Fallback – native Streamlit charts
            st.warning("Install plotly for richer charts:  pip install plotly")
            by_parish = df["parish"].value_counts()
            st.bar_chart(by_parish)
            price_data = df.set_index("sale_date")["price_sold"].dropna()
            st.line_chart(price_data)

# ────────────────────────────────────────────────────────── Export ────────────
with tab_export:
    st.subheader("Export Results")

    if df.empty:
        st.info("Run a search first.")
    else:
        st.write(f"**{len(df):,} records** ready for export.")

        col_csv, col_xlsx = st.columns(2)

        with col_csv:
            st.download_button(
                label="⬇️ Download CSV",
                data=to_csv(df),
                file_name=f"comparables_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col_xlsx:
            xlsx_bytes = to_excel(df, stats)
            st.download_button(
                label="⬇️ Download Excel Report",
                data=xlsx_bytes,
                file_name=f"comparables_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        st.divider()
        st.subheader("📑 Summary Statistics")

        stat_table = {
            "Metric": [
                "Total Records Shown",
                "Records with Sale Price",
                "Minimum Sale Price",
                "Maximum Sale Price",
                "Average Sale Price",
                "Median Sale Price",
                "Average Sq. Ft.",
                "Avg Price per Sq. Ft.",
            ],
            "Value": [
                f"{stats['count']:,}",
                f"{stats['with_price']:,}",
                fmt_currency(stats["min_price"])  if stats["min_price"]  else "—",
                fmt_currency(stats["max_price"])  if stats["max_price"]  else "—",
                fmt_currency(stats["avg_price"])  if stats["avg_price"]  else "—",
                fmt_currency(stats["med_price"])  if stats["med_price"]  else "—",
                f"{stats['avg_sqft']:,.0f}" if stats["avg_sqft"] else "—",
                fmt_currency(stats["price_per_sqft"]) if stats["price_per_sqft"] else "—",
            ],
        }
        st.table(pd.DataFrame(stat_table))

        # Breakdown tables
        r1, r2 = st.columns(2)
        with r1:
            st.markdown("**By Parish**")
            p = df["parish"].value_counts().rename_axis("Parish").reset_index(name="Count")
            st.dataframe(p, use_container_width=True, hide_index=True)
        with r2:
            st.markdown("**By Property Type**")
            t = df["type"].value_counts().rename_axis("Type").reset_index(name="Count")
            st.dataframe(t, use_container_width=True, hide_index=True)
