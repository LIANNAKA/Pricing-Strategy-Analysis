import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import argparse
import os

def scrape_webshop(url, site_name):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    products = []
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for card in soup.select(".thumbnail"):
        name = card.select_one(".title")
        price = card.select_one(".price")

        if name and price:
            products.append({
                "competitor": site_name,
                "product": name.get_text(strip=True),
                "price": float(price.get_text().replace("$", "")),
                "scraped_at": scraped_at,
            })

    return products


def save_csv(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["competitor", "product", "price", "scraped_at"])
        writer.writeheader()
        writer.writerows(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--site", default="competitor")
    parser.add_argument("--output", default="data/competitor_prices.csv")
    args = parser.parse_args()

    data = scrape_webshop(args.url, args.site)
    save_csv(data, args.output)

    print(f"Saved {len(data)} products → {args.output}")


if __name__ == "__main__":
    main()
