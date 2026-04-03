"""
dashboard.py
Streamlit dashboard for FakeStore Pricing Strategy Analysis.

Run with:
    streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from analysis import run_full_analysis, simulate_price_change

# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Pricing Strategy Dashboard",
    page_icon="💰",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .section-header {
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ── CACHE (IMPORTANT 🚀) ──────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_data(use_cache):
    return run_full_analysis(use_cache=use_cache)

# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.title("⚙️ Settings")

use_cache = st.sidebar.toggle("Use cached data", value=True)

if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! Reloading...")

# Load data safely
try:
    with st.spinner("Loading analysis..."):
        data = load_data(use_cache)

except Exception as e:
    st.error("⚠️ Failed to load live data. Showing cached data if available.")
    data = load_data(True)

products = data["products"]
cat_summary = data["category_summary"]
comp_enriched = data["competitor_enriched"]
recommendations = data["recommendations"]
margin_df = data["margin_simulation"]

# ── Header ────────────────────────────────────────────────────────────────────

st.title("💰 Pricing Strategy Dashboard")
st.caption("FakeStore Data · Competitor Benchmarking · Decision Intelligence")

st.divider()

# ── KPI Row ───────────────────────────────────────────────────────────────────

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("Products", len(products))
k2.metric("Categories", products["category"].nunique())
k3.metric("Avg Price", f"${products['price'].mean():.2f}")
k4.metric("Price Range", f"${products['price'].min():.2f} – ${products['price'].max():.2f}")
k5.metric("Avg Rating", f"{products['rating_rate'].mean():.2f} ⭐")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Category",
    "🏁 Competitors",
    "💡 Recommendations",
    "📈 Revenue",
    "🛍️ Explorer",
    "🧠 Simulator"
])

# ════════════════════════════════════════════════════════════════════
# TAB 1 — Category
# ════════════════════════════════════════════════════════════════════

with tab1:
    st.markdown('<p class="section-header">Category Pricing Overview</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(cat_summary, x="category", y="avg_price", color="category", text_auto=".2f")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.box(products, x="category", y="price", color="category")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════════════════
# TAB 2 — Competitors
# ════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown('<p class="section-header">Competitor Benchmarking</p>', unsafe_allow_html=True)

    fig = px.scatter(
        comp_enriched,
        x="avg_competitor_price",
        y="our_price",
        color="positioning",
        hover_name="product_name"
    )

    st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════════════════
# TAB 3 — Recommendations
# ════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown('<p class="section-header">Pricing Recommendations</p>', unsafe_allow_html=True)

    st.dataframe(recommendations, use_container_width=True)

# ════════════════════════════════════════════════════════════════════
# TAB 4 — Revenue
# ════════════════════════════════════════════════════════════════════

with tab4:
    st.markdown('<p class="section-header">Revenue & Margin Analysis</p>', unsafe_allow_html=True)

    cost_pct = st.slider("Cost %", 30, 80, 55)

    df = margin_df.copy()
    df["cost"] = df["price"] * cost_pct / 100
    df["profit"] = df["price"] - df["cost"]

    fig = px.box(df, x="category", y="profit")
    st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════════════════
# TAB 5 — Explorer
# ════════════════════════════════════════════════════════════════════

with tab5:
    st.markdown('<p class="section-header">Product Explorer</p>', unsafe_allow_html=True)

    price_range = st.slider(
        "Price Range",
        float(products["price"].min()),
        float(products["price"].max()),
        (float(products["price"].min()), float(products["price"].max()))
    )

    filtered = products[
        (products["price"] >= price_range[0]) &
        (products["price"] <= price_range[1])
    ]

    fig = px.scatter(filtered, x="price", y="rating_rate", size="rating_count")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(filtered)

# ════════════════════════════════════════════════════════════════════
# TAB 6 — Simulator (🔥 STAR FEATURE)
# ════════════════════════════════════════════════════════════════════

with tab6:
    st.markdown('<p class="section-header">What-if Pricing Simulator</p>', unsafe_allow_html=True)

    product_names = products["title"].tolist()
    selected_product = st.selectbox("Select Product", product_names)

    product = products[products["title"] == selected_product].iloc[0]

    st.write(f"**Price:** ${product['price']:.2f}")
    st.write(f"**Demand:** {product['rating_count']}")

    new_price = st.slider(
        "New Price",
        float(product["price"] * 0.5),
        float(product["price"] * 1.5),
        float(product["price"])
    )

    elasticity = st.slider("Elasticity", -3.0, -0.1, -1.2)

    result = simulate_price_change(product, new_price, elasticity)

    if result:
        col1, col2, col3 = st.columns(3)
        col1.metric("Old Revenue", f"${result['old_revenue']:.2f}")
        col2.metric("New Revenue", f"${result['new_revenue']:.2f}")
        col3.metric("Change %", f"{result['revenue_change_pct']}%")

        fig = go.Figure([
            go.Bar(name="Old", x=["Revenue"], y=[result["old_revenue"]]),
            go.Bar(name="New", x=["Revenue"], y=[result["new_revenue"]])
        ])
        st.plotly_chart(fig, use_container_width=True)

# ── Footer ─────────────────────────────────────────────────────────

st.divider()
st.caption("Built with Streamlit · Pricing Strategy Analysis Project")
