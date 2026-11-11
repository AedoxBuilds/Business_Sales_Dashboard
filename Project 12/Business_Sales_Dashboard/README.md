# 📊 Business Sales Analytics Dashboard

An interactive Streamlit app that turns CSV / Excel sales records into clear business insights:
revenue and profit trends, product performance and customer purchasing analysis.

> AndroMind Institute - Project 01. Built with Python, Pandas, NumPy, Plotly and Streamlit.

## Features
- Upload **.csv** or **.xlsx** files (clear error messages for unsupported / unreadable / empty files)
- Validation + documented cleaning (duplicates, bad dates, bad quantities, missing values)
- KPI cards: total revenue, total profit, orders, average order value
- 5 pages: Sales Overview, Product Performance, Monthly Analysis, Customer Analytics, Data Explorer
- Filters: date range, product, category, region (category/region only if those columns exist)
- **Key insights** box on the overview page (best/weakest month, top product and city, lowest margin, customer concentration)
- **Best product in each city** + cross-city recommendations, with a pop-up (toast) when one city is selected
- **Inactive customers** win-back list with an adjustable number of days
- Downloads: filtered data (CSV) and multi-sheet summary report (Excel)
- Profit is **never guessed**: without `Unit_Cost` the app shows revenue analysis and marks profit "N/A"

## Setup
```bash
git clone <your-repo-url>
cd Business_Sales_Dashboard
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python data/generate_sample_data.py   # optional: re-creates the sample CSV
streamlit run app.py
```

## Project structure
```
Business_Sales_Dashboard/
├── app.py                      # Streamlit interface (5 pages, filters, downloads)
├── requirements.txt
├── data/
│   ├── sample_sales.csv        # synthetic demo data (PKR, Jan-Jun 2026)
│   ├── uae_sales_data.xlsx     # synthetic UAE data (AED, Jan-Oct 2026) - upload to test
│   ├── test_sales_random.xlsx  # data with deliberate errors - tests the cleaning report
│   └── generate_sample_data.py # creates the sample file
├── modules/
│   ├── data_loader.py          # Assignment 1 - load CSV/Excel, overview
│   ├── data_cleaning.py        # Assignment 2 - validation + cleaning report
│   ├── sales_analysis.py       # Assignment 3 & 5 - metrics, grouping, customers, Excel export
│   └── visualizations.py       # Assignment 4 - Plotly charts
├── screenshots/                # add your screenshots here
└── README.md
```

## Required data format (one row = one order line)
| Column | Required | Notes |
|---|---|---|
| Order_ID, Order_Date, Customer_ID, Customer_Name, Product, Quantity, Unit_Price | Yes | An order can have several rows |
| Category, Unit_Cost, Region | Optional | Related pages/metrics appear only when present |

Formulas: Revenue = Quantity × Unit_Price · Cost = Quantity × Unit_Cost · Profit = Revenue − Cost ·
Margin % = Profit ÷ Revenue × 100 (revenue ≠ 0) · Average order value = Total revenue ÷ **unique** orders.

## Cleaning rules
| Problem | Action |
|---|---|
| Exact duplicate rows | Removed (first kept) |
| Invalid / missing date | Row removed |
| Quantity missing, ≤ 0 or not a whole number | Row removed |
| Unit_Price missing or negative | Row removed |
| Missing Order_ID / Customer_ID / Product | Row removed |
| Missing Customer_Name / Category / Region | Labelled (Customer_ID / "Uncategorized" / "Unknown") |
| Missing or negative Unit_Cost | Kept as missing - profit for that row is "unavailable" |

The Data Explorer page shows exactly how many rows each rule changed.

## Sample data notes
`sample_sales.csv` is fully **synthetic** (no real customers). Currency: PKR. Range: 2026-01-01 to 2026-06-30.
It intentionally contains a few bad rows (4 duplicates, 1 invalid date, 1 zero quantity, 1 missing name)
so the cleaning report has something to show: 651 rows in → 645 after cleaning.

## Assumptions and limitations
- One currency and one date format per file.
- A month counts as "Full" if the data covers it except for ~3 edge days; partial months are flagged and excluded from the fair comparison.
- Customer groups compare each customer with the median customer of the current selection.

## Screenshots
_Add screenshots of each page to `screenshots/` and link them here._

## Freelance service description
**I will build a Python sales analytics dashboard using Streamlit, Pandas and Plotly.**
Upload your CSV or Excel sales file and get an interactive dashboard showing your best-selling products,
profitable months, valuable customers and regional performance - with cleaned data, working filters and
downloadable reports. Delivery: working app, reusable source code, sample dataset, GitHub repository,
screenshots and a short demo video.
