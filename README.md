# Real Estate Comparables – Database & Search Tool

A local web application that turns your Excel comparables spreadsheet into a
searchable, filterable, exportable database — purpose-built for real estate
appraisers.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Quick-Start (First-Time Setup)](#quick-start)
3. [Launching the App](#launching-the-app)
4. [Using the Search Interface](#using-the-search-interface)
   - [Location filters](#location-filters)
   - [Property filters](#property-filters)
   - [Price & Date filters](#price--date-filters)
   - [Size filters](#size-filters)
5. [Charts & Analytics tab](#charts--analytics)
6. [Exporting Results](#exporting-results)
7. [Updating the Data](#updating-the-data)
8. [Database Reference](#database-reference)
9. [Troubleshooting](#troubleshooting)

---

## Project Structure

```
comparable/
├── FINAL COMPARABLE SPREADSHEET 2026.xlsm   ← your raw data (keep here)
├── build_db.py          ← one-time ETL: Excel → SQLite
├── app.py               ← the Streamlit web application
├── requirements.txt     ← Python package list
├── README.md            ← this file
└── comparables.db       ← generated database (auto-created on first run)
```

---

## Quick-Start

### 1 · Install Python (if not already installed)

- Download Python 3.11+ from https://www.python.org/downloads/
- Verify: open a terminal and type `python3 --version`

### 2 · Install dependencies

Open a terminal, navigate to the project folder, and run:

```bash
cd /path/to/comparable
python3 -m pip install -r requirements.txt
```

### 3 · Build the database

```bash
python3 build_db.py
```

This reads the `.xlsm` file and creates `comparables.db`.  
You will see output like:

```
Loading: FINAL COMPARABLE SPREADSHEET 2026.xlsm
Rows to process: 1530
Done: 1499 records inserted, 31 blank rows skipped.
Database saved to: comparables.db
```

---

## Launching the App

```bash
python3 -m streamlit run app.py
```

Your browser will open automatically at **http://localhost:8501**.

> **Tip:** If it does not open automatically, copy the URL from the terminal
> into your browser.

To stop the app, press `Ctrl+C` in the terminal.

---

## Using the Search Interface

All filters are in the **left-hand sidebar**.  
Results update automatically as you adjust filters (no need to press Search).
Pressing **Search** also triggers a refresh.

### Location Filters

| Filter | Description |
|---|---|
| **Parish / Region** | Multi-select. Leave blank = all parishes. Includes normalised names (e.g. "Smiths" and "Smith's" merged). |
| **Country** | Currently all records are Bermuda. Useful when multi-country data is added. |

### Property Filters

| Filter | Description |
|---|---|
| **Property Type** | Multi-select. Normalised types: House, Condominium, Apartment, House/Apartment, Land, Commercial, Fractional, Hotel Condo, etc. |
| **Zone Code** | Multi-select. Zoning codes from the assessment data (e.g. 110, 130, 150…). |
| **Guest Apt** | Yes / No / All. Whether the property has a guest apartment. |
| **Pool** | Yes / No / All. |
| **Waterfront** | Yes / No / All. |
| **Listed** | Yes / No / All. Whether the property was MLS listed. |
| **Beds / Baths / Units** | Numeric range inputs. |

### Price & Date Filters

| Filter | Description |
|---|---|
| **Sale Price Range** | Slider in USD. Drag both handles to narrow the range. |
| **Sale Date – From/To** | Calendar date pickers for the closed-sale date range. |

### Size Filters

| Filter | Description |
|---|---|
| **Sq. Ft. Range** | Interior area slider. |
| **Lot Size (acres)** | Numeric lot sizes parsed from the raw data (Ha and Acres converted). |

### Free-text Search

Type any part of a **property name** or **address** in the top search box to
narrow results across all other active filters.

### Reset Filters

Click **↺ Reset Filters** to clear everything and return to the full dataset.

---

## Charts & Analytics

The **📊 Charts & Analytics** tab renders automatically for the current search
results:

- **Sale Price Distribution** – histogram of all sold prices
- **Records by Parish** – bar chart
- **Records by Property Type** – donut chart
- **Median Sale Price by Year** – trend line
- **Sale Price vs. Sq. Ft.** – scatter plot coloured by type

> Charts require the `plotly` package (included in requirements.txt).

---

## Exporting Results

Switch to the **⬇️ Export / Report** tab.

### CSV Download
Plain comma-separated values – opens in any version of Excel, Google Sheets, or
Numbers.

### Excel Report (.xlsx)
A formatted two-sheet workbook:

| Sheet | Contents |
|---|---|
| **Comparables** | Full filtered dataset, frozen header row, currency formatting |
| **Summary** | 8 KPI stats + records-by-parish table + records-by-type table |

File names include a timestamp, e.g. `comparables_report_20260301_1430.xlsx`.

---

## Updating the Data

Whenever you add new sales to the spreadsheet:

1. Save the updated `.xlsm` file in the same folder.
2. Run `python3 build_db.py` – this **rebuilds the entire database** from
   scratch, so all normalisations and deduplication are reapplied.
3. Restart (or simply reload) the Streamlit app.

> Records with no Parish, no Sale Price, and no Property Name are automatically
> skipped as blank rows.

---

## Database Reference

The SQLite database (`comparables.db`) contains one table: **`comparables`**.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | Auto-increment PK |
| `property_name` | TEXT | As entered |
| `address` | TEXT | Street address |
| `parish` | TEXT | Original value from spreadsheet |
| `parish_normalized` | TEXT | Cleaned / merged parish name |
| `price_sold` | REAL | Sale price USD |
| `sale_date` | TEXT | ISO format `YYYY-MM-DD` |
| `sale_year` | INTEGER | Extracted year |
| `sale_month` | INTEGER | Extracted month (1-12) |
| `sq_ft` | REAL | Interior area |
| `beds` | INTEGER | Bedrooms |
| `baths` | REAL | Bathrooms |
| `lot_size_raw` | TEXT | Original lot size string |
| `lot_size_acres` | REAL | Parsed numeric value in acres |
| `no_units` | INTEGER | Number of units |
| `arv` | REAL | Annual Rental Value |
| `assessment` | REAL | Government assessment |
| `property_type` | TEXT | Original type string |
| `property_type_normalized` | TEXT | Cleaned property type |
| `guest` | TEXT | `Y` / `N` / NULL |
| `pool` | TEXT | `Y` / `N` / NULL |
| `waterfront` | TEXT | `Y` / `N` / NULL |
| `listed` | TEXT | `Y` / `N` / NULL |
| `zone` | TEXT | Zoning code |
| `notes` | TEXT | Free-form notes |
| `country` | TEXT | Default `Bermuda` |

You can also query the database directly with any SQLite client (e.g. DB
Browser for SQLite – https://sqlitebrowser.org/) for advanced queries.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError` | Run `python3 -m pip install -r requirements.txt` |
| `FileNotFoundError: Excel file not found` | Make sure the `.xlsm` file is in the same folder |
| App shows "Database not found" | Run `python3 build_db.py` first |
| Charts are missing | Run `python3 -m pip install plotly` |
| Port 8501 already in use | Run `python3 -m streamlit run app.py --server.port 8502` |
| Slow first load | Normal – Streamlit caches data after the first query |

---

## Support & Customisation

Common enhancements:
- **Add a Country column** to the spreadsheet to track overseas comparables.
- **Multi-user cloud deployment** – the app can be deployed to Streamlit Cloud
  (streamlit.io) or any Python web server.
- **Automatic refresh** – schedule `build_db.py` via cron to pick up changes
  nightly.
- **Photo attachments** – add an `image_url` column to the database and render
  thumbnails in the results table.

---

*Built March 2026 · Streamlit + SQLite + Python 3.11+*
