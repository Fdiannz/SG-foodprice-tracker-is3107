import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "../../pipeline/etl"))
from load import get_client

st.set_page_config(page_title="Fresh Commodity", page_icon="🥩", layout="wide")
st.title("🥩 Fresh & Commodity Comparison")
st.caption("Prices compared at the same pack size across stores — meat, seafood, fruits and vegetables.")

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
def load_data():
    rows = fetch_all("commodity_price_comparisons", "scraped_date")
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    latest = df["scraped_date"].max()
    return df[df["scraped_date"] == latest]

with st.spinner("Loading data..."):
    df = load_data()

if df.empty:
    st.error("No commodity data found.")
    st.stop()

df["cheapest_store_label"] = df["cheapest_store"].map(STORE_LABELS).fillna(df["cheapest_store"])
df["priciest_store_label"] = df["priciest_store"].map(STORE_LABELS).fillna(df["priciest_store"])

st.markdown(f"**Data as of:** {df['scraped_date'].max()}")
st.divider()

# ── FILTERS ───────────────────────────────────────────────────────────────────

col1, col2, col3 = st.columns(3)
with col1:
    categories = ["All"] + sorted(df["unified_category"].dropna().unique().tolist())
    selected_cat = st.selectbox("Category", categories)
with col2:
    frozen_options = ["All"] + sorted(df["frozen_flag"].dropna().unique().tolist())
    selected_frozen = st.selectbox("Fresh / Frozen", frozen_options)
with col3:
    search_cut = st.text_input("Search", placeholder="e.g. chicken breast, broccoli, salmon")

filtered = df.copy()
if selected_cat != "All":
    filtered = filtered[filtered["unified_category"] == selected_cat]
if selected_frozen != "All":
    filtered = filtered[filtered["frozen_flag"] == selected_frozen]
if search_cut:
    filtered = filtered[filtered["cut"].str.contains(search_cut, case=False, na=False)]

st.markdown(f"**{len(filtered)} cuts found**")
st.divider()

# ── CHART 1: Cheapest store per cut (horizontal bar) ─────────────────────────

st.subheader("Cheapest store per cut")
st.caption("Price shown is for the most common pack size across stores.")

if not filtered.empty:
    chart_df = filtered.sort_values("cheapest_price_sgd", ascending=True).head(30)

    fig = px.bar(
        chart_df,
        y="cut",
        x="cheapest_price_sgd",
        color="cheapest_store",
        color_discrete_map=STORE_COLORS,
        orientation="h",
        text="cheapest_price_sgd",
        labels={
            "cut": "",
            "cheapest_price_sgd": "Cheapest Price (SGD)",
            "cheapest_store": "Store",
        },
        hover_data={
            "common_weight_g": True,
            "frozen_flag": True,
            "cheapest_product_name": True,
            "cheapest_store": False,
        },
        custom_data=["cheapest_store_label", "common_weight_g", "frozen_flag", "cheapest_product_name"],
    )
    fig.update_traces(
        texttemplate="$%{x:.2f}",
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Store: %{customdata[0]}<br>"
            "Price: $%{x:.2f}<br>"
            "Pack: %{customdata[1]}g (%{customdata[2]})<br>"
            "Product: %{customdata[3]}<extra></extra>"
        ),
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(0,0,0,0.08)", title="Price (SGD)"),
        yaxis=dict(title="", autorange="reversed"),
        height=max(400, len(chart_df) * 28),
        margin=dict(t=10, b=10, r=100),
        legend_title="Cheapest Store",
    )
    # Rename legend labels
    for trace in fig.data:
        trace.name = STORE_LABELS.get(trace.name, trace.name)

    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── CHART 2: Price spread per cut ────────────────────────────────────────────

st.subheader("How much can you save by switching stores?")
st.caption("Spread = difference between cheapest and priciest store at the same pack size.")

if not filtered.empty:
    spread_df = filtered[filtered["price_spread_sgd"] > 0].sort_values("price_spread_sgd", ascending=True)

    fig2 = px.bar(
        spread_df,
        y="cut",
        x="price_spread_sgd",
        color="cheapest_store",
        color_discrete_map=STORE_COLORS,
        orientation="h",
        text="price_spread_sgd",
        labels={
            "cut": "",
            "price_spread_sgd": "Price Spread (SGD)",
            "cheapest_store": "Cheapest Store",
        },
        custom_data=["cheapest_store_label", "priciest_store_label", "cheapest_price_sgd", "priciest_price_sgd"],
    )
    fig2.update_traces(
        texttemplate="$%{x:.2f}",
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Cheapest: %{customdata[0]} $%{customdata[2]:.2f}<br>"
            "Priciest: %{customdata[1]} $%{customdata[3]:.2f}<br>"
            "Spread: $%{x:.2f}<extra></extra>"
        ),
    )
    fig2.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(0,0,0,0.08)", title="Price Spread (SGD)"),
        yaxis=dict(title="", autorange="reversed"),
        height=max(400, len(spread_df) * 28),
        margin=dict(t=10, b=10, r=100),
        legend_title="Cheapest Store",
    )
    for trace in fig2.data:
        trace.name = STORE_LABELS.get(trace.name, trace.name)

    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── TABLE ─────────────────────────────────────────────────────────────────────

st.subheader("Full comparison table")

if not filtered.empty:
    table = filtered[[
        "cut", "unified_category", "frozen_flag",
        "common_weight_g",
        "cheapest_store_label", "cheapest_price_sgd", "cheapest_product_name",
        "priciest_store_label", "priciest_price_sgd", "priciest_product_name",
        "price_spread_sgd", "stores_seen",
    ]].sort_values("price_spread_sgd", ascending=False).reset_index(drop=True)

    table.columns = [
        "Cut", "Category", "Fresh/Frozen", "Pack (g)",
        "Cheapest Store", "Cheapest ($)", "Cheapest Product",
        "Priciest Store", "Priciest ($)", "Priciest Product",
        "Spread ($)", "Stores",
    ]
    for col in ["Cheapest ($)", "Priciest ($)", "Spread ($)"]:
        table[col] = table[col].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "-")

    st.dataframe(table, use_container_width=True, hide_index=True)