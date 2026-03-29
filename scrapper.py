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


def fetch_all_products() -> list[dict]:
    """Fetch all products from FakeStore API."""
    response = requests.get(f"{BASE_URL}/products", timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_products_by_category(category: str) -> list[dict]:
    """Fetch products filtered by category."""
    encoded = requests.utils.quote(category)
    response = requests.get(f"{BASE_URL}/products/category/{encoded}", timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_all_categories() -> list[str]:
    """Fetch all available product categories."""
    response = requests.get(f"{BASE_URL}/products/categories", timeout=10)
    response.raise_for_status()
    return response.json()


def products_to_dataframe(products: list[dict]) -> pd.DataFrame:
    """Convert product list to a clean DataFrame."""
    df = pd.DataFrame(products)
    df = df[["id", "title", "price", "category", "description", "rating"]]
    df["rating_rate"] = df["rating"].apply(lambda x: x.get("rate", 0) if isinstance(x, dict) else 0)
    df["rating_count"] = df["rating"].apply(lambda x: x.get("count", 0) if isinstance(x, dict) else 0)
    df.drop(columns=["rating"], inplace=True)
    df["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return df


def save_products(df: pd.DataFrame, filename: str = "products.csv"):
    """Save products DataFrame to the data folder."""
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)
    df.to_csv(filepath, index=False)
    print(f"Saved {len(df)} products to {filepath}")
    return filepath


def save_raw_json(data: list[dict], filename: str = "products_raw.json"):
    """Save raw API response as JSON."""
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved raw JSON to {filepath}")
    return filepath


def load_products(filename: str = "products.csv") -> pd.DataFrame:
    """Load products from local CSV cache."""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"No cached data found at {filepath}. Run scrape_and_save() first."
        )
    return pd.read_csv(filepath)


def scrape_and_save(save_json: bool = False) -> pd.DataFrame:
    """
    Full pipeline: fetch → parse → save → return DataFrame.
    This is the main entry point used by other modules.
    """
    print("Fetching products from FakeStore API...")
    products = fetch_all_products()
    print(f"Fetched {len(products)} products.")

    if save_json:
        save_raw_json(products)

    df = products_to_dataframe(products)
    save_products(df)
    return df


def get_products(use_cache: bool = True) -> pd.DataFrame:
    """
    Get products — from cache if available and use_cache=True, else re-scrape.
    """
    cache_path = os.path.join(DATA_DIR, "products.csv")
    if use_cache and os.path.exists(cache_path):
        print("Loading products from local cache...")
        return load_products()
    return scrape_and_save()


if __name__ == "__main__":
    df = scrape_and_save(save_json=True)
    print("\nSample data:")
    print(df.head())
    print(f"\nCategories: {df['category'].unique().tolist()}")
    print(f"Price range: ${df['price'].min():.2f} – ${df['price'].max():.2f}")