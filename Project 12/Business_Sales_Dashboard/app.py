"""Business Sales Analytics Dashboard  -  run with:  streamlit run app.py"""
from io import BytesIO

import pandas as pd
import streamlit as st

from modules.data_loader import load_file, file_overview
from modules.data_cleaning import clean_data
from modules import sales_analysis as sa
from modules import visualizations as viz

st.set_page_config(page_title="Business Sales Analytics Dashboard", page_icon="📊", layout="wide")

SAMPLE_PATH = "data/sample_sales.csv"
PAGES = ["1. Sales Overview", "2. Product Performance", "3. Monthly Sales Analysis",
         "4. Customer Analytics", "5. Data Explorer"]


@st.cache_data(show_spinner="Reading and cleaning your file...")
def prepare_data(file_bytes, filename):
    raw = load_file(BytesIO(file_bytes), filename)
    clean, report = clean_data(raw)
    return raw, sa.add_metrics(clean), report


def money(value, currency):
    return f"{currency} {value:,.0f}"


# ----------------------------------------------------------------- sidebar: data
st.sidebar.title("📊 Sales Dashboard")
uploaded = st.sidebar.file_uploader("Upload sales file (CSV or Excel .xlsx)", type=["csv", "xlsx"])
use_sample = st.sidebar.checkbox("Use sample data", value=uploaded is None,
                                 help="Synthetic demo data (see README).")
currency = st.sidebar.text_input("Currency label", value="PKR")

if uploaded is not None and not use_sample:
    file_bytes, file_name = uploaded.getvalue(), uploaded.name
elif use_sample:
    with open(SAMPLE_PATH, "rb") as f:
        file_bytes, file_name = f.read(), "sample_sales.csv"
else:
    st.title("Business Sales Analytics Dashboard")
    st.info("Upload a CSV or Excel file in the sidebar, or tick **Use sample data**.")
    st.stop()

try:
    raw, data, report = prepare_data(file_bytes, file_name)
except ValueError as error:
    st.error(str(error))
    st.stop()

meta = report["meta"]
has_profit = meta["has_cost"]

# ----------------------------------------------------------------- sidebar: filters
st.sidebar.divider()
st.sidebar.subheader("Filters")
min_date, max_date = data["Order_Date"].min().date(), data["Order_Date"].max().date()
dates = st.sidebar.date_input("Order date", value=(min_date, max_date),
                              min_value=min_date, max_value=max_date)
if len(dates) != 2:
    st.info("Select both a start date and an end date.")
    st.stop()

mask = (data["Order_Date"].dt.date >= dates[0]) & (data["Order_Date"].dt.date <= dates[1])
selected, mask_no_region = {}, None
for column, present in [("Product", True), ("Category", meta["has_category"]), ("Region", meta["has_region"])]:
    if present:
        if column == "Region":
            mask_no_region = mask.copy()   # city comparisons must see ALL cities
        options = sorted(data[column].unique())
        chosen = st.sidebar.multiselect(column, options, default=options)
        selected[column] = chosen
        mask &= data[column].isin(chosen)

if mask_no_region is None:
    mask_no_region = mask
df = data[mask]
compare_df = data[mask_no_region]
st.sidebar.caption(f"{len(df):,} of {len(data):,} rows selected")
page = st.sidebar.radio("Go to", PAGES)

st.title(page[3:])
st.caption(f"File: {file_name}  |  Currency: {currency}  |  "
           f"Data range: {min_date:%d %b %Y} to {max_date:%d %b %Y}")
if df.empty:
    st.warning("No records match the current filters. Widen the filters in the sidebar.")
    st.stop()
if not has_profit:
    st.warning("No usable Unit_Cost values were provided, so profit metrics are unavailable. "
               "Revenue analysis is shown instead (costs are never guessed).")

k = sa.kpis(df)

# pop-up (toast): best product of the selected city, shown once per city selection
if meta["has_region"]:
    picked = selected.get("Region", [])
    if len(picked) == 1 and st.session_state.get("toast_region") != picked[0]:
        recs = sa.region_recommendations(compare_df)
        row = recs[recs["Region"] == picked[0]]
        if not row.empty:
            r = row.iloc[0]
            st.toast(f"**{picked[0]}:** best seller is **{r['Top_Product']}** "
                     f"({money(r['Revenue'], currency)}). {r['Recommendation']}", icon="💡", duration=10)
        st.session_state["toast_region"] = picked[0]
    elif len(picked) != 1:
        st.session_state["toast_region"] = None

# ----------------------------------------------------------------- page 1
if page == PAGES[0]:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total revenue", money(k["revenue"], currency))
    c2.metric("Total profit", money(k["profit"], currency) if k["profit"] is not None else "N/A",
              delta=f"{k['margin']:.1f}% margin" if k["margin"] is not None else None, delta_color="off")
    c3.metric("Orders", f"{k['orders']:,}")
    c4.metric("Average order value", money(k["aov"], currency))
    if has_profit and k["rows_missing_cost"]:
        st.caption(f"⚠️ Profit excludes {k['rows_missing_cost']} row(s) with no unit cost.")

    st.plotly_chart(viz.revenue_over_time(df, currency), width="stretch")

    top_product = df.groupby("Product")["Revenue"].sum().idxmax()
    top_share = df.groupby("Product")["Revenue"].sum().max() / k["revenue"] * 100
    summary = (f"**Summary:** Between {df['Order_Date'].min():%d %b %Y} and {df['Order_Date'].max():%d %b %Y}, "
               f"{k['customers']} customers placed {k['orders']:,} orders ({k['units']:,.0f} units) worth "
               f"{money(k['revenue'], currency)}. **{top_product}** was the biggest revenue product "
               f"({top_share:.0f}% of revenue).")
    if meta["has_category"]:
        top_cat = df.groupby("Category")["Revenue"].sum().idxmax()
        summary += f" The strongest category was **{top_cat}**."
    st.markdown(summary)

    st.subheader("💡 Key insights")
    for line in sa.auto_insights(df, meta, has_profit, currency):
        st.markdown("- " + line)

    if meta["has_category"] or meta["has_region"]:
        st.subheader("Category and region comparison")
        cols = st.columns(2)
        if meta["has_category"]:
            cat = sa.summarize(df, "Category").sort_values("Revenue", ascending=False)
            cols[0].plotly_chart(viz.grouped_bar(cat, "Category", currency, has_profit,
                                                 "Revenue and profit by category"), width="stretch")
        if meta["has_region"]:
            reg = sa.summarize(df, "Region").sort_values("Revenue", ascending=False)
            cols[1].plotly_chart(viz.grouped_bar(reg, "Region", currency, has_profit,
                                                 "Revenue and profit by region"), width="stretch")

# ----------------------------------------------------------------- page 2
elif page == PAGES[1]:
    ps = sa.summarize(df, "Product")
    choices = ["Units sold", "Revenue"] + (["Profit"] if has_profit else [])
    metric = st.radio("Rank products by", choices, horizontal=True)
    col = {"Units sold": "Units", "Revenue": "Revenue", "Profit": "Profit"}[metric]
    unit_label = metric if metric == "Units sold" else f"{metric} ({currency})"
    ranked = ps.dropna(subset=[col])

    left, right = st.columns(2)
    left.plotly_chart(viz.ranked_bar(ranked.nlargest(10, col), "Product", col,
                                     f"Top 10 products by {metric.lower()}", unit_label, viz.GREEN),
                      width="stretch")
    right.plotly_chart(viz.ranked_bar(ranked.nsmallest(10, col), "Product", col,
                                      f"Lowest 10 products by {metric.lower()}", unit_label, "#dc2626"),
                       width="stretch")
    if len(ranked) <= 10:
        st.caption("This selection has 10 or fewer products, so the two charts show the same items.")

    st.subheader("Why units sold and revenue are different")
    best_units = ps.loc[ps["Units"].idxmax()]
    best_rev = ps.loc[ps["Revenue"].idxmax()]
    st.markdown(
        "- **Units sold** counts how many items left the shop. **Revenue** = units × selling price, "
        "so it also depends on how expensive each item is.\n"
        "- A cheap product can sell thousands of units and still earn little money, while an expensive "
        "product can sell a few units and earn a lot.\n"
        + (f"- In your data: **{best_units['Product']}** sold the most units ({best_units['Units']:,.0f}), "
           f"but **{best_rev['Product']}** earned the most revenue ({money(best_rev['Revenue'], currency)}).\n"
           if best_units["Product"] != best_rev["Product"] else
           f"- In your data **{best_units['Product']}** leads in both units and revenue.\n")
        + ("- **Profit** goes one step further: revenue minus what the items cost you."
           if has_profit else "")
    )
    st.dataframe(ps.sort_values("Revenue", ascending=False).round(1), width="stretch", hide_index=True)

    if meta["has_region"]:
        st.subheader("Best-selling product in each city")
        st.caption("Uses all cities within the selected dates, products and categories. Shares are a % of each "
                   "city's own revenue, so large cities do not win automatically.")
        recs = sa.region_recommendations(compare_df)
        st.dataframe(recs.drop(columns="Recommendation").round(1), width="stretch", hide_index=True)
        tips = recs[~recs["Recommendation"].str.startswith("No clear gap")]
        if tips.empty:
            st.info("No clear gaps between cities for the current selection.")
        for text in tips["Recommendation"]:
            st.markdown("💡 " + text)

# ----------------------------------------------------------------- page 3
elif page == PAGES[2]:
    m = sa.monthly_summary(df)
    st.plotly_chart(viz.monthly_chart(m, currency, has_profit), width="stretch")

    best = m.loc[m["Revenue"].idxmax()]
    msg = f"🏆 **Best month by revenue: {best['Month_Label']}** with {money(best['Revenue'], currency)}"
    if has_profit and pd.notna(best["Profit"]):
        msg += f" and {money(best['Profit'], currency)} profit"
    st.success(msg + ".")
    if best["Coverage"] == "Partial month":
        st.warning("The best month only has partial data, so it may not be a fair winner.")

    full = m[m["Coverage"] == "Full month"]
    if len(full) >= 2:
        a, b = full.iloc[-2], full.iloc[-1]
        change = (b["Revenue"] - a["Revenue"]) / a["Revenue"] * 100 if a["Revenue"] else float("nan")
        st.markdown(f"**Fair comparison (last two full months):** {a['Month_Label']} → {b['Month_Label']}: "
                    f"revenue changed by **{change:+.1f}%**.")
    else:
        st.info("Fewer than two full months are selected, so a fair month-to-month comparison is not possible.")
    if (m["Coverage"] == "Partial month").any():
        st.caption("Months marked 'Partial month' do not have data for the whole month (e.g. your date filter "
                   "cuts them off) and should not be compared directly with full months.")

    table = m[["Month_Label", "Coverage", "Orders", "Units", "Revenue", "Revenue_MoM_%"]
              + (["Profit", "Profit_Margin_%"] if has_profit else [])]
    st.dataframe(table.round(1), width="stretch", hide_index=True)

# ----------------------------------------------------------------- page 4
elif page == PAGES[3]:
    cust = sa.customer_summary(df)
    left, right = st.columns(2)
    left.plotly_chart(viz.ranked_bar(cust.nlargest(10, "Spend"), "Customer_Name", "Spend",
                                     "Top 10 customers by spending", f"Total spend ({currency})"),
                      width="stretch")
    right.plotly_chart(viz.ranked_bar(cust.nlargest(10, "Orders"), "Customer_Name", "Orders",
                                      "Top 10 customers by order frequency", "Number of orders", viz.GREEN),
                       width="stretch")

    top_spender, top_frequent = cust.loc[cust["Spend"].idxmax()], cust.loc[cust["Orders"].idxmax()]
    st.markdown(
        "**Spend vs. frequency:** *Customer spend* is the total money a customer paid. *Order frequency* is "
        "how many separate orders they placed. A customer with few big orders can out-spend one who buys "
        "often but in small baskets.\n\n"
        f"Here, **{top_spender['Customer_Name']}** spent the most ({money(top_spender['Spend'], currency)}), "
        f"and **{top_frequent['Customer_Name']}** ordered most often ({top_frequent['Orders']} orders)."
    )

    if cust["Segment"].iloc[0] != "Not enough customers to group":
        st.subheader("Purchasing behaviour groups")
        st.plotly_chart(viz.customer_scatter(cust, currency), width="stretch")
        seg = cust.groupby("Segment").agg(Customers=("Customer_ID", "count"), Revenue=("Spend", "sum"),
                                          Avg_Orders=("Orders", "mean")).reset_index()
        st.dataframe(seg.round(1), width="stretch", hide_index=True)
        st.caption("Groups compare each customer with the median customer in the current selection "
                   "(higher or lower spend, more or fewer orders).")
    else:
        st.info("Fewer than 8 customers are selected - too few to group by behaviour.")
    st.dataframe(cust.assign(Last_Order=cust["Last_Order"].dt.date).sort_values("Spend", ascending=False).round(1),
                 width="stretch", hide_index=True)

    st.subheader("Inactive customers (win-back list)")
    span = max(int((df["Order_Date"].max() - df["Order_Date"].min()).days), 1)
    gap = st.slider("Show customers with no order for at least (days)", 7, max(span, 8), min(60, max(span, 8)))
    inactive, ref_date = sa.inactive_customers(df, gap)
    share = inactive["Spend"].sum() / k["revenue"] * 100 if k["revenue"] else 0
    i1, i2 = st.columns(2)
    i1.metric("Inactive customers", f"{len(inactive)} of {len(cust)}")
    i2.metric("Their share of past revenue", f"{share:.0f}%")
    st.caption(f"Measured against the latest order in the selected data ({ref_date:%d %b %Y}).")
    if inactive.empty:
        st.success("No customers have been inactive for that long.")
    else:
        st.dataframe(inactive.assign(Last_Order=inactive["Last_Order"].dt.date).round(1),
                     width="stretch", hide_index=True)

# ----------------------------------------------------------------- page 5
else:
    search = st.text_input("🔍 Search (product, customer name or order ID)")
    view = df
    if search:
        s = search.lower()
        view = df[df["Product"].str.lower().str.contains(s, regex=False)
                  | df["Customer_Name"].str.lower().str.contains(s, regex=False)
                  | df["Order_ID"].str.lower().str.contains(s, regex=False)]
    st.write(f"Showing **{len(view):,}** records")
    st.dataframe(view, width="stretch", hide_index=True)

    d1, d2 = st.columns(2)
    d1.download_button("⬇️ Download filtered data (CSV)", view.to_csv(index=False).encode("utf-8"),
                       "filtered_sales.csv", "text/csv")
    d2.download_button("⬇️ Download summary report (Excel)", sa.build_summary_excel(df, currency, meta),
                       "sales_summary.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with st.expander("File overview (as uploaded)"):
        info = file_overview(raw)
        st.write(f"**Shape:** {info['rows']:,} rows × {info['columns']} columns")
        st.dataframe(info["head"], width="stretch", hide_index=True)
        st.dataframe(info["dtypes"], width="stretch", hide_index=True)
    with st.expander("Data cleaning report", expanded=True):
        st.write(f"Rows in file: **{report['rows_in']:,}** → rows after cleaning: **{report['rows_out']:,}**")
        st.dataframe(report["steps"], width="stretch", hide_index=True)
        st.write("Missing values found in the original file:")
        if report["missing_before"].empty:
            st.write("None.")
        else:
            st.dataframe(report["missing_before"], width="stretch", hide_index=True)
