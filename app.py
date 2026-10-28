import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Business Intelligence Dashboard",
    page_icon="📊",
    layout="wide"
)

@st.cache_data
def load_data():
    traffic = pd.read_csv("web_traffic.csv")
    churn = pd.read_csv("customer_churn.csv")
    regional = pd.read_csv("regional_market.csv")
    checkout = pd.read_csv("checkout_ab_test.csv")

    traffic["Date"] = pd.to_datetime(traffic["Date"], errors="coerce")
    checkout["Timestamp"] = pd.to_datetime(
        checkout["Timestamp"], errors="coerce"
    )

    churn = churn.drop_duplicates(subset="CustomerID").copy()
    churn = churn.replace(r"(?i)^\s*unknown\s*$", np.nan, regex=True)

    if churn["Region"].notna().any():
        churn["Region"] = churn["Region"].fillna(
            churn["Region"].mode()[0]
        )

    churn["TotalChargesINR"] = pd.to_numeric(
        churn["TotalChargesINR"], errors="coerce"
    )

    churn["MonthlyChargesINR"] = pd.to_numeric(
        churn["MonthlyChargesINR"], errors="coerce"
    )

    return traffic, churn, regional, checkout


traffic, churn, regional, checkout = load_data()

st.sidebar.title("Dashboard Filters")

min_date = traffic["Date"].min().date()
max_date = traffic["Date"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    start_date, end_date = min_date, max_date
else:
    start_date, end_date = date_range

traffic_regions = ["All"] + sorted(
    traffic["Region"].dropna().unique().tolist()
)

selected_region = st.sidebar.selectbox(
    "Website traffic region", traffic_regions
)

subscription_types = ["All"] + sorted(
    churn["SubscriptionType"].dropna().unique().tolist()
)

selected_category = st.sidebar.selectbox(
    "Subscription category", subscription_types
)

t = traffic[
    traffic["Date"].dt.date.between(start_date, end_date)
].copy()

c = checkout[
    checkout["Timestamp"].dt.date.between(start_date, end_date)
].copy()

if selected_region != "All":
    t = t[t["Region"] == selected_region]

if selected_category != "All":
    churn_view = churn[
        churn["SubscriptionType"] == selected_category
    ].copy()
else:
    churn_view = churn.copy()

st.title("📊 Interactive Business Intelligence Dashboard")
st.caption(
    "A multi-dataset dashboard for website engagement, "
    "customer retention, regional demand and checkout performance."
)

st.info(
    "Learning project: all supplied datasets are synthetic. "
    "Filters apply to the relevant sections; the churn and regional "
    "datasets do not contain the same date and region fields as traffic."
)

converted = c[c["Converted"].astype(str).str.lower() == "yes"]
revenue = pd.to_numeric(
    converted["OrderValueINR"], errors="coerce"
).fillna(0).sum()

active_visitors = c["VisitorID"].nunique()

churn_total = len(churn_view)
churned_count = (
    churn_view["Churn"].astype(str).str.lower() == "yes"
).sum()

churn_pct = (
    100 * churned_count / churn_total
    if churn_total else 0
)

avg_ticket = (
    pd.to_numeric(converted["OrderValueINR"], errors="coerce")
    .dropna().mean()
    if len(converted) else 0
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Revenue", f"₹{revenue:,.0f}")
k2.metric("Active Visitors", f"{active_visitors:,}")
k3.metric("Churn Rate", f"{churn_pct:.1f}%")
k4.metric("Average Ticket Size", f"₹{avg_ticket:,.0f}")

st.caption(
    "Revenue and average ticket size use converted checkout records. "
    "Active visitors means unique checkout VisitorIDs in the selected "
    "date range. Churn rate uses the selected customer subscription "
    "category and is not date-filtered."
)

st.divider()

st.header("1. Website Traffic & Engagement")

a, b = st.columns(2)

with a:
    if not t.empty:
        daily = t.groupby(t["Date"].dt.date).size().reset_index(name="Visits")
        daily.columns = ["Date", "Visits"]
        fig = px.line(
            daily, x="Date", y="Visits", markers=True,
            title="Website Visits Over Time"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No website visits match these filters.")

with b:
    if not t.empty:
        source_data = t.groupby("Source").agg(
            Visits=("SessionID", "count"),
            Registrations=("Registered", lambda x:
                (x.astype(str).str.lower() == "yes").sum())
        ).reset_index()
        source_data["Conversion Rate (%)"] = (
            100 * source_data["Registrations"] / source_data["Visits"]
        )
        fig = px.bar(
            source_data, x="Source", y="Visits",
            color="Conversion Rate (%)",
            title="Visits by Traffic Source",
            hover_data=["Registrations", "Conversion Rate (%)"]
        )
        st.plotly_chart(fig, use_container_width=True)

st.header("2. Customer Retention & Churn")

if not churn_view.empty:
    x, y = st.columns(2)

    with x:
        contract_data = churn_view.groupby("ContractType").agg(
            Customers=("CustomerID", "count"),
            Churned=("Churn", lambda s:
                (s.astype(str).str.lower() == "yes").sum())
        ).reset_index()

        contract_data["Churn Rate (%)"] = (
            100 * contract_data["Churned"] / contract_data["Customers"]
        )

        fig = px.bar(
            contract_data, x="ContractType", y="Churn Rate (%)",
            title="Churn Rate by Contract Type", color="Churn Rate (%)"
        )
        st.plotly_chart(fig, use_container_width=True)

    with y:
        churn_by_region = churn_view.groupby("Region").agg(
            Customers=("CustomerID", "count"),
            Churned=("Churn", lambda s:
                (s.astype(str).str.lower() == "yes").sum())
        ).reset_index()

        churn_by_region["Churn Rate (%)"] = (
            100 * churn_by_region["Churned"]
            / churn_by_region["Customers"]
        )

        fig = px.bar(
            churn_by_region, x="Region", y="Churn Rate (%)",
            title="Churn Rate by Customer Region"
        )
        st.plotly_chart(fig, use_container_width=True)

st.divider()

st.header("3. Regional Market Opportunities")

state_summary = regional.groupby("State").agg(
    Total_Demand=("MonthlySearchDemand", "sum"),
    Average_Demand=("MonthlySearchDemand", "mean"),
    Average_Competition=("ExistingCompetitors", "mean"),
    Average_Conversion=("LeadConversionRate", "mean"),
    Average_Acquisition_Cost=("EstimatedAcquisitionCostINR", "mean")
).reset_index()

x, y = st.columns(2)

with x:
    fig = px.bar(
        state_summary.sort_values("Total_Demand", ascending=False),
        x="State", y="Total_Demand",
        title="Total Monthly Search Demand by State"
    )
    st.plotly_chart(fig, use_container_width=True)

with y:
    fig = px.scatter_geo(
        regional,
        lat="Latitude",
        lon="Longitude",
        color="MonthlySearchDemand",
        size="MonthlySearchDemand",
        hover_name="City",
        hover_data=[
            "State", "ExistingCompetitors",
            "LeadConversionRate", "EstimatedAcquisitionCostINR"
        ],
        scope="asia",
        title="Regional Market Demand Map"
    )
    fig.update_geos(
        lataxis_range=[5, 38],
        lonaxis_range=[68, 98]
    )
    st.plotly_chart(fig, use_container_width=True)

st.dataframe(
    state_summary.sort_values("Total_Demand", ascending=False),
    use_container_width=True,
    hide_index=True
)

st.divider()

st.header("4. Checkout & A/B Experiment")

if not c.empty:
    a, b = st.columns(2)

    with a:
        experiment = c.groupby("Variant").agg(
            Visitors=("VisitorID", "nunique"),
            Conversions=("Converted", lambda s:
                (s.astype(str).str.lower() == "yes").sum())
        ).reset_index()

        experiment["Conversion Rate (%)"] = (
            100 * experiment["Conversions"] / experiment["Visitors"]
        )

        fig = px.bar(
            experiment, x="Variant", y="Conversion Rate (%)",
            title="Checkout Conversion Rate by Variant",
            text_auto=".2f"
        )
        st.plotly_chart(fig, use_container_width=True)

    with b:
        source_checkout = c.groupby("TrafficSource").agg(
            Visitors=("VisitorID", "nunique"),
            Conversions=("Converted", lambda s:
                (s.astype(str).str.lower() == "yes").sum())
        ).reset_index()

        source_checkout["Conversion Rate (%)"] = (
            100 * source_checkout["Conversions"]
            / source_checkout["Visitors"]
        )

        fig = px.bar(
            source_checkout, x="TrafficSource",
            y="Conversion Rate (%)",
            title="Checkout Conversion by Traffic Source"
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No checkout visitors match the selected date range.")

st.divider()

st.header("5. Data Tables")

with st.expander("View website traffic records"):
    st.dataframe(t, use_container_width=True)

with st.expander("View customer churn records"):
    st.dataframe(churn_view, use_container_width=True)

with st.expander("View regional market records"):
    st.dataframe(regional, use_container_width=True)

with st.expander("View checkout records"):
    st.dataframe(c, use_container_width=True)

st.caption(
    "Interpretation note: results describe synthetic learning data, "
    "not verified company performance. Correlation and group differences "
    "do not prove causation."
)
