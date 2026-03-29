"""
analysis.py
Core pricing strategy analysis — category breakdowns, competitor comparisons,
margin estimates, and pricing recommendations.
"""

import os
import pandas as pd
import numpy as np
from scrapper import get_products

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
COMPETITORS_FILE = os.path.join(DATA_DIR, "competitors_prices.csv")


# ── 1. Load Data ─────────────────────────────────────────────────────────────

def load_fakestore_data(use_cache: bool = True) -> pd.DataFrame:
    """Load FakeStore product data."""
    return get_products(use_cache=use_cache)


def load_competitor_data() -> pd.DataFrame:
    """Load competitor pricing CSV."""
    if not os.path.exists(COMPETITORS_FILE):
        raise FileNotFoundError(
            f"Competitor data not found at {COMPETITORS_FILE}. "
            "Make sure data/competitors_prices.csv exists."
        )
    return pd.read_csv(COMPETITORS_FILE)

def generate_fake_competitors(fake_df):
    import random

    rows = []

    for _, row in fake_df.iterrows():
        base = row["price"]

        rows.append({
            "product_name": row["title"],
            "category": row["category"],
            "our_price": base,
            "competitor_a": round(base * random.uniform(0.9, 1.1), 2),
            "competitor_b": round(base * random.uniform(0.85, 1.15), 2),
            "competitor_c": round(base * random.uniform(0.8, 1.2), 2),
            "competitor_d": round(base * random.uniform(0.88, 1.12), 2),
        })

    return pd.DataFrame(rows)

# ── 2. Category Analysis ──────────────────────────────────────────────────────

def category_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate pricing stats per category."""
    summary = (
        df.groupby("category")
        .agg(
            product_count=("id", "count"),
            avg_price=("price", "mean"),
            median_price=("price", "median"),
            min_price=("price", "min"),
            max_price=("price", "max"),
            price_std=("price", "std"),
            avg_rating=("rating_rate", "mean"),
            total_reviews=("rating_count", "sum"),
        )
        .reset_index()
    )
    summary["avg_price"] = summary["avg_price"].round(2)
    summary["median_price"] = summary["median_price"].round(2)
    summary["price_std"] = summary["price_std"].round(2)
    summary["avg_rating"] = summary["avg_rating"].round(2)
    return summary.sort_values("avg_price", ascending=False)


def price_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Bucket products into price tiers."""
    bins = [0, 20, 50, 100, 300, float("inf")]
    labels = ["Budget (<$20)", "Economy ($20–$50)", "Mid-range ($50–$100)",
              "Premium ($100–$300)", "Luxury ($300+)"]
    df = df.copy()
    df["price_tier"] = pd.cut(df["price"], bins=bins, labels=labels)
    return df


def price_tier_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Count products per price tier per category."""
    df = price_distribution(df)
    return (
        df.groupby(["category", "price_tier"], observed=True)
        .size()
        .reset_index(name="count")
    )


# ── 3. Competitor Analysis ────────────────────────────────────────────────────

COMPETITOR_COLS = ["competitor_a", "competitor_b", "competitor_c", "competitor_d"]


def enrich_competitor_data(comp_df: pd.DataFrame) -> pd.DataFrame:
    """Add derived columns to competitor DataFrame."""
    comp_df = comp_df.copy()
    comp_df["avg_competitor_price"] = comp_df[COMPETITOR_COLS].mean(axis=1).round(2)
    comp_df["min_competitor_price"] = comp_df[COMPETITOR_COLS].min(axis=1).round(2)
    comp_df["max_competitor_price"] = comp_df[COMPETITOR_COLS].max(axis=1).round(2)
    comp_df["price_vs_avg"] = (
        (comp_df["our_price"] - comp_df["avg_competitor_price"])
        / comp_df["avg_competitor_price"] * 100
    ).round(2)
    comp_df["positioning"] = comp_df["price_vs_avg"].apply(_classify_positioning)
    comp_df["cheapest_competitor"] = comp_df[COMPETITOR_COLS].idxmin(axis=1)
    comp_df["price_gap_to_cheapest"] = (
        comp_df["our_price"] - comp_df["min_competitor_price"]
    ).round(2)
    return comp_df


def _classify_positioning(pct_diff: float) -> str:
    if pct_diff < -10:
        return "Significantly Cheaper"
    elif pct_diff < -3:
        return "Slightly Cheaper"
    elif pct_diff <= 3:
        return "Competitively Priced"
    elif pct_diff <= 10:
        return "Slightly Expensive"
    else:
        return "Significantly Expensive"


def competitor_category_summary(comp_df: pd.DataFrame) -> pd.DataFrame:
    """Category-level comparison vs competitors."""
    enriched = enrich_competitor_data(comp_df)
    return (
        enriched.groupby("category")
        .agg(
            avg_our_price=("our_price", "mean"),
            avg_competitor_price=("avg_competitor_price", "mean"),
            avg_price_vs_avg=("price_vs_avg", "mean"),
            products=("product_name", "count"),
        )
        .reset_index()
        .round(2)
    )


# ── 4. Pricing Recommendations ────────────────────────────────────────────────

def generate_recommendations(comp_df: pd.DataFrame) -> pd.DataFrame:
    """Rule-based pricing recommendations for each product."""
    enriched = enrich_competitor_data(comp_df)
    recommendations = []

    for _, row in enriched.iterrows():
        rec = _recommend(row)
        recommendations.append({
            "product_name": row["product_name"],
            "category": row["category"],
            "our_price": row["our_price"],
            "avg_competitor_price": row["avg_competitor_price"],
            "price_vs_avg_pct": row["price_vs_avg"],
            "positioning": row["positioning"],
            "recommendation": rec["action"],
            "suggested_price": rec["suggested_price"],
            "rationale": rec["rationale"],
        })

    return pd.DataFrame(recommendations)


def _recommend(row: pd.Series) -> dict:
    our = row["our_price"]
    avg_comp = row["avg_competitor_price"]
    min_comp = row["min_competitor_price"]
    pct = row["price_vs_avg"]

    if pct > 10:
        suggested = round(avg_comp * 1.02, 2)
        return {
            "action": "Reduce Price",
            "suggested_price": suggested,
            "rationale": f"We are {pct:.1f}% above competitors. "
                         f"Lower to ~${suggested} to stay competitive.",
        }
    elif pct < -10:
        suggested = round(avg_comp * 0.97, 2)
        return {
            "action": "Increase Price",
            "suggested_price": suggested,
            "rationale": f"We are {abs(pct):.1f}% below competitors. "
                         f"Room to raise to ~${suggested} without losing customers.",
        }
    elif -3 <= pct <= 3:
        return {
            "action": "Maintain Price",
            "suggested_price": our,
            "rationale": "Price is well-aligned with market. No change needed.",
        }
    elif 3 < pct <= 10:
        suggested = round(avg_comp * 1.01, 2)
        return {
            "action": "Minor Reduction",
            "suggested_price": suggested,
            "rationale": f"Slightly above market. Small reduction to ~${suggested} advised.",
        }
    else:
        suggested = round(avg_comp * 0.99, 2)
        return {
            "action": "Minor Increase",
            "suggested_price": suggested,
            "rationale": f"Slightly below market. Marginal increase to ~${suggested} possible.",
        }


# ── 5. Margin & Revenue Simulation ────────────────────────────────────────────

def simulate_margin(df: pd.DataFrame, cost_pct: float = 0.55) -> pd.DataFrame:
    """
    Estimate gross margin assuming cost = cost_pct * price.
    Default: 55% cost → 45% gross margin target.
    """
    df = df.copy()
    df["estimated_cost"] = (df["price"] * cost_pct).round(2)
    df["gross_margin"] = (df["price"] - df["estimated_cost"]).round(2)
    df["gross_margin_pct"] = ((df["gross_margin"] / df["price"]) * 100).round(2)
    return df


def revenue_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Estimate revenue potential using rating_count as a proxy for units sold."""
    df = simulate_margin(df)
    return (
        df.groupby("category")
        .apply(lambda g: pd.Series({
            "total_products": len(g),
            "estimated_units_sold": g["rating_count"].sum(),
            "estimated_revenue": (g["price"] * g["rating_count"]).sum().round(2),
            "estimated_profit": (g["gross_margin"] * g["rating_count"]).sum().round(2),
            "avg_margin_pct": g["gross_margin_pct"].mean().round(2),
        }))
        .reset_index()
    )


# ── 6. Top / Bottom Performers ────────────────────────────────────────────────

def top_value_products(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Products with best rating per dollar (value score)."""
    df = df.copy()
    df["value_score"] = (df["rating_rate"] / df["price"] * 100).round(4)
    return df.nlargest(n, "value_score")[
        ["title", "category", "price", "rating_rate", "rating_count", "value_score"]
    ]


def overpriced_products(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """High price but low rating — potentially overpriced."""
    df = df.copy()
    df["overpriced_score"] = (df["price"] / (df["rating_rate"] + 0.1)).round(2)
    return df.nlargest(n, "overpriced_score")[
        ["title", "category", "price", "rating_rate", "rating_count", "overpriced_score"]
    ]


# ── 7. Full Report ────────────────────────────────────────────────────────────

def run_full_analysis(use_cache: bool = True) -> dict:
    """Run all analyses and return results as a dict of DataFrames."""
    print("Running full pricing analysis...")
    products = load_fakestore_data(use_cache=use_cache)
    try:
        competitors = load_competitor_data()
        print("Loaded competitor data from CSV.")
    except FileNotFoundError:
        print("⚠️ Competitor data not found — generating synthetic competitors...")
        competitors = generate_fake_competitors(products)


    return {
        "products": products,
        "category_summary": category_summary(products),
        "price_tiers": price_tier_summary(products),
        "competitor_enriched": enrich_competitor_data(competitors),
        "competitor_category": competitor_category_summary(competitors),
        "recommendations": generate_recommendations(competitors),
        "margin_simulation": simulate_margin(products),
        "revenue_by_category": revenue_by_category(products),
        "top_value_products": top_value_products(products),
        "overpriced_products": overpriced_products(products),
    }


# ── 8. What-if Pricing Simulator ─────────────────────────────────────

def simulate_price_change(row: pd.Series, new_price: float, elasticity: float = -1.2):
    """
    Simulate demand and revenue impact when price changes.
    
    elasticity < 0 → normal demand behavior
    """
    old_price = row["price"]
    old_demand = row["rating_count"]  # proxy

    if old_price == 0:
        return None

    # % change in price
    price_change_pct = (new_price - old_price) / old_price

    # demand change using elasticity
    demand_change_pct = elasticity * price_change_pct

    new_demand = max(0, old_demand * (1 + demand_change_pct))

    new_revenue = new_price * new_demand
    old_revenue = old_price * old_demand

    return {
        "old_price": old_price,
        "new_price": new_price,
        "old_demand": old_demand,
        "new_demand": round(new_demand, 2),
        "old_revenue": round(old_revenue, 2),
        "new_revenue": round(new_revenue, 2),
        "revenue_change_pct": round(
            ((new_revenue - old_revenue) / old_revenue) * 100, 2
        ) if old_revenue != 0 else 0
    }


if __name__ == "__main__":
    results = run_full_analysis()
    print("\n=== Category Summary ===")
    print(results["category_summary"].to_string(index=False))
    print("\n=== Pricing Recommendations ===")
    print(results["recommendations"][["product_name", "our_price", "recommendation", "suggested_price"]].to_string(index=False))