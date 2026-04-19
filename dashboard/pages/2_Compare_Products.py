import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "../../pipeline/etl"))
from load import get_client

st.set_page_config(page_title="Compare Products", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1 { font-family: 'DM Serif Display', serif !important; font-size: 2.2rem !important;
     letter-spacing: -0.02em; color: #1a1a1a; }
h2 { font-family: 'DM Serif Display', serif !important; font-size: 1.4rem !important;
     color: #1a1a1a; font-weight: 400 !important; }
h3 { font-size: 0.72rem !important; font-weight: 600 !important;
     letter-spacing: 0.1em; text-transform: uppercase; color: #888 !important; }
[data-testid="metric-container"] {
    background: #fff; border: 1px solid #ebe7e0;
    border-radius: 10px; padding: 16px 20px !important;
}
[data-testid="metric-container"] label {
    font-size: 0.72rem !important; font-weight: 500;
    letter-spacing: 0.08em; text-transform: uppercase; color: #999;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'DM Serif Display', serif !important; font-size: 1.8rem !important;
}
hr { border-color: #ebe7e0 !important; }
</style>
""", unsafe_allow_html=True)

STORE_COLORS = {
    "fairprice": "#F5821F",
    "redmart": "#C8102E",
    "coldstorage": "#005BAC",
    "shengsiong": "#00843D",
}
STORE_LABELS = {
    "fairprice": "FairPrice",
    "redmart": "RedMart",
    "coldstorage": "Cold Storage",
    "shengsiong": "Sheng Siong",
}

PLOTLY_BASE = dict(
    font=dict(family="DM Sans, sans-serif", size=13, color="#1a1a1a"),
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(t=30, b=10, l=10, r=80),
)

def apply_base_axes(fig):
    fig.update_xaxes(gridcolor="#f0ede8", linecolor="#e0dbd2", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", linecolor="rgba(0,0,0,0)", zeroline=False)
    return fig

def _fetch_latest_date(table, date_col):
    client = get_client()
    res = client.table(table).select(date_col).order(date_col, desc=True).limit(1).execute()
    return res.data[0][date_col] if res.data else None

def _fetch_for_date(table, date_col, date_val, columns="*"):
    client = get_client()
    rows, page = [], 0
    while True:
        res = (
            client.table(table).select(columns)
            .eq(date_col, date_val)
            .range(page * 1000, (page + 1) * 1000 - 1)
            .execute()
        )
        if not res.data:
            break
        rows.extend(res.data)
        if len(res.data) < 1000:
            break
        page += 1
    return rows

FRESH_CATEGORIES = {"Fruits & Vegetables", "Meat & Seafood"}

@st.cache_data(ttl=300)
def load_recs():
    latest = _fetch_latest_date("canonical_product_daily_recommendations", "scraped_date_sg")
    if not latest:
        return pd.DataFrame()
    df = pd.DataFrame(_fetch_for_date("canonical_product_daily_recommendations", "scraped_date_sg", latest))
    if df.empty:
        return df
    df = df[df["stores_seen_for_day"] >= 2]
    return df[~df["unified_category"].isin(FRESH_CATEGORIES)]

@st.cache_data(ttl=300)
def load_prices_today():
    latest = _fetch_latest_date("canonical_product_daily_prices", "scraped_date_sg")
    if not latest:
        return pd.DataFrame()
    return pd.DataFrame(_fetch_for_date("canonical_product_daily_prices", "scraped_date_sg", latest))

with st.spinner("Loading..."):
    df_rec = load_recs()
    df_prices = load_prices_today()

if df_rec.empty:
    st.error("No data found.")
    st.stop()

st.title("Compare Products")
st.markdown(
    "<p style='color:#888; font-size:0.9rem; margin-top:-12px'>"
    "Only showing products matched across 2 or more stores — "
    "comparisons are guaranteed to be identical items. "
    "Fruits &amp; Vegetables and Meat &amp; Seafood are on the Fresh &amp; Commodity page.</p>",
    unsafe_allow_html=True
)
st.divider()

# ── FILTERS ───────────────────────────────────────────────────────────────────

col1, col2 = st.columns([1, 2])
with col1:
    cats = ["All"] + sorted(df_rec["unified_category"].dropna().unique().tolist())
    selected_cat = st.selectbox("Category", cats)
with col2:
    search = st.text_input("Search product", placeholder="Milo, Greek yogurt, soy sauce…")

filtered = df_rec.copy()
if selected_cat != "All":
    filtered = filtered[filtered["unified_category"] == selected_cat]
if search:
    filtered = filtered[
        filtered["canonical_name"].str.contains(search, case=False, na=False)
    ]

st.markdown(
    f"<p style='color:#888; font-size:0.85rem'>{len(filtered):,} products found</p>",
    unsafe_allow_html=True,
)

# ── PRODUCT TABLE ─────────────────────────────────────────────────────────────

display = (
    filtered[[
        "canonical_name", "canonical_brand", "unified_category", "size_display",
        "stores_seen_for_day", "cheapest_store", "cheapest_price_sgd",
        "priciest_store", "priciest_price_sgd", "price_spread_sgd",
    ]]
    .sort_values("price_spread_sgd", ascending=False)
    .reset_index(drop=True)
    .copy()
)
display["cheapest_store"] = display["cheapest_store"].map(STORE_LABELS).fillna(display["cheapest_store"])
display["priciest_store"] = display["priciest_store"].map(STORE_LABELS).fillna(display["priciest_store"])
display.columns = [
    "Product", "Brand", "Category", "Size", "Stores",
    "Cheapest Store", "Cheapest",
    "Priciest Store", "Priciest", "Spread",
]
for col in ["Cheapest", "Priciest", "Spread"]:
    display[col] = display[col].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "—")

st.dataframe(display, width='stretch', hide_index=True)
st.divider()

# ── PRODUCT DETAIL ────────────────────────────────────────────────────────────

st.subheader("Product detail")

if filtered.empty:
    st.info("No products match your search.")
    st.stop()

selection_df = (
    filtered.sort_values(["canonical_name", "size_display", "canonical_product_id"])
    .drop_duplicates(subset=["canonical_product_id"])
    .copy()
)
selection_df["product_label"] = selection_df.apply(
    lambda row: f"{row['canonical_name']} | {row['size_display']}"
    if pd.notna(row.get("size_display")) and str(row.get("size_display")).strip()
    else row["canonical_name"],
    axis=1,
)

selected_label = st.selectbox(
    "Select a product for full store breakdown",
    options=selection_df["product_label"].tolist(),
)

if selected_label:
    rec = selection_df[selection_df["product_label"] == selected_label].iloc[0]
    selected_canonical_product_id = rec["canonical_product_id"]
    price_rows = df_prices[
        df_prices["canonical_product_id"] == selected_canonical_product_id
    ].copy()
    price_rows["store_label"] = price_rows["store"].map(STORE_LABELS).fillna(price_rows["store"])
    price_rows = price_rows.sort_values("price_sgd")

    cheapest_label = STORE_LABELS.get(rec["cheapest_store"], rec["cheapest_store"])
    priciest_label = STORE_LABELS.get(rec["priciest_store"], rec["priciest_store"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Cheapest store", cheapest_label, f"${rec['cheapest_price_sgd']:.2f}")
    c2.metric("Priciest store", priciest_label, f"${rec['priciest_price_sgd']:.2f}")
    c3.metric("You save", f"${rec['price_spread_sgd']:.2f}", "by choosing the cheapest store")

    if not price_rows.empty:
        min_price = price_rows["price_sgd"].min()

        fig = go.Figure()
        for _, row in price_rows.iterrows():
            is_cheapest = row["price_sgd"] == min_price
            fig.add_trace(go.Bar(
                y=[row["store_label"]],
                x=[row["price_sgd"]],
                orientation="h",
                marker_color=STORE_COLORS.get(row["store"], "#aaa"),
                marker_line_width=3 if is_cheapest else 0,
                marker_line_color="#1a1a1a" if is_cheapest else "rgba(0,0,0,0)",
                text=f"  ${row['price_sgd']:.2f}",
                textposition="outside",
                name=row["store_label"],
                hovertemplate=(
                    f"<b>{row['store_label']}</b><br>"
                    f"${row['price_sgd']:.2f}<br>"
                    f"{row.get('store_product_name', '')}<extra></extra>"
                ),
            ))

        fig.update_layout(**PLOTLY_BASE, showlegend=False, height=240, xaxis_title="Price (SGD)")
        apply_base_axes(fig)
        st.plotly_chart(fig, width='stretch')

        st.markdown("### Store-level detail")
        detail = price_rows[[
            "store_label", "store_product_name", "price_sgd",
            "original_price_sgd", "discount_sgd", "unit", "product_url",
        ]].copy()
        detail["price_sgd"] = detail["price_sgd"].apply(lambda x: f"${x:.2f}")
        detail["original_price_sgd"] = detail["original_price_sgd"].apply(
            lambda x: f"${x:.2f}" if pd.notna(x) and x else "—"
        )
        detail["discount_sgd"] = detail["discount_sgd"].apply(
            lambda x: f"${x:.2f}" if pd.notna(x) and x else "—"
        )
        detail.columns = ["Store", "Product Name", "Price", "Original", "Discount", "Unit", "URL"]
        st.dataframe(detail, width='stretch', hide_index=True)

        # ── Match score breakdown ─────────────────────────────────────────────

        st.markdown("### Why these products were matched")
        st.caption(
            "Scores from the matching algorithm per store pair. "
            "Strong matches require score ≥ 0.93 with title similarity ≥ 0.82."
        )

        product_ids = price_rows["product_id"].tolist()
        if product_ids:
            client = get_client()
            cand_res = (
                client.table("product_match_candidates")
                .select(
                    "name_a,name_b,store_a,store_b,"
                    "brand_score,size_score,title_score,variant_score,"
                    "match_score,match_status,explanation"
                )
                .in_("product_id_a", product_ids)
                .eq("match_status", "strong_match")
                .limit(20)
                .execute()
            )
            cands = pd.DataFrame(cand_res.data or [])

            if not cands.empty:
                for _, cand in cands.iterrows():
                    sa = STORE_LABELS.get(cand["store_a"], cand["store_a"])
                    sb = STORE_LABELS.get(cand["store_b"], cand["store_b"])
                    with st.expander(f"{sa} vs {sb} — match score {cand['match_score']:.2f}"):
                        mc1, mc2, mc3, mc4 = st.columns(4)
                        mc1.metric("Brand", f"{cand['brand_score']:.2f}")
                        mc2.metric("Size", f"{cand['size_score']:.2f}")
                        mc3.metric("Title", f"{cand['title_score']:.2f}")
                        mc4.metric("Variant", f"{cand['variant_score']:.2f}")
                        st.caption(f"*{cand['name_a']}* → *{cand['name_b']}*")
                        if cand.get("explanation"):
                            st.caption(f"Algo notes: {cand['explanation']}")
            else:
                st.caption("No match candidate records found for this product.")

    st.divider()

    # ── Price history ─────────────────────────────────────────────────────────

    st.subheader("Price history")
    st.markdown("### How this product's price has moved across stores over time")

    with st.spinner("Loading price history..."):
        client_h = get_client()
        hist_rows = []
        p2 = 0
        while True:
            res2 = (
                client_h.table("canonical_product_daily_prices")
                .select("store,price_sgd,scraped_date_sg")
                .eq("canonical_product_id", int(selected_canonical_product_id))
                .order("scraped_date_sg", desc=False)
                .range(p2 * 1000, (p2 + 1) * 1000 - 1)
                .execute()
            )
            if not res2.data:
                break
            hist_rows.extend(res2.data)
            if len(res2.data) < 1000:
                break
            p2 += 1

    if hist_rows:
        hist_df = pd.DataFrame(hist_rows)
        hist_df["store_label"] = hist_df["store"].map(STORE_LABELS).fillna(hist_df["store"])

        if hist_df["scraped_date_sg"].nunique() > 1:
            fig_hist = px.line(
                hist_df,
                x="scraped_date_sg",
                y="price_sgd",
                color="store",
                color_discrete_map=STORE_COLORS,
                markers=True,
                labels={
                    "scraped_date_sg": "Date",
                    "price_sgd": "Price (SGD)",
                    "store": "Store",
                },
            )
            for trace in fig_hist.data:
                trace.name = STORE_LABELS.get(trace.name, trace.name)
            fig_hist.update_layout(
                **{**PLOTLY_BASE, "margin": dict(t=30, b=10, l=10, r=10)},
                height=300,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""),
            )
            apply_base_axes(fig_hist)
            st.plotly_chart(fig_hist, width='stretch')
        else:
            st.info(
                "Only one day of price data so far. "
                "History will appear after the pipeline runs across multiple days."
            )
