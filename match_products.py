"""
match_products.py
Matches FakeStore products with competitor products using fuzzy matching.
Generates competitors_prices.csv for analysis.
"""

import os
import pandas as pd
from rapidfuzz import fuzz, process

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

FAKESTORE_FILE = os.path.join(DATA_DIR, "products.csv")
COMPETITOR_FILE = os.path.join(DATA_DIR, "competitor_prices.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "competitors_prices.csv")


# ── Load Data ───────────────────────────────────────────────────────

def load_data():
    fake_df = pd.read_csv(FAKESTORE_FILE)
    comp_df = pd.read_csv(COMPETITOR_FILE)

    fake_df["title_clean"] = fake_df["title"].str.lower()
    comp_df["product_clean"] = comp_df["product"].str.lower()

    return fake_df, comp_df


# ── Matching Logic ──────────────────────────────────────────────────

KEYWORDS = ["laptop", "asus", "hp", "lenovo", "notebook"]

def match_products(fake_df, comp_df, threshold=40):
    results = []

    comp_products = comp_df["product_clean"].tolist()

    for _, f_row in fake_df.iterrows():
        f_name = f_row["title_clean"]

        # ✅ Only electronics from FakeStore
        if "electronic" not in f_row["category"].lower():
            continue

        # # ✅ Optional keyword filter (relaxes matching noise)
        # if not any(k in f_name for k in KEYWORDS):
        #     continue

        # 🔍 Fuzzy match
        match = process.extractOne(
            f_name,
            comp_products,
            scorer=fuzz.token_sort_ratio
        )

        if match:
            matched_name, score, idx = match

            if score >= threshold:
                matched_rows = comp_df[comp_df["product_clean"] == matched_name]
                comp_price = matched_rows["price"].mean()

                results.append({
                    "product_name": f_row["title"],
                    "category": f_row["category"],
                    "our_price": f_row["price"],
                    "competitor_a": round(comp_price, 2),
                    "match_score": score
                })

    return pd.DataFrame(results)


# ── Save Output ─────────────────────────────────────────────────────

def save_output(df):
    if df.empty:
        print("⚠️ No matches found. Try lowering threshold (e.g., 40).")
        return

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Saved matched data → {OUTPUT_FILE}")
    print(f"Matched products: {len(df)}")


# ── Main ────────────────────────────────────────────────────────────

def main():
    print("🔍 Matching products...")
    fake_df, comp_df = load_data()

    matched_df = match_products(fake_df, comp_df, threshold=50)

    save_output(matched_df)


if __name__ == "__main__":
    main()
