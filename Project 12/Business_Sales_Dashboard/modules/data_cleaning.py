"""Assignment 2 - Data Cleaning and validation.

Every change is recorded in report["steps"] so the dashboard can show
exactly what was changed or removed, and why.
"""
import pandas as pd

REQUIRED = ["Order_ID", "Order_Date", "Customer_ID", "Customer_Name",
            "Product", "Quantity", "Unit_Price"]
OPTIONAL = ["Category", "Unit_Cost", "Region"]
ALL_COLUMNS = REQUIRED + OPTIONAL


def standardize_columns(df):
    """'order date ' / 'ORDER_DATE' -> 'Order_Date' (only for known columns)."""
    lookup = {c.lower(): c for c in ALL_COLUMNS}
    rename = {}
    for col in df.columns:
        key = str(col).strip().replace(" ", "_").lower()
        if key in lookup:
            rename[col] = lookup[key]
    return df.rename(columns=rename)


def clean_data(raw):
    """Validate + clean. Returns (clean_df, report). Raises ValueError if unusable."""
    df = standardize_columns(raw.copy())
    steps = []

    def log(step, count, action):
        steps.append({"Step": step, "Rows affected": int(count), "What was done": action})

    # 1. required columns
    missing_cols = [c for c in REQUIRED if c not in df.columns]
    if missing_cols:
        raise ValueError(
            "Missing required column(s): " + ", ".join(missing_cols)
            + ". Required columns are: " + ", ".join(REQUIRED) + "."
            + " Columns found in your file: " + ", ".join(str(c) for c in list(raw.columns)[:10])
            + ". Check that you uploaded the sales data file and that the column names are in the first row."
        )
    df = df[[c for c in ALL_COLUMNS if c in df.columns]].copy()
    meta = {
        "has_category": "Category" in df.columns,
        "has_region": "Region" in df.columns,
        "has_cost": "Unit_Cost" in df.columns,
    }
    rows_in = len(df)

    # 2. tidy text, blanks -> missing
    for col in df.columns:
        if df[col].dtype == object or str(df[col].dtype) == "string":
            df[col] = df[col].astype(object).map(
                lambda v: v.strip() if isinstance(v, str) else v
            ).replace("", None)

    missing_before = df.isna().sum()
    missing_before = missing_before[missing_before > 0].reset_index()
    missing_before.columns = ["Column", "Missing values"]

    # 3. exact duplicate rows
    dup = int(df.duplicated().sum())
    df = df.drop_duplicates()
    log("Duplicate rows", dup, "Removed exact duplicate rows (kept the first copy).")

    # 4. dates
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")
    bad = df["Order_Date"].isna()
    log("Invalid or missing dates", bad.sum(), "Removed rows - an order without a valid date cannot be placed on a timeline.")
    df = df[~bad].copy()

    # 5. numeric columns
    for col in ["Quantity", "Unit_Price"] + (["Unit_Cost"] if meta["has_cost"] else []):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    bad = df["Quantity"].isna() | (df["Quantity"] <= 0) | (df["Quantity"] % 1 != 0)
    log("Invalid quantity", bad.sum(), "Removed rows - Quantity must be a positive whole number.")
    df = df[~bad].copy()

    bad = df["Unit_Price"].isna() | (df["Unit_Price"] < 0)
    log("Invalid unit price", bad.sum(), "Removed rows - Unit_Price must be a number that is not negative.")
    df = df[~bad].copy()

    # 6. required identifiers
    bad = df["Order_ID"].isna() | df["Customer_ID"].isna() | df["Product"].isna()
    log("Missing Order_ID / Customer_ID / Product", bad.sum(), "Removed rows - these fields cannot be guessed.")
    df = df[~bad].copy()

    # 7. fill descriptive labels (labels only, never numbers)
    miss_name = df["Customer_Name"].isna()
    df.loc[miss_name, "Customer_Name"] = df.loc[miss_name, "Customer_ID"]
    log("Missing Customer_Name", miss_name.sum(), "Used Customer_ID as the display name.")

    if meta["has_category"]:
        miss = df["Category"].isna()
        df.loc[miss, "Category"] = "Uncategorized"
        log("Missing Category", miss.sum(), "Labelled as 'Uncategorized'.")
    if meta["has_region"]:
        miss = df["Region"].isna()
        df.loc[miss, "Region"] = "Unknown"
        log("Missing Region", miss.sum(), "Labelled as 'Unknown'.")

    # 8. cost - NEVER invent a missing cost
    if meta["has_cost"]:
        neg = df["Unit_Cost"] < 0
        df.loc[neg, "Unit_Cost"] = float("nan")
        log("Negative Unit_Cost", neg.sum(), "Set to missing (not guessed).")
        log("Missing Unit_Cost", df["Unit_Cost"].isna().sum(),
            "Rows kept for revenue analysis; profit for these rows is shown as unavailable.")
        if df["Unit_Cost"].notna().sum() == 0:
            meta["has_cost"] = False
    else:
        df["Unit_Cost"] = float("nan")
        log("Unit_Cost column not provided", 0, "Profit metrics are marked unavailable; only revenue analysis is shown.")

    df = df.reset_index(drop=True)
    if df.empty:
        raise ValueError("No valid rows are left after cleaning. Please check your file.")

    report = {
        "rows_in": rows_in,
        "rows_out": len(df),
        "missing_before": missing_before,
        "steps": pd.DataFrame(steps),
        "meta": meta,
    }
    return df, report
