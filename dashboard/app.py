import streamlit as st

st.set_page_config(
    page_title="SG Food Price Tracker",
    page_icon="🛒",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

h1 {
    font-family: 'DM Serif Display', serif !important;
    font-size: 3rem !important;
    letter-spacing: -0.03em;
    color: #1a1a1a;
    line-height: 1.1;
}

h2 {
    font-family: 'DM Serif Display', serif !important;
    font-size: 1.3rem !important;
    color: #1a1a1a;
    font-weight: 400 !important;
}

hr { border-color: #ebe7e0 !important; }

.store-pill {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 500;
    margin-right: 8px;
    margin-bottom: 6px;
    font-family: 'DM Sans', sans-serif;
}

.nav-card {
    background: #ffffff;
    border: 1px solid #ebe7e0;
    border-radius: 12px;
    padding: 24px 28px;
    height: 100%;
}

.nav-card h3 {
    font-family: 'DM Serif Display', serif !important;
    font-size: 1.15rem !important;
    color: #1a1a1a;
    font-weight: 400 !important;
    margin-bottom: 8px;
    text-transform: none !important;
    letter-spacing: 0 !important;
}

.nav-card p {
    font-size: 0.875rem;
    color: #777;
    line-height: 1.5;
    margin: 0;
}

.nav-card .page-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #bbb;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.title("SG Food Price Tracker")
st.markdown(
    "<p style='font-size:1.1rem; color:#666; max-width:600px; line-height:1.6; margin-top:-8px'>"
    "Daily price intelligence across Singapore's four major supermarkets — "
    "so you know where to buy what, and when a deal is actually a deal."
    "</p>",
    unsafe_allow_html=True
)

st.markdown("""
<div style='margin: 16px 0 32px 0'>
    <span class='store-pill' style='background:#FFF3E8; color:#F5821F'>FairPrice</span>
    <span class='store-pill' style='background:#FFF0F0; color:#C8102E'>RedMart</span>
    <span class='store-pill' style='background:#EEF4FF; color:#005BAC'>Cold Storage</span>
    <span class='store-pill' style='background:#EDFAF3; color:#00843D'>Sheng Siong</span>
</div>
""", unsafe_allow_html=True)

st.divider()

c1, c2, c3 = st.columns(3, gap="medium")

with c1:
    st.markdown("""
    <div class='nav-card'>
        <div class='page-label'>Page 1</div>
        <h3>Overview</h3>
        <p>Store competitiveness at a glance — which store wins most often,
        how prices spread across categories, match quality from the algorithm,
        and historical price trends over time.</p>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class='nav-card'>
        <div class='page-label'>Page 2</div>
        <h3>Compare Products</h3>
        <p>Search any branded product and see exactly what each store charges today,
        with price history over time and the algorithm's match confidence
        shown per store pair.</p>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown("""
    <div class='nav-card'>
        <div class='page-label'>Page 3</div>
        <h3>Fresh & Commodity</h3>
        <p>Meat, seafood, fruits and vegetables compared at the same pack size.
        Unit price per 100g per store, cheapest cut per category,
        and a full spread breakdown table.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.divider()

st.subheader("How the data works")

col_a, col_b, col_c = st.columns(3, gap="large")

with col_a:
    st.markdown("**Scraped daily**")
    st.markdown(
        "<p style='font-size:0.875rem; color:#666; line-height:1.6'>"
        "Prices are collected from each store's internal API every day via an Airflow pipeline. "
        "Raw data is stored as JSON, cleaned into a unified schema, then loaded into Supabase."
        "</p>", unsafe_allow_html=True
    )

with col_b:
    st.markdown("**Matched by algorithm**")
    st.markdown(
        "<p style='font-size:0.875rem; color:#666; line-height:1.6'>"
        "Products are matched across stores using a scoring algorithm — "
        "brand, size, title and variant similarity. Only strong matches (score ≥ 0.93) "
        "appear in comparisons."
        "</p>", unsafe_allow_html=True
    )

with col_c:
    st.markdown("**Two comparison methods**")
    st.markdown(
        "<p style='font-size:0.875rem; color:#666; line-height:1.6'>"
        "Branded goods use identity matching. Fresh meat and produce use commodity "
        "matching — grouped by cut type and compared at the same pack size."
        "</p>", unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)