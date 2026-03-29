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
from analysis import (
    run_full_analysis,
    simulate_price_change,
    load_fakestore_data,
    load_competitor_data,
    enrich_competitor_data,
    COMPETITOR_COLS,
)

# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Pricing Strategy Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .metric-card {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.title("⚙️ Settings")
use_cache = st.sidebar.toggle("Use cached product data", value=True)

if st.sidebar.button("🔄 Re-scrape FakeStore API"):
    with st.spinner("Fetching latest data from FakeStore API..."):
        data = run_full_analysis(use_cache=False)
    st.sidebar.success("Data refreshed!")
else:
    with st.spinner("Loading analysis..."):
        data = run_full_analysis(use_cache=use_cache)

products = data["products"]
cat_summary = data["category_summary"]
comp_enriched = data["competitor_enriched"]
recommendations = data["recommendations"]
margin_df = data["margin_simulation"]
revenue_df = data["revenue_by_category"]

categories = ["All"] + sorted(products["category"].unique().tolist())
selected_cat = st.sidebar.selectbox("Filter by Category", categories)

if selected_cat != "All":
    products_filtered = products[products["category"] == selected_cat]
else:
    products_filtered = products

# ── Header ────────────────────────────────────────────────────────────────────

st.title("💰 FakeStore Pricing Strategy Dashboard")
st.caption("Data sourced from fakestoreapi.com · Competitor benchmarking included")

st.divider()

# ── KPI Row ───────────────────────────────────────────────────────────────────

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("Total Products", len(products))
k2.metric("Categories", products["category"].nunique())
k3.metric("Avg Price", f"${products['price'].mean():.2f}")
k4.metric("Price Range", f"${products['price'].min():.2f} – ${products['price'].max():.2f}")
k5.metric("Avg Rating", f"{products['rating_rate'].mean():.2f} ⭐")

st.divider()

# ── Tab Layout ────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Category Analysis",
    "🏁 Competitor Benchmarking",
    "💡 Recommendations",
    "📈 Revenue & Margins",
    "🛍️ Product Explorer",
    "🧠 What-if Simulator"
])


# ════════════════════════════════════════════════════════════════════
# TAB 1 — Category Analysis
# ════════════════════════════════════════════════════════════════════

with tab1:
    st.markdown('<p class="section-header">Category-Level Pricing Overview</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        fig_avg = px.bar(
            cat_summary,
            x="category",
            y="avg_price",
            color="category",
            title="Average Price by Category",
            text_auto=".2f",
            labels={"avg_price": "Avg Price ($)", "category": ""},
        )
        fig_avg.update_layout(showlegend=False, xaxis_tickangle=-20)
        st.plotly_chart(fig_avg, use_container_width=True)

    with col2:
        fig_box = px.box(
            products_filtered,
            x="category",
            y="price",
            color="category",
            title="Price Distribution per Category",
            labels={"price": "Price ($)", "category": ""},
        )
        fig_box.update_layout(showlegend=False, xaxis_tickangle=-20)
        st.plotly_chart(fig_box, use_container_width=True)

    # Price tiers heatmap
    tier_df = data["price_tiers"]
    pivot = tier_df.pivot(index="price_tier", columns="category", values="count").fillna(0)
    fig_heat = px.imshow(
        pivot,
        text_auto=True,
        color_continuous_scale="Blues",
        title="Product Count by Price Tier & Category",
        labels={"color": "Count"},
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    st.markdown("**Category Summary Table**")
    st.dataframe(cat_summary, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════
# TAB 2 — Competitor Benchmarking
# ════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown('<p class="section-header">Our Price vs Competitors</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        # Grouped bar: our price vs avg competitor per category
        comp_cat = data["competitor_category"]
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(name="Our Avg Price", x=comp_cat["category"], y=comp_cat["avg_our_price"]))
        fig_comp.add_trace(go.Bar(name="Competitor Avg", x=comp_cat["category"], y=comp_cat["avg_competitor_price"]))
        fig_comp.update_layout(
            barmode="group",
            title="Our Price vs Competitor Avg by Category",
            xaxis_title="",
            yaxis_title="Price ($)",
            xaxis_tickangle=-20,
        )
        st.plotly_chart(fig_comp, use_container_width=True)

    with col2:
        # Positioning distribution pie
        pos_counts = comp_enriched["positioning"].value_counts().reset_index()
        pos_counts.columns = ["positioning", "count"]
        fig_pie = px.pie(
            pos_counts,
            names="positioning",
            values="count",
            title="Our Pricing Positioning",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # Scatter: our price vs avg competitor
    fig_scatter = px.scatter(
        comp_enriched,
        x="avg_competitor_price",
        y="our_price",
        color="positioning",
        hover_name="product_name",
        hover_data=["category", "price_vs_avg"],
        title="Our Price vs Avg Competitor Price (per product)",
        labels={"avg_competitor_price": "Avg Competitor Price ($)", "our_price": "Our Price ($)"},
    )
    # Add diagonal reference line
    max_val = max(comp_enriched["our_price"].max(), comp_enriched["avg_competitor_price"].max()) + 20
    fig_scatter.add_shape(
        type="line", x0=0, y0=0, x1=max_val, y1=max_val,
        line=dict(dash="dash", color="gray")
    )
    fig_scatter.add_annotation(x=max_val * 0.7, y=max_val * 0.78, text="Price parity line",
                                showarrow=False, font=dict(color="gray"))
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown("**Detailed Competitor Comparison**")
    display_cols = ["product_name", "category", "our_price", "avg_competitor_price",
                    "min_competitor_price", "max_competitor_price", "price_vs_avg", "positioning"]
    st.dataframe(comp_enriched[display_cols], use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════
# TAB 3 — Recommendations
# ════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown('<p class="section-header">Pricing Recommendations</p>', unsafe_allow_html=True)

    action_colors = {
        "Reduce Price": "#ef4444",
        "Minor Reduction": "#f97316",
        "Maintain Price": "#22c55e",
        "Minor Increase": "#3b82f6",
        "Increase Price": "#8b5cf6",
    }

    # Summary counts
    action_counts = recommendations["recommendation"].value_counts().reset_index()
    action_counts.columns = ["action", "count"]
    action_counts["color"] = action_counts["action"].map(action_colors)

    col1, col2 = st.columns([1, 2])

    with col1:
        fig_actions = px.bar(
            action_counts,
            x="count",
            y="action",
            orientation="h",
            color="action",
            color_discrete_map=action_colors,
            title="Recommendation Breakdown",
        )
        fig_actions.update_layout(showlegend=False)
        st.plotly_chart(fig_actions, use_container_width=True)

    with col2:
        # Waterfall-style: current price vs suggested price
        rec_plot = recommendations.copy()
        rec_plot["price_delta"] = rec_plot["suggested_price"] - rec_plot["our_price"]
        fig_delta = px.bar(
            rec_plot,
            x="product_name",
            y="price_delta",
            color="recommendation",
            color_discrete_map=action_colors,
            title="Suggested Price Change per Product ($)",
            labels={"price_delta": "Price Delta ($)", "product_name": ""},
        )
        fig_delta.update_layout(xaxis_tickangle=-45, xaxis=dict(tickfont=dict(size=9)))
        st.plotly_chart(fig_delta, use_container_width=True)

    # Filter by action
    action_filter = st.multiselect(
        "Filter by Recommendation Type",
        options=recommendations["recommendation"].unique().tolist(),
        default=recommendations["recommendation"].unique().tolist(),
    )
    filtered_recs = recommendations[recommendations["recommendation"].isin(action_filter)]

    st.dataframe(
        filtered_recs.style.applymap(
            lambda v: f"color: {action_colors.get(v, 'black')}",
            subset=["recommendation"]
        ),
        use_container_width=True,
        hide_index=True,
    )


# ════════════════════════════════════════════════════════════════════
# TAB 4 — Revenue & Margins
# ════════════════════════════════════════════════════════════════════

with tab4:
    st.markdown('<p class="section-header">Revenue Potential & Margin Analysis</p>', unsafe_allow_html=True)

    cost_pct = st.slider("Assumed Cost as % of Price", min_value=30, max_value=80, value=55, step=5)
    margin_df_adj = margin_df.copy()
    margin_df_adj["estimated_cost"] = (margin_df_adj["price"] * cost_pct / 100).round(2)
    margin_df_adj["gross_margin"] = (margin_df_adj["price"] - margin_df_adj["estimated_cost"]).round(2)
    margin_df_adj["gross_margin_pct"] = ((margin_df_adj["gross_margin"] / margin_df_adj["price"]) * 100).round(2)

    col1, col2 = st.columns(2)

    with col1:
        fig_margin = px.box(
            margin_df_adj,
            x="category",
            y="gross_margin_pct",
            color="category",
            title="Gross Margin % Distribution by Category",
            labels={"gross_margin_pct": "Gross Margin (%)", "category": ""},
        )
        fig_margin.update_layout(showlegend=False, xaxis_tickangle=-20)
        st.plotly_chart(fig_margin, use_container_width=True)

    with col2:
        rev_adj = margin_df_adj.groupby("category").apply(lambda g: pd.Series({
            "estimated_revenue": (g["price"] * g["rating_count"]).sum().round(2),
            "estimated_profit": (g["gross_margin"] * g["rating_count"]).sum().round(2),
        })).reset_index()

        fig_rev = go.Figure()
        fig_rev.add_trace(go.Bar(name="Est. Revenue", x=rev_adj["category"], y=rev_adj["estimated_revenue"]))
        fig_rev.add_trace(go.Bar(name="Est. Profit", x=rev_adj["category"], y=rev_adj["estimated_profit"]))
        fig_rev.update_layout(
            barmode="group",
            title="Estimated Revenue vs Profit by Category",
            xaxis_title="",
            yaxis_title="Amount ($)",
            xaxis_tickangle=-20,
        )
        st.plotly_chart(fig_rev, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("**Top Value Products** (Best rating per dollar)")
        st.dataframe(data["top_value_products"], use_container_width=True, hide_index=True)

    with col4:
        st.markdown("**Potentially Overpriced Products** (High price, low rating)")
        st.dataframe(data["overpriced_products"], use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════
# TAB 5 — Product Explorer
# ════════════════════════════════════════════════════════════════════

with tab5:
    st.markdown('<p class="section-header">Product Explorer</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        price_min, price_max = st.slider(
            "Price Range ($)",
            float(products["price"].min()),
            float(products["price"].max()),
            (float(products["price"].min()), float(products["price"].max())),
        )
    with col2:
        min_rating = st.slider("Minimum Rating", 0.0, 5.0, 0.0, 0.1)

    cat_filter = st.multiselect(
        "Categories",
        options=products["category"].unique().tolist(),
        default=products["category"].unique().tolist(),
    )

    filtered = products[
        (products["price"] >= price_min) &
        (products["price"] <= price_max) &
        (products["rating_rate"] >= min_rating) &
        (products["category"].isin(cat_filter))
    ]

    st.caption(f"Showing {len(filtered)} of {len(products)} products")

    fig_explorer = px.scatter(
        filtered,
        x="price",
        y="rating_rate",
        size="rating_count",
        color="category",
        hover_name="title",
        hover_data=["price", "rating_rate", "rating_count"],
        title="Price vs Rating (bubble size = review count)",
        labels={"price": "Price ($)", "rating_rate": "Rating"},
    )
    st.plotly_chart(fig_explorer, use_container_width=True)

    st.dataframe(
        filtered[["id", "title", "category", "price", "rating_rate", "rating_count"]],
        use_container_width=True,
        hide_index=True,
    )

# ════════════════════════════════════════════════════════════════════
# TAB 6 — What-if Pricing Simulator
# ════════════════════════════════════════════════════════════════════

with tab6:
    st.markdown('<p class="section-header">What-if Pricing Simulator</p>', unsafe_allow_html=True)

    product_names = products["title"].tolist()
    selected_product = st.selectbox("Select Product", product_names)

    product_row = products[products["title"] == selected_product].iloc[0]

    st.write(f"**Category:** {product_row['category']}")
    st.write(f"**Current Price:** ${product_row['price']:.2f}")
    st.write(f"**Current Demand (proxy):** {product_row['rating_count']}")

    # Slider for new price
    new_price = st.slider(
        "Adjust Price ($)",
        min_value=float(product_row["price"] * 0.5),
        max_value=float(product_row["price"] * 1.5),
        value=float(product_row["price"]),
        step=1.0
    )

    elasticity = st.slider(
        "Price Elasticity",
        min_value=-3.0,
        max_value=-0.1,
        value=-1.2,
        step=0.1
    )

    result = simulate_price_change(product_row, new_price, elasticity)

    if result:
        col1, col2, col3 = st.columns(3)

        col1.metric("Old Revenue", f"${result['old_revenue']:.2f}")
        col2.metric("New Revenue", f"${result['new_revenue']:.2f}")
        col3.metric("Revenue Change %", f"{result['revenue_change_pct']}%")

        col4, col5 = st.columns(2)
        col4.metric("Old Demand", result["old_demand"])
        col5.metric("New Demand", result["new_demand"])

        # Simple comparison chart
        import plotly.graph_objects as go

        fig = go.Figure(data=[
            go.Bar(name="Old", x=["Revenue"], y=[result["old_revenue"]]),
            go.Bar(name="New", x=["Revenue"], y=[result["new_revenue"]])
        ])

        fig.update_layout(title="Revenue Comparison")
        st.plotly_chart(fig, use_container_width=True)


# ── Footer ────────────────────────────────────────────────────────────────────

st.divider()
st.caption("FakeStore Pricing Strategy Dashboard · Built with Streamlit & Plotly · Data: fakestoreapi.com")