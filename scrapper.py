"""
scrapper.py
Fetches product data from fakestoreapi.com and saves it locally.
"""

import requests
import json
import os
import pandas as pd
from datetime import datetime

BASE_URL = "https://fakestoreapi.com"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# -------------------------------
# FETCH FUNCTIONS
# -------------------------------

def fetch_all_products():
    """Fetch all products from FakeStore API with fallback."""
    url = f"{BASE_URL}/products"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print("API Error:", e)

        # Fallback → load from local CSV
        fallback_path = os.path.join(DATA_DIR, "products.csv")

        if os.path.exists(fallback_path):
            print("Loading fallback data from CSV...")
            return pd.read_csv(fallback_path)
        else:
            raise Exception("API failed and no local data available.")


def fetch_products_by_category(category: str):
    """Fetch products filtered by category."""
    encoded = requests.utils.quote(category)

    try:
        response = requests.get(f"{BASE_URL}/products/category/{encoded}", timeout=10)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print("Category fetch error:", e)
        return []


def fetch_all_categories():
    """Fetch all available product categories."""
    try:
        response = requests.get(f"{BASE_URL}/products/categories", timeout=10)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print("Category fetch error:", e)
        return []


# -------------------------------
# DATA PROCESSING
# -------------------------------

def products_to_dataframe(products):
    """Convert product list to a clean DataFrame."""

    # If already DataFrame (fallback case), return directly
    if isinstance(products, pd.DataFrame):
        return products

    if not products:
        raise Exception("No product data available.")

    df = pd.DataFrame(products)

    # Safe column selection
    expected_cols = ["id", "title", "price", "category", "description", "rating"]
    df = df[[col for col in expected_cols if col in df.columns]]

    # Handle rating column safely
    if "rating" in df.columns:
        df["rating_rate"] = df["rating"].apply(
            lambda x: x.get("rate", 0) if isinstance(x, dict) else 0
        )
        df["rating_count"] = df["rating"].apply(
            lambda x: x.get("count", 0) if isinstance(x, dict) else 0
        )
        df.drop(columns=["rating"], inplace=True)

    # Add timestamp
    df["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return df


# -------------------------------
# SAVE / LOAD FUNCTIONS
# -------------------------------

def save_products(df, filename="products.csv"):
    """Save products DataFrame to the data folder."""
    os.makedirs(DATA_DIR, exist_ok=True)

    filepath = os.path.join(DATA_DIR, filename)
    df.to_csv(filepath, index=False)

    print(f"Saved {len(df)} products to {filepath}")
    return filepath


def save_raw_json(data, filename="products_raw.json"):
    """Save raw API response as JSON."""
    os.makedirs(DATA_DIR, exist_ok=True)

    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Saved raw JSON to {filepath}")
    return filepath


def load_products(filename="products.csv"):
    """Load products from local CSV cache."""
    filepath = os.path.join(DATA_DIR, filename)

    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"No cached data found at {filepath}. Run scrape_and_save() first."
        )

    return pd.read_csv(filepath)


# -------------------------------
# MAIN PIPELINE
# -------------------------------

def scrape_and_save(save_json=False):
    """
    Full pipeline: fetch → parse → save → return DataFrame.
    """
    print("Fetching products from FakeStore API...")

    products = fetch_all_products()

    df = products_to_dataframe(products)

    print(f"Processed {len(df)} products.")

    if save_json and not isinstance(products, pd.DataFrame):
        save_raw_json(products)

    save_products(df)

    return df


def get_products(use_cache=True):
    """
    Get products — from cache if available, else fetch fresh.
    """
    cache_path = os.path.join(DATA_DIR, "products.csv")

    if use_cache and os.path.exists(cache_path):
        print("Loading products from local cache...")
        return load_products()

    try:
        return scrape_and_save()

    except Exception:
        print("Falling back to cache due to API failure...")

        if os.path.exists(cache_path):
            return load_products()
        else:
            raise Exception("No data available (API failed + no cache).")


# -------------------------------
# TEST RUN
# -------------------------------

if __name__ == "__main__":
    df = scrape_and_save(save_json=True)

    print("\nSample data:")
    print(df.head())

    print(f"\nCategories: {df['category'].unique().tolist()}")
    print(f"Price range: ${df['price'].min():.2f} – ${df['price'].max():.2f}")
