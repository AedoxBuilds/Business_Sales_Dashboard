"""Assignment 4 - Plotly charts. Every chart has a title, axis labels and units."""
import plotly.express as px
import plotly.graph_objects as go

TEMPLATE = "plotly_white"
BLUE, GREEN = "#2563eb", "#16a34a"


def revenue_over_time(df, currency):
    span = (df["Order_Date"].max() - df["Order_Date"].min()).days
    if span <= 60:
        series, level = df.groupby(df["Order_Date"].dt.normalize())["Revenue"].sum(), "daily"
    else:
        series, level = df.set_index("Order_Date")["Revenue"].resample("W").sum(), "weekly"
    fig = px.line(x=series.index, y=series.values, markers=True, template=TEMPLATE,
                  title=f"Revenue over time ({level})",
                  labels={"x": "Date", "y": f"Revenue ({currency})"})
    fig.update_traces(line_color=BLUE)
    return fig


def ranked_bar(data, label, value, title, value_label, color=BLUE):
    fig = px.bar(data, x=value, y=label, orientation="h", template=TEMPLATE, title=title,
                 labels={value: value_label, label: ""}, text_auto=".3s")
    fig.update_traces(marker_color=color)
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
    return fig


def monthly_chart(m, currency, has_profit):
    fig = go.Figure()
    fig.add_bar(x=m["Month_Label"], y=m["Revenue"], name="Revenue", marker_color=BLUE)
    if has_profit:
        fig.add_scatter(x=m["Month_Label"], y=m["Profit"], name="Profit", mode="lines+markers",
                        line={"color": GREEN, "width": 3})
    fig.update_layout(template=TEMPLATE, title=f"Monthly revenue and profit ({currency})",
                      xaxis_title="Month", yaxis_title=f"Amount ({currency})",
                      legend={"orientation": "h", "y": 1.1})
    return fig


def grouped_bar(data, label, currency, has_profit, title):
    fig = go.Figure()
    fig.add_bar(x=data[label], y=data["Revenue"], name="Revenue", marker_color=BLUE)
    if has_profit:
        fig.add_bar(x=data[label], y=data["Profit"], name="Profit", marker_color=GREEN)
    fig.update_layout(template=TEMPLATE, barmode="group", title=title,
                      xaxis_title=label, yaxis_title=f"Amount ({currency})",
                      legend={"orientation": "h", "y": 1.1})
    return fig


def customer_scatter(c, currency):
    return px.scatter(c, x="Orders", y="Spend", color="Segment", hover_name="Customer_Name",
                      template=TEMPLATE, title="Customer spend vs. order frequency",
                      labels={"Orders": "Number of orders", "Spend": f"Total spend ({currency})"})
