# Real Estate Comparables – Database & Search Tool

A cloud-hosted web application for searching, filtering, and reporting on real
estate comparable sales. Built for the Bermuda real estate appraisal market.

> **Live app:** deployed on Streamlit Community Cloud  
> **Data:** stored in a private GitHub repository, persistent across restarts

---

## Table of Contents

1. [What Was Delivered](#what-was-delivered)
2. [Architecture Overview](#architecture-overview)
3. [GitHub Repositories](#github-repositories)
4. [Using the Application](#using-the-application)
   - [Search & Filters](#search--filters)
   - [Charts & Analytics](#charts--analytics)
   - [Exporting Results](#exporting-results)
   - [Adding a New Record](#adding-a-new-record)
5. [Data Persistence](#data-persistence)
6. [Running Locally](#running-locally)
7. [Deployment Guide](#deployment-guide)
8. [Importing from Excel (optional)](#importing-from-excel)
9. [Database Reference](#database-reference)
10. [File Reference](#file-reference)
11. [Troubleshooting](#troubleshooting)

---

## What Was Delivered

| # | Deliverable | Status |
|---|---|---|
| 1 | Structured SQLite database (26-column schema, 6 indexes) | ✅ |
| 2 | Dynamic search interface with 15+ filter criteria | ✅ |
| 3 | Charts & analytics (price distribution, parish, type, trend, scatter) | ✅ |
| 4 | Export to CSV and formatted Excel report (.xlsx) | ✅ |
| 5 | Add Record form — enter new comparables directly in the browser | ✅ |
| 6 | Cloud deployment on Streamlit Community Cloud | ✅ |
| 7 | Persistent data storage via private GitHub repository | ✅ |
| 8 | Unit test suite (101 tests, 100% passing) | ✅ |
| 9 | Documentation & handover guide (this file) | ✅ |

---

## Architecture Overview

```
Browser (User)
     │
     ▼
Streamlit Community Cloud  ←──── GitHub: real-estate-comparables (app code)
     │                                    app.py
     │  on startup: fetch DB              comparables_utils.py
     │  after write: push DB              db_sync.py
     ▼
GitHub: real-estate-comparables-db  (comparables.db)
```

**On every cold start**, the app downloads `comparables.db` from the private
`real-estate-comparables-db` repository. After any record is added via the form,
the updated database is committed back to that repository automatically. This
means all data survives server restarts.

---

## GitHub Repositories

| Repository | Purpose | Visibility |
|---|---|---|
| `filipejrcorreia/real-estate-comparables` | Application source code | Private |
| `filipejrcorreia/real-estate-comparables-db` | SQLite database file | Private |

---

## Using the Application

### Search & Filters

All filters are in the **left sidebar**. Results update automatically.

| Filter | Description |
|---|---|
| **🔍 Search box** | Free-text match on property name or address |
| **Parish / Region** | Multi-select. Blank = all parishes |
| **Country** | All / Bermuda |
| **Property Type** | Multi-select. Types are normalised (e.g. typos merged) |
| **Zone Code** | Multi-select zoning codes |
| **Guest Apt / Pool / Waterfront / Listed** | Y / N / All toggles |
| **Sale Price Range** | USD slider |
| **Sale Date From / To** | Calendar date pickers |
| **Sq. Ft. Range** | Interior area slider |
| **Lot Size (acres)** | Numeric lot size slider |
| **Beds / Baths / Units** | Min/max number inputs |

Click **↺ Reset Filters** to return to the full dataset.

---

### Charts & Analytics

The **📊 Charts & Analytics** tab renders for the current filtered results:

- **Sale Price Distribution** – histogram
- **Records by Parish** – bar chart
- **Records by Property Type** – donut chart
- **Median Sale Price by Year** – trend line
- **Sale Price vs. Sq. Ft.** – scatter plot coloured by type

---

### Exporting Results

Switch to the **⬇️ Export / Report** tab.

**CSV Download** — plain `.csv`, works in Excel, Google Sheets, Numbers.

**Excel Report (.xlsx)** — formatted two-sheet workbook:

| Sheet | Contents |
|---|---|
| **Comparables** | Full filtered dataset, frozen header, currency formatting |
| **Summary** | 8 KPI stats + breakdown by parish + breakdown by type |

File names include a timestamp e.g. `comparables_report_20260301_1430.xlsx`.

---

### Adding a New Record

1. Click the **➕ Add Record** tab.
2. Fill in the form fields (only **Property Name** is required).
3. For Parish and Property Type, choose from the existing dropdown or select
   **➕ Other…** and type a custom value.
4. Click **💾 Save Record**.

The record is written to the database and immediately synced to GitHub. It will
appear in search results straight away.

---

## Data Persistence

The database lives in:
**`https://github.com/filipejrcorreia/real-estate-comparables-db`** (private)

- Every `git commit` to that repo is a snapshot of the full database.
- The GitHub commit history gives you a complete audit trail of all changes.
- To restore to a previous state, checkout an older commit of `comparables.db`
  from that repository.

The sync is driven by the `[github]` block in Streamlit secrets (set in the
Streamlit Cloud dashboard → App settings → Secrets):

```toml
[github]
token     = "ghp_xxxxxxxxxxxxxxxxxxxx"
db_owner  = "filipejrcorreia"
db_repo   = "real-estate-comparables-db"
db_branch = "main"
db_path   = "comparables.db"
```

> The token must have **`repo`** scope (full control of private repositories).
> Create/rotate tokens at https://github.com/settings/tokens

---

## Running Locally

### Requirements

- Python 3.11+
- Git

### Setup

```bash
# 1. Clone the app repo
git clone https://github.com/filipejrcorreia/real-estate-comparables.git
cd real-estate-comparables

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create local secrets file
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml and add your GitHub token

# 4. Run the app
python3 -m streamlit run app.py
```

Browser opens at **http://localhost:8501**.

> On first run the app fetches `comparables.db` from GitHub automatically.
> To stop the app press `Ctrl+C`.

---

## Deployment Guide

### Streamlit Community Cloud (current hosting)

1. Go to https://share.streamlit.io
2. **New app** → connect `filipejrcorreia/real-estate-comparables` / branch `main` / file `app.py`
3. **Advanced settings → Secrets** → paste the `[github]` block shown above
4. Click **Deploy**

### Re-deploying / Updating

Push any change to the `main` branch of `real-estate-comparables` — Streamlit
Cloud re-deploys automatically within ~1 minute.

### Transferring Ownership

To hand the app to another GitHub account:

1. Transfer both repos in GitHub → Settings → Transfer ownership.
2. Update `db_owner` in the Streamlit secrets to the new owner's username.
3. In `db_sync.py` update the `db_owner` default fallback (line ~25) to match.

---

## Importing from Excel

If you have an existing spreadsheet of comparables to bulk-import:

```bash
# The script accepts any .xlsx or .xlsm file as an argument
python3 build_db.py path/to/your_spreadsheet.xlsm

# Optionally write to a different database file
python3 build_db.py --db new.db path/to/your_spreadsheet.xlsm
```

**Expected spreadsheet format (Sheet1):**

| Column | Name | Notes |
|---|---|---|
| A | Property Name | |
| B | Address | |
| C | Parish | Auto-normalised |
| D | Price Sold | Numeric |
| E | Date | Excel date or text |
| F | Sq. ft. | Numeric |
| G | Bed | |
| H | Bath | |
| I | Lot Size | Acres, Ha, or text |
| J | No. Units | |
| K | ARV | Annual Rental Value |
| L | Assessment | |
| M | Type | Auto-normalised |
| N | Guest | Y/N |
| O | Pool | Y/N |
| P | Waterfront | Y/N |
| Q | Listed | Y/N |
| R | Zone | |
| S | Notes | |

After import, push the new `comparables.db` to `real-estate-comparables-db`:

```bash
cd /tmp && git clone https://github.com/filipejrcorreia/real-estate-comparables-db.git
cp /path/to/comparables.db real-estate-comparables-db/
cd real-estate-comparables-db && git add comparables.db
git commit -m "Bulk import from spreadsheet" && git push
```

---

## Database Reference

Table: **`comparables`** — one row per sold property.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | Auto-increment primary key |
| `property_name` | TEXT | |
| `address` | TEXT | |
| `parish` | TEXT | Original value |
| `parish_normalized` | TEXT | Cleaned / merged name |
| `price_sold` | REAL | USD |
| `sale_date` | TEXT | `YYYY-MM-DD` |
| `sale_year` | INTEGER | |
| `sale_month` | INTEGER | 1–12 |
| `sq_ft` | REAL | Interior area |
| `beds` | INTEGER | |
| `baths` | REAL | |
| `lot_size_raw` | TEXT | Original string |
| `lot_size_acres` | REAL | Parsed numeric acres |
| `no_units` | INTEGER | |
| `arv` | REAL | Annual Rental Value |
| `assessment` | REAL | Government assessment |
| `property_type` | TEXT | Original type string |
| `property_type_normalized` | TEXT | Cleaned type |
| `guest` | TEXT | `Y` / `N` / NULL |
| `pool` | TEXT | `Y` / `N` / NULL |
| `waterfront` | TEXT | `Y` / `N` / NULL |
| `listed` | TEXT | `Y` / `N` / NULL |
| `zone` | TEXT | Zoning code |
| `notes` | TEXT | |
| `country` | TEXT | Default `Bermuda` |

**Direct DB access:** use [DB Browser for SQLite](https://sqlitebrowser.org/)
to run custom queries, bulk edits, or data corrections directly on `comparables.db`.

---

## File Reference

```
real-estate-comparables/
├── app.py                          Main Streamlit application
├── comparables_utils.py            Pure-Python logic (query, export, stats)
├── db_sync.py                      GitHub fetch/push for persistent storage
├── build_db.py                     Optional: bulk import from Excel/xlsm
├── requirements.txt                Python dependencies
├── .streamlit/
│   └── secrets.toml.example        Template for GitHub token configuration
├── tests/
│   ├── conftest.py                 Shared pytest fixtures
│   ├── test_app.py                 Tests for comparables_utils (53 tests)
│   └── test_build_db.py            Tests for build_db ETL (48 tests)
└── README.md                       This file
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| **App shows "No GitHub token found"** | Add the `[github]` block to Streamlit secrets |
| **Database not loading** | Check the token has `repo` scope and `db_owner`/`db_repo` are correct |
| **Record saved but disappeared after restart** | GitHub push failed — check secrets and token expiry |
| **`ModuleNotFoundError`** | Run `pip install -r requirements.txt` |
| **Port 8501 in use (local)** | Run `python3 -m streamlit run app.py --server.port 8502` |
| **Charts not showing** | Run `pip install plotly` |
| **Slow first load** | Normal — Streamlit fetches DB from GitHub on cold start (~3–5 s) |

---

## Running the Test Suite

```bash
python3 -m pytest tests/ -v
# Expected: 101 passed in ~1s
```

---

*Built March 2026 · Python 3.13 · Streamlit 1.54 · SQLite · GitHub API*


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
