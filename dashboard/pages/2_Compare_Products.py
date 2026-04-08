import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "../../pipeline/etl"))
from load import get_client

st.set_page_config(page_title="Compare Products", page_icon="🔍", layout="wide")
st.title("🔍 Compare Products")
st.caption("Search for any branded product and compare its price across stores.")

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
    # Only show products seen in 2+ stores — otherwise no comparison to make
    return df[(df["scraped_date_sg"] == latest) & (df["stores_seen_for_day"] >= 2)]

@st.cache_data(ttl=300)
def load_prices():
    rows = fetch_all("canonical_product_daily_prices", "scraped_date_sg")
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    latest = df["scraped_date_sg"].max()
    return df[df["scraped_date_sg"] == latest]

with st.spinner("Loading data..."):
    df_rec = load_recommendations()
    df_prices = load_prices()

if df_rec.empty:
    st.error("No data found.")
    st.stop()

# ── FILTERS ───────────────────────────────────────────────────────────────────

col1, col2 = st.columns([1, 2])
with col1:
    categories = ["All"] + sorted(df_rec["unified_category"].dropna().unique().tolist())
    selected_cat = st.selectbox("Category", categories)
with col2:
    search = st.text_input("Search product", placeholder="e.g. Milo, Pokka, Greek yogurt")

filtered = df_rec.copy()
if selected_cat != "All":
    filtered = filtered[filtered["unified_category"] == selected_cat]
if search:
    filtered = filtered[filtered["canonical_name"].str.contains(search, case=False, na=False)]

st.markdown(f"**{len(filtered)} comparable products found**")
st.divider()

# ── PRODUCT TABLE ─────────────────────────────────────────────────────────────

display = (
    filtered[[
        "canonical_name", "canonical_brand", "unified_category",
        "size_display", "stores_seen_for_day",
        "cheapest_store", "cheapest_price_sgd",
        "priciest_store", "priciest_price_sgd",
        "price_spread_sgd",
    ]]
    .sort_values("price_spread_sgd", ascending=False)
    .reset_index(drop=True)
    .copy()
)
display["cheapest_store"] = display["cheapest_store"].map(STORE_LABELS).fillna(display["cheapest_store"])
display["priciest_store"] = display["priciest_store"].map(STORE_LABELS).fillna(display["priciest_store"])
display.columns = [
    "Product", "Brand", "Category", "Size", "Stores",
    "Cheapest Store", "Cheapest ($)",
    "Priciest Store", "Priciest ($)", "Spread ($)",
]
for col in ["Cheapest ($)", "Priciest ($)", "Spread ($)"]:
    display[col] = display[col].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "-")

st.dataframe(display, use_container_width=True, hide_index=True)
st.divider()

# ── PRODUCT DETAIL ────────────────────────────────────────────────────────────

st.subheader("Product detail")

if filtered.empty:
    st.info("No products match your search.")
    st.stop()

selected_name = st.selectbox(
    "Select a product for full store breakdown",
    options=filtered["canonical_name"].tolist()
)

if selected_name:
    rec_row = filtered[filtered["canonical_name"] == selected_name].iloc[0]
    price_rows = df_prices[df_prices["canonical_name"] == selected_name].copy()
    price_rows["store_label"] = price_rows["store"].map(STORE_LABELS).fillna(price_rows["store"])

    c1, c2, c3 = st.columns(3)
    cheapest_label = STORE_LABELS.get(rec_row["cheapest_store"], rec_row["cheapest_store"])
    priciest_label = STORE_LABELS.get(rec_row["priciest_store"], rec_row["priciest_store"])
    c1.metric("Cheapest Store", cheapest_label, f"${rec_row['cheapest_price_sgd']:.2f}")
    c2.metric("Priciest Store", priciest_label, f"${rec_row['priciest_price_sgd']:.2f}")
    c3.metric("You save", f"${rec_row['price_spread_sgd']:.2f}", "by choosing cheapest store")

    if not price_rows.empty:
        price_rows_sorted = price_rows.sort_values("price_sgd")

        # Horizontal bar chart — easier to read store names
        fig = go.Figure()
        for _, row in price_rows_sorted.iterrows():
            is_cheapest = row["is_cheapest_for_day"]
            fig.add_trace(go.Bar(
                y=[row["store_label"]],
                x=[row["price_sgd"]],
                orientation="h",
                marker_color=STORE_COLORS.get(row["store"], "#888"),
                text=f"${row['price_sgd']:.2f}",
                textposition="outside",
                name=row["store_label"],
                hovertemplate=(
                    f"<b>{row['store_label']}</b><br>"
                    f"${row['price_sgd']:.2f}<br>"
                    f"{row['store_product_name']}<extra></extra>"
                ),
            ))

        fig.update_layout(
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                title="Price (SGD)",
                gridcolor="rgba(0,0,0,0.08)",
            ),
            yaxis=dict(title=""),
            height=280,
            margin=dict(t=10, b=10, l=10, r=80),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Store breakdown table
        detail = price_rows[[
            "store_label", "store_product_name",
            "price_sgd", "original_price_sgd",
            "discount_sgd", "unit", "product_url"
        ]].copy()
        detail["price_sgd"] = detail["price_sgd"].apply(lambda x: f"${x:.2f}")
        detail["original_price_sgd"] = detail["original_price_sgd"].apply(
            lambda x: f"${x:.2f}" if pd.notna(x) and x else "-"
        )
        detail["discount_sgd"] = detail["discount_sgd"].apply(
            lambda x: f"${x:.2f}" if pd.notna(x) and x else "-"
        )
        detail.columns = ["Store", "Product Name", "Price", "Original Price", "Discount", "Unit", "URL"]
        st.dataframe(detail, use_container_width=True, hide_index=True)