"""Assignment 3 + 5 - Sales calculations, grouping and customer analysis."""
from io import BytesIO
import numpy as np
import pandas as pd

COVERAGE_TOLERANCE_DAYS = 3  # a month counts as complete if data covers all but a few edge days


def add_metrics(df):
    """Revenue = Qty x Price | Cost = Qty x Unit_Cost | Profit = Revenue - Cost."""
    df = df.copy()
    df["Revenue"] = df["Quantity"] * df["Unit_Price"]
    df["Cost"] = df["Quantity"] * df["Unit_Cost"]          # NaN when cost unknown
    df["Profit"] = df["Revenue"] - df["Cost"]              # NaN when cost unknown
    df["Profit_Margin_%"] = df["Profit"] / df["Revenue"].replace(0, np.nan) * 100
    return df


def kpis(df):
    """Headline numbers. Orders are counted with nunique - one order has many rows."""
    revenue = df["Revenue"].sum()
    orders = df["Order_ID"].nunique()
    known = df[df["Profit"].notna()]
    profit = known["Profit"].sum() if len(known) else None
    known_rev = known["Revenue"].sum()
    margin = (profit / known_rev * 100) if (profit is not None and known_rev != 0) else None
    return {
        "revenue": revenue,
        "profit": profit,
        "margin": margin,
        "orders": orders,
        "aov": revenue / orders if orders else 0,
        "units": df["Quantity"].sum(),
        "customers": df["Customer_ID"].nunique(),
        "rows_missing_cost": int(df["Profit"].isna().sum()),
    }


def summarize(df, by):
    """Units, revenue, profit, orders and margin grouped by one column."""
    tmp = df.assign(_rev_known=df["Revenue"].where(df["Profit"].notna(), 0.0))
    out = tmp.groupby(by).agg(
        Units=("Quantity", "sum"),
        Revenue=("Revenue", "sum"),
        Profit=("Profit", lambda s: s.sum(min_count=1)),
        Orders=("Order_ID", "nunique"),
        _rev_known=("_rev_known", "sum"),
    ).reset_index()
    out["Profit_Margin_%"] = out["Profit"] / out["_rev_known"].replace(0, np.nan) * 100
    return out.drop(columns="_rev_known")


def monthly_summary(df):
    """Monthly totals + month-over-month change + coverage flag (full vs partial month)."""
    tmp = df.assign(Month=df["Order_Date"].dt.to_period("M").dt.to_timestamp())
    m = summarize(tmp, "Month").sort_values("Month").reset_index(drop=True)
    first, last = df["Order_Date"].min(), df["Order_Date"].max()
    tol = pd.Timedelta(days=COVERAGE_TOLERANCE_DAYS)
    month_end = m["Month"] + pd.offsets.MonthEnd(0)
    full = (first <= m["Month"] + tol) & (last >= month_end - tol)
    m["Coverage"] = np.where(full, "Full month", "Partial month")
    m["Revenue_MoM_%"] = m["Revenue"].pct_change() * 100
    m["Month_Label"] = m["Month"].dt.strftime("%b %Y")
    return m


def customer_summary(df):
    """Spend vs. order frequency per customer, plus simple behaviour segments."""
    c = df.groupby("Customer_ID").agg(
        Customer_Name=("Customer_Name", "first"),
        Orders=("Order_ID", "nunique"),
        Units=("Quantity", "sum"),
        Spend=("Revenue", "sum"),
        Profit=("Profit", lambda s: s.sum(min_count=1)),
        Last_Order=("Order_Date", "max"),
    ).reset_index()
    c["Avg_Order_Value"] = c["Spend"] / c["Orders"]
    if len(c) >= 8:   # need enough customers for grouping to mean anything
        hi_spend = c["Spend"] >= c["Spend"].median()
        hi_freq = c["Orders"] >= c["Orders"].median()
        c["Segment"] = np.select(
            [hi_spend & hi_freq, hi_spend & ~hi_freq, ~hi_spend & hi_freq],
            ["Loyal big spenders", "Big spenders, less frequent", "Frequent, smaller baskets"],
            default="Occasional, lower spend",
        )
    else:
        c["Segment"] = "Not enough customers to group"
    return c


def build_summary_excel(df, currency, meta):
    """Multi-sheet Excel summary report as bytes (for the download button)."""
    k = kpis(df)
    overview = pd.DataFrame({
        "Metric": ["Currency", "Date range", "Total revenue", "Total profit", "Profit margin %",
                   "Orders", "Customers", "Average order value", "Rows without unit cost"],
        "Value": [currency,
                  f"{df['Order_Date'].min():%Y-%m-%d} to {df['Order_Date'].max():%Y-%m-%d}",
                  round(k["revenue"], 2),
                  "Unavailable" if k["profit"] is None else round(k["profit"], 2),
                  "Unavailable" if k["margin"] is None else round(k["margin"], 2),
                  k["orders"], k["customers"], round(k["aov"], 2), k["rows_missing_cost"]],
    })
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        overview.to_excel(writer, sheet_name="Overview", index=False)
        summarize(df, "Product").sort_values("Revenue", ascending=False).to_excel(writer, sheet_name="Products", index=False)
        monthly_summary(df).drop(columns="Month").to_excel(writer, sheet_name="Monthly", index=False)
        customer_summary(df).sort_values("Spend", ascending=False).to_excel(writer, sheet_name="Customers", index=False)
        if meta["has_category"]:
            summarize(df, "Category").to_excel(writer, sheet_name="Categories", index=False)
        if meta["has_region"]:
            summarize(df, "Region").to_excel(writer, sheet_name="Regions", index=False)
    return buffer.getvalue()


# ---------------------------------------------------------------- v2 additions
MIN_ORDERS_FOR_COMPARISON = 5   # ignore cities with fewer orders when looking for "weak" cities


def region_recommendations(df):
    """Best-selling product (by revenue) in every region + where it under-performs.

    Shares are compared as % of each region's own revenue, so big cities do not
    automatically win. Cities with very few orders are not used as 'weak' cities.
    """
    region_total = df.groupby("Region")["Revenue"].sum()
    region_orders = df.groupby("Region")["Order_ID"].nunique()
    pv = df.pivot_table(index="Region", columns="Product", values="Revenue", aggfunc="sum", fill_value=0)
    shares = pv.div(region_total, axis=0) * 100
    rows = []
    for region in pv.index:
        product = pv.loc[region].idxmax()
        own = shares.loc[region, product]
        others = shares[product].drop(region)
        others = others[region_orders.reindex(others.index) >= MIN_ORDERS_FOR_COMPARISON]
        weakest, weak_share, rec = None, None, "No clear gap in other cities."
        if len(others):
            weakest, weak_share = others.idxmin(), others.min()
            if weak_share < own * 0.5:
                gap = "has no sales" if weak_share < 0.5 else f"is only {weak_share:.0f}% of revenue"
                rec = (f"{product} leads in {region} ({own:.0f}% of its revenue) but {gap} "
                       f"in {weakest} - consider promoting it there.")
        rows.append({"Region": region, "Top_Product": product, "Revenue": pv.loc[region, product],
                     "Share_of_Region_%": own, "Weakest_Region": weakest, "Weak_Region_Share_%": weak_share,
                     "Recommendation": rec})
    return pd.DataFrame(rows).sort_values("Revenue", ascending=False).reset_index(drop=True)


def inactive_customers(df, days):
    """Customers whose last order is at least `days` before the latest order in the data."""
    ref = df["Order_Date"].max()
    c = customer_summary(df)
    c["Days_Since_Last_Order"] = (ref - c["Last_Order"]).dt.days
    out = c[c["Days_Since_Last_Order"] >= days].sort_values("Spend", ascending=False)
    return out[["Customer_ID", "Customer_Name", "Orders", "Spend", "Last_Order", "Days_Since_Last_Order"]], ref


def auto_insights(df, meta, has_profit, currency):
    """Plain-English findings for the selected data."""
    k = kpis(df)
    out = []
    m = monthly_summary(df)
    if len(m) > 1:
        best = m.loc[m["Revenue"].idxmax()]
        worst = m.loc[m["Revenue"].idxmin()]
        out.append(f"**Best month:** {best['Month_Label']} ({currency} {best['Revenue']:,.0f}); "
                   f"weakest month: {worst['Month_Label']} ({currency} {worst['Revenue']:,.0f}).")
        full = m[m["Coverage"] == "Full month"]
        if len(full) >= 2 and full.iloc[-2]["Revenue"]:
            a, b = full.iloc[-2], full.iloc[-1]
            out.append(f"**Latest trend:** revenue in {b['Month_Label']} is "
                       f"{(b['Revenue'] / a['Revenue'] - 1) * 100:+.1f}% vs {a['Month_Label']}.")
    prod = summarize(df, "Product")
    top = prod.loc[prod["Revenue"].idxmax()]
    out.append(f"**Top product:** {top['Product']} brings {top['Revenue'] / k['revenue'] * 100:.0f}% of revenue.")
    if meta["has_region"]:
        reg = df.groupby("Region")["Revenue"].sum()
        if len(reg) > 1:
            out.append(f"**Top city/region:** {reg.idxmax()} generates {reg.max() / k['revenue'] * 100:.0f}% of revenue.")
    if has_profit:
        big = prod[(prod["Revenue"] >= k["revenue"] * 0.02) & prod["Profit_Margin_%"].notna()]
        if len(big):
            low = big.loc[big["Profit_Margin_%"].idxmin()]
            out.append(f"**Lowest margin (products with 2%+ of revenue):** {low['Product']} at "
                       f"{low['Profit_Margin_%']:.0f}% vs {k['margin']:.0f}% overall - review its price or cost.")
    cust = df.groupby("Customer_ID")["Revenue"].sum().sort_values(ascending=False)
    if len(cust) >= 10:
        out.append(f"**Customer concentration:** your top 5 customers make {cust.head(5).sum() / k['revenue'] * 100:.0f}% of revenue.")
    return out
