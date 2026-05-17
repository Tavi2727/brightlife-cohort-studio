import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="BrightLife Care | Cohort & Retention Studio",
    page_icon="💊",
    layout="wide"
)

# ── LOAD & CLEAN ─────────────────────────────────────────────────────────────

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Normalise dates — handle timezone offsets and mixed formats
    df["order_date"] = pd.to_datetime(df["order_date"], utc=True, errors="coerce")
    df["order_date"] = df["order_date"].dt.tz_convert("UTC").dt.tz_localize(None)

    # Drop rows where date could not be parsed
    df = df.dropna(subset=["order_date"])

    # Deduplicate order_ids — keep first occurrence
    df = df.drop_duplicates(subset=["order_id"], keep="first")

    # Drop negative revenue (refunds / data errors)
    df = df[df["gross_revenue"] >= 0]

    # Fill missing channel with "unknown"
    df["channel"] = df["channel"].fillna("unknown").str.strip().str.lower()

    # Drop rows still missing gross_revenue
    df = df.dropna(subset=["gross_revenue"])

    # Derived columns
    df["order_month"] = df["order_date"].dt.to_period("M")
    df["order_month_dt"] = df["order_date"].dt.to_period("M").dt.to_timestamp()

    # First order month per customer (acquisition cohort)
    first_order = df.groupby("customer_id")["order_date"].min().reset_index()
    first_order.columns = ["customer_id", "first_order_date"]
    first_order["cohort_month"] = first_order["first_order_date"].dt.to_period("M")
    df = df.merge(first_order, on="customer_id", how="left")

    # Months since acquisition
    df["months_since_acq"] = (
        df["order_month"].astype(int) - df["cohort_month"].astype(int)
    )

    return df


@st.cache_data
def build_retention_matrix(df: pd.DataFrame):
    cohort_data = (
        df.groupby(["cohort_month", "months_since_acq"])["customer_id"]
        .nunique()
        .reset_index()
    )
    cohort_pivot = cohort_data.pivot_table(
        index="cohort_month", columns="months_since_acq", values="customer_id"
    )
    cohort_sizes = cohort_pivot[0]
    retention = cohort_pivot.divide(cohort_sizes, axis=0) * 100
    return retention, cohort_sizes


@st.cache_data
def build_ltv_by_channel(df: pd.DataFrame) -> pd.DataFrame:
    ltv = (
        df.groupby(["customer_id", "channel"])
        .agg(total_revenue=("gross_revenue", "sum"), orders=("order_id", "count"))
        .reset_index()
    )
    # Acquisition channel = channel of first order
    first_channel = (
        df.sort_values("order_date")
        .groupby("customer_id")
        .first()
        .reset_index()[["customer_id", "channel"]]
        .rename(columns={"channel": "acq_channel"})
    )
    ltv = ltv.merge(first_channel, on="customer_id", how="left")
    channel_ltv = (
        ltv.groupby("acq_channel")
        .agg(
            avg_ltv=("total_revenue", "mean"),
            total_revenue=("total_revenue", "sum"),
            customers=("customer_id", "nunique"),
            avg_orders=("orders", "mean"),
        )
        .reset_index()
    )
    return channel_ltv


@st.cache_data
def build_cumulative_revenue(df: pd.DataFrame) -> pd.DataFrame:
    cum = (
        df.groupby(["cohort_month", "months_since_acq"])["gross_revenue"]
        .sum()
        .groupby(level=0)
        .cumsum()
        .reset_index()
    )
    cohort_sizes = df.groupby("cohort_month")["customer_id"].nunique()
    cum = cum.merge(cohort_sizes.rename("cohort_size"), on="cohort_month")
    cum["cumrev_per_customer"] = cum["gross_revenue"] / cum["cohort_size"]
    return cum


# ── SIDEBAR ───────────────────────────────────────────────────────────────────

st.sidebar.image("https://img.icons8.com/color/96/caduceus.png", width=60)
st.sidebar.title("BrightLife Care")
st.sidebar.caption("Cohort & Retention Studio")

uploaded = st.sidebar.file_uploader("Upload your own orders.csv", type=["csv"])
if uploaded:
    df = load_data(uploaded)
else:
    df = load_data("orders.csv")

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Records loaded:** {len(df):,}")
st.sidebar.markdown(f"**Customers:** {df['customer_id'].nunique():,}")
st.sidebar.markdown(f"**Date range:** {df['order_date'].min().date()} → {df['order_date'].max().date()}")

channels = ["All"] + sorted(df["channel"].unique().tolist())
sel_channel = st.sidebar.selectbox("Filter by channel", channels)
if sel_channel != "All":
    df_filtered = df[df["channel"] == sel_channel]
else:
    df_filtered = df

# ── HEADER ────────────────────────────────────────────────────────────────────

st.title("💊 BrightLife Care — Cohort & Retention Studio")
st.caption("Monthly cohort retention · Lifetime value · Channel performance")

# KPI row
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Revenue", f"${df_filtered['gross_revenue'].sum():,.0f}")
k2.metric("Customers", f"{df_filtered['customer_id'].nunique():,}")
k3.metric("Orders", f"{df_filtered['order_id'].nunique():,}")
k4.metric("Avg Order Value", f"${df_filtered['gross_revenue'].mean():.2f}")
k5.metric("Avg Orders / Customer",
          f"{df_filtered.groupby('customer_id')['order_id'].count().mean():.1f}")

st.markdown("---")

# ── TAB LAYOUT ────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Cohort Retention Heatmap",
    "💰 Lifetime Value by Channel",
    "📈 Cumulative Revenue per Cohort",
    "📡 Channel Comparison"
])

# ── TAB 1: RETENTION HEATMAP ─────────────────────────────────────────────────

with tab1:
    st.subheader("Monthly Cohort Retention Heatmap")
    st.caption("Each cell shows % of the cohort's original customers who placed an order in that month.")

    retention, cohort_sizes = build_retention_matrix(df_filtered)

    # Limit to first 12 months for readability
    max_months = min(12, retention.shape[1])
    ret_display = retention.iloc[:, :max_months]

    cohort_labels = [str(c) for c in ret_display.index]
    month_labels = [f"Month {m}" for m in ret_display.columns]

    z = ret_display.values
    z_text = [[f"{v:.1f}%" if not np.isnan(v) else "" for v in row] for row in z]

    fig1 = go.Figure(go.Heatmap(
        z=z,
        x=month_labels,
        y=cohort_labels,
        text=z_text,
        texttemplate="%{text}",
        colorscale="Blues",
        zmin=0, zmax=100,
        colorbar=dict(title="Retention %"),
        hoverongaps=False,
    ))
    fig1.update_layout(
        height=500,
        xaxis_title="Months Since Acquisition",
        yaxis_title="Acquisition Cohort",
        margin=dict(l=10, r=10, t=30, b=10)
    )
    st.plotly_chart(fig1, use_container_width=True)

    with st.expander("📋 Raw retention table"):
        st.dataframe(ret_display.style.format("{:.1f}%", na_rep="—"))

    # Insight callout
    avg_m1 = retention[1].mean() if 1 in retention.columns else None
    if avg_m1:
        st.info(f"📌 **Insight:** Average Month-1 retention across all cohorts is **{avg_m1:.1f}%** — "
                f"meaning roughly {100-avg_m1:.0f}% of customers do not return after their first order.")

# ── TAB 2: LTV BY CHANNEL ────────────────────────────────────────────────────

with tab2:
    st.subheader("Lifetime Value by Acquisition Channel")
    st.caption("LTV = total gross revenue per customer, grouped by the channel they first purchased from.")

    channel_ltv = build_ltv_by_channel(df_filtered)

    col_a, col_b = st.columns(2)

    with col_a:
        fig2a = px.bar(
            channel_ltv.sort_values("avg_ltv", ascending=True),
            x="avg_ltv", y="acq_channel",
            orientation="h",
            labels={"avg_ltv": "Avg LTV ($)", "acq_channel": "Acquisition Channel"},
            title="Average LTV per Customer by Channel",
            color="avg_ltv",
            color_continuous_scale="Teal",
            text_auto=".2f"
        )
        fig2a.update_layout(showlegend=False, coloraxis_showscale=False, height=380)
        st.plotly_chart(fig2a, use_container_width=True)

    with col_b:
        fig2b = px.scatter(
            channel_ltv,
            x="customers", y="avg_ltv",
            size="total_revenue",
            color="acq_channel",
            hover_name="acq_channel",
            labels={"customers": "# Customers", "avg_ltv": "Avg LTV ($)"},
            title="LTV vs Customer Volume (bubble = total revenue)"
        )
        fig2b.update_layout(height=380)
        st.plotly_chart(fig2b, use_container_width=True)

    st.dataframe(
        channel_ltv.sort_values("avg_ltv", ascending=False)
        .rename(columns={
            "acq_channel": "Channel", "avg_ltv": "Avg LTV ($)",
            "total_revenue": "Total Revenue ($)", "customers": "Customers",
            "avg_orders": "Avg Orders/Customer"
        })
        .style.format({
            "Avg LTV ($)": "${:.2f}",
            "Total Revenue ($)": "${:,.0f}",
            "Avg Orders/Customer": "{:.2f}"
        }),
        use_container_width=True
    )

    best = channel_ltv.loc[channel_ltv["avg_ltv"].idxmax()]
    st.success(f"📌 **Insight:** **{best['acq_channel'].title()}** delivers the highest average LTV "
               f"(${best['avg_ltv']:.2f}/customer) — consider increasing spend there.")

# ── TAB 3: CUMULATIVE REVENUE ─────────────────────────────────────────────────

with tab3:
    st.subheader("Cumulative Revenue per Cohort")
    st.caption("Revenue accumulated per customer over months since acquisition, by cohort.")

    cum = build_cumulative_revenue(df_filtered)

    fig3 = px.line(
        cum,
        x="months_since_acq",
        y="cumrev_per_customer",
        color=cum["cohort_month"].astype(str),
        labels={
            "months_since_acq": "Months Since Acquisition",
            "cumrev_per_customer": "Cumulative Revenue / Customer ($)",
            "color": "Cohort"
        },
        title="Cumulative Revenue per Customer by Cohort",
        markers=True
    )
    fig3.update_layout(height=500, legend_title="Cohort Month")
    st.plotly_chart(fig3, use_container_width=True)

    # Also show total cumulative revenue by month
    monthly_rev = df_filtered.groupby("order_month_dt")["gross_revenue"].sum().reset_index()
    monthly_rev["cumulative"] = monthly_rev["gross_revenue"].cumsum()

    fig3b = make_subplots(specs=[[{"secondary_y": True}]])
    fig3b.add_trace(go.Bar(
        x=monthly_rev["order_month_dt"], y=monthly_rev["gross_revenue"],
        name="Monthly Revenue", marker_color="#60a5fa"
    ))
    fig3b.add_trace(go.Scatter(
        x=monthly_rev["order_month_dt"], y=monthly_rev["cumulative"],
        name="Cumulative Revenue", line=dict(color="#f59e0b", width=3)
    ), secondary_y=True)
    fig3b.update_layout(
        title="Monthly vs Cumulative Revenue",
        height=380,
        legend=dict(orientation="h")
    )
    fig3b.update_yaxes(title_text="Monthly Revenue ($)", secondary_y=False)
    fig3b.update_yaxes(title_text="Cumulative Revenue ($)", secondary_y=True)
    st.plotly_chart(fig3b, use_container_width=True)

# ── TAB 4: CHANNEL COMPARISON ────────────────────────────────────────────────

with tab4:
    st.subheader("Channel-Level Comparison")

    ch_summary = df_filtered.groupby("channel").agg(
        orders=("order_id", "count"),
        customers=("customer_id", "nunique"),
        total_revenue=("gross_revenue", "sum"),
        avg_order_value=("gross_revenue", "mean"),
    ).reset_index()
    ch_summary["revenue_per_customer"] = ch_summary["total_revenue"] / ch_summary["customers"]
    ch_summary["orders_per_customer"] = ch_summary["orders"] / ch_summary["customers"]

    col1, col2 = st.columns(2)

    with col1:
        fig4a = px.pie(
            ch_summary, values="total_revenue", names="channel",
            title="Revenue Share by Channel",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig4a.update_traces(textposition="inside", textinfo="percent+label")
        fig4a.update_layout(height=380, showlegend=False)
        st.plotly_chart(fig4a, use_container_width=True)

    with col2:
        fig4b = px.bar(
            ch_summary.sort_values("avg_order_value", ascending=False),
            x="channel", y="avg_order_value",
            color="channel",
            title="Average Order Value by Channel",
            labels={"avg_order_value": "Avg Order Value ($)", "channel": "Channel"},
            color_discrete_sequence=px.colors.qualitative.Set2,
            text_auto=".2f"
        )
        fig4b.update_layout(height=380, showlegend=False)
        st.plotly_chart(fig4b, use_container_width=True)

    # Orders per customer
    fig4c = px.bar(
        ch_summary.sort_values("orders_per_customer", ascending=False),
        x="channel", y="orders_per_customer",
        color="channel",
        title="Repeat Purchase Rate (Orders per Customer) by Channel",
        labels={"orders_per_customer": "Avg Orders / Customer", "channel": "Channel"},
        color_discrete_sequence=px.colors.qualitative.Pastel,
        text_auto=".2f"
    )
    fig4c.update_layout(height=350, showlegend=False)
    st.plotly_chart(fig4c, use_container_width=True)

    st.markdown("#### Full Channel Metrics Table")
    st.dataframe(
        ch_summary.sort_values("total_revenue", ascending=False)
        .rename(columns={
            "channel": "Channel", "orders": "Orders", "customers": "Customers",
            "total_revenue": "Total Revenue ($)", "avg_order_value": "Avg Order Value ($)",
            "revenue_per_customer": "Revenue / Customer ($)", "orders_per_customer": "Orders / Customer"
        })
        .style.format({
            "Total Revenue ($)": "${:,.0f}",
            "Avg Order Value ($)": "${:.2f}",
            "Revenue / Customer ($)": "${:.2f}",
            "Orders / Customer": "{:.2f}"
        }),
        use_container_width=True
    )

    top_ch = ch_summary.loc[ch_summary["total_revenue"].idxmax()]
    st.info(f"📌 **Insight:** **{top_ch['channel'].title()}** drives the most total revenue "
            f"(${top_ch['total_revenue']:,.0f}) with {top_ch['customers']:,} customers.")

# ── FOOTER ────────────────────────────────────────────────────────────────────

st.markdown("---")
st.caption("BrightLife Care · Cohort & Retention Studio · Built with Streamlit + Plotly")

