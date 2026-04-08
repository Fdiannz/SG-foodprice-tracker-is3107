import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "../../pipeline/etl"))
from load import get_client

st.set_page_config(page_title="Overview", page_icon="📊", layout="wide")

st.markdown("""
<style>
.metric-card {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 20px 24px;
    border-left: 4px solid #2563eb;
}
.section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #1e293b;
    margin-bottom: 4px;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Overview")
st.caption("Today's price landscape across all 4 stores.")

STORE_COLORS = {
    "fairprice":   "#F5821F",
    "redmart":     "#E31837",
    "coldstorage": "#0066CC",
    "shengsiong":  "#009B4E",
}

STORE_LABELS = {
    "fairprice":   "FairPrice",
    "redmart":     "RedMart",
    "coldstorage": "Cold Storage",
    "shengsiong":  "Sheng Siong",
}

def fetch_all(table, date_col):
    client = get_client()
    all_rows = []
    page = 0
    page_size = 1000
    while True:
        res = (
            client.table(table)
            .select("*")
            .order(date_col, desc=True)
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
        )
        if not res.data:
            break
        all_rows.extend(res.data)
        if len(res.data) < page_size:
            break
        page += 1
    return all_rows

@st.cache_data(ttl=300)
def load_recommendations():
    rows = fetch_all("canonical_product_daily_recommendations", "scraped_date_sg")
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    latest = df["scraped_date_sg"].max()
    return df[df["scraped_date_sg"] == latest]

@st.cache_data(ttl=300)
def load_commodity():
    rows = fetch_all("commodity_price_comparisons", "scraped_date")
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    latest = df["scraped_date"].max()
    return df[df["scraped_date"] == latest]

with st.spinner("Loading data..."):
    df = load_recommendations()
    df_commodity = load_commodity()

if df.empty:
    st.error("No data found. Make sure the pipeline has run.")
    st.stop()

# Only products seen in 2+ stores for meaningful comparison
df_multi = df[df["stores_seen_for_day"] >= 2]

st.markdown(f"**Data as of:** {df['scraped_date_sg'].max()}")
st.divider()

# ── KPI CARDS ─────────────────────────────────────────────────────────────────

st.subheader("At a Glance")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Matched Products", f"{len(df):,}")
c2.metric("Comparable Across 2+ Stores", f"{len(df_multi):,}")
c3.metric("Avg Price Spread", f"${df_multi['price_spread_sgd'].mean():.2f}",
          help="Average gap between cheapest and priciest store for products matched across 2+ stores")
c4.metric("Categories Covered", f"{df['unified_category'].nunique()}")

st.divider()

# ── CHART 1: Which store wins most? ──────────────────────────────────────────

st.subheader("Which store is cheapest most often?")
st.caption("Across all matched products available in 2+ stores today.")

counts = df_multi["cheapest_store"].value_counts().reset_index()
counts.columns = ["store", "count"]
counts["store_label"] = counts["store"].map(STORE_LABELS).fillna(counts["store"])
counts["pct"] = (counts["count"] / counts["count"].sum() * 100).round(1)

fig1 = go.Figure()
fig1.add_trace(go.Bar(
    x=counts["store_label"],
    y=counts["count"],
    marker_color=[STORE_COLORS.get(s, "#888") for s in counts["store"]],
    text=[f"{c} products<br>({p}%)" for c, p in zip(counts["count"], counts["pct"])],
    textposition="outside",
    hovertemplate="<b>%{x}</b><br>Cheapest for %{y} products<extra></extra>",
))
fig1.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(gridcolor="rgba(0,0,0,0.08)", title="Number of products"),
    xaxis=dict(title=""),
    height=380,
    margin=dict(t=20, b=20),
)
st.plotly_chart(fig1, use_container_width=True)

st.divider()

# ── CHART 2: Heatmap — store vs category ─────────────────────────────────────

st.subheader("Store competitiveness by category")
st.caption("How often each store offers the lowest price within each category.")

heat_data = (
    df_multi.groupby(["unified_category", "cheapest_store"])
    .size()
    .reset_index(name="count")
)
heat_pivot = heat_data.pivot(index="unified_category", columns="cheapest_store", values="count").fillna(0)
heat_pivot.columns = [STORE_LABELS.get(c, c) for c in heat_pivot.columns]

fig2 = px.imshow(
    heat_pivot,
    color_continuous_scale="Blues",
    aspect="auto",
    labels=dict(x="Store", y="Category", color="# Products cheapest"),
    text_auto=True,
)
fig2.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    height=380,
    margin=dict(t=20, b=20),
    coloraxis_showscale=False,
    xaxis=dict(side="bottom"),
)
fig2.update_traces(textfont_size=13)
st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── CHART 3: Price spread by category (box plot) ─────────────────────────────

st.subheader("Price spread distribution by category")
st.caption("Each dot is a matched product. Wider spread = bigger savings potential by switching stores.")

spread_df = df_multi[df_multi["price_spread_sgd"] > 0].copy()

fig3 = px.box(
    spread_df,
    x="unified_category",
    y="price_spread_sgd",
    color="unified_category",
    points="outliers",
    labels={
        "unified_category": "Category",
        "price_spread_sgd": "Price Spread (SGD)",
    },
)
fig3.update_layout(
    showlegend=False,
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(gridcolor="rgba(0,0,0,0.08)"),
    xaxis_tickangle=-25,
    height=400,
    margin=dict(t=20, b=20),
)
st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ── TABLE: Top 10 commodity spreads ──────────────────────────────────────────

st.subheader("Top 10 biggest price spreads — fresh goods")
st.caption("Based on commodity matching at the same pack size. These are genuinely comparable products.")

if not df_commodity.empty:
    top = (
        df_commodity[[
            "cut", "unified_category", "frozen_flag",
            "common_weight_g",
            "cheapest_store", "cheapest_price_sgd",
            "cheapest_product_name",
            "priciest_store", "priciest_price_sgd",
            "priciest_product_name",
            "price_spread_sgd",
        ]]
        .sort_values("price_spread_sgd", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    top["cheapest_store"] = top["cheapest_store"].map(STORE_LABELS).fillna(top["cheapest_store"])
    top["priciest_store"] = top["priciest_store"].map(STORE_LABELS).fillna(top["priciest_store"])
    top.columns = [
        "Cut", "Category", "Fresh/Frozen", "Pack (g)",
        "Cheapest Store", "Cheapest ($)", "Cheapest Product",
        "Priciest Store", "Priciest ($)", "Priciest Product",
        "Spread ($)",
    ]
    for col in ["Cheapest ($)", "Priciest ($)", "Spread ($)"]:
        top[col] = top[col].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "-")
    st.dataframe(top, use_container_width=True, hide_index=True)
else:
    st.info("No commodity data available.")