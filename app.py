"""A guided learning project: HTML -> clean data -> CSV, SQLite and a report."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import sys
import time
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import pandas as pd
import requests


ROOT = Path(__file__).resolve().parent
START_URL = "https://books.toscrape.com/catalogue/page-1.html"
RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def parse_books(html, page_url):
    """Extract text first. Cleaning and numeric conversion happen separately."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("article.product_pod")
    if not cards:
        raise ValueError("No book cards found. The page may have changed.")

    books = []
    for card in cards:
        link = card.select_one("h3 a")
        price = card.select_one(".price_color")
        stock = card.select_one(".availability")
        stars = card.select_one(".star-rating")
        if any(node is None for node in (link, price, stock, stars)):
            raise ValueError("A book is missing a required HTML field.")
        if not link.get("href"):
            raise ValueError("A book is missing its product link.")

        rating = next((RATINGS[c] for c in stars.get("class", []) if c in RATINGS), None)
        books.append({
            "title": link.get("title") or link.get_text(" ", strip=True),
            "price_text": price.get_text(" ", strip=True),
            "availability_text": stock.get_text(" ", strip=True),
            "rating": rating,
            "product_url": urljoin(page_url, link["href"]),
        })

    next_link = soup.select_one("li.next a")
    next_url = urljoin(page_url, next_link["href"]) if next_link and next_link.get("href") else None
    return books, next_url


def clean_books(records):
    """Validate data and remove duplicate product URLs with Pandas."""
    if not records:
        raise ValueError("Cannot create a report from an empty dataset.")
    frame = pd.DataFrame(records)
    frame["title"] = frame["title"].str.replace(r"\s+", " ", regex=True).str.strip()
    amounts = frame["price_text"].str.strip().str.extract(r"^£(\d+(?:\.\d{1,2})?)$", expand=False)
    frame["price_gbp"] = pd.to_numeric(amounts, errors="coerce")
    frame["rating"] = pd.to_numeric(frame["rating"], errors="coerce")
    stock = frame["availability_text"].str.replace(r"\s+", " ", regex=True).str.strip().str.lower()

    invalid = (
        frame["title"].isna() | frame["title"].eq("")
        | frame["price_gbp"].isna() | frame["price_gbp"].le(0)
        | ~frame["rating"].isin([1, 2, 3, 4, 5])
        | ~stock.isin(["in stock", "out of stock"])
    )
    if invalid.any():
        raise ValueError(f"Invalid book data in rows: {frame.index[invalid].tolist()}")

    frame["in_stock"] = stock.eq("in stock")
    frame["rating"] = frame["rating"].astype(int)
    columns = ["title", "price_gbp", "rating", "in_stock", "product_url"]
    return frame[columns].drop_duplicates("product_url").reset_index(drop=True)


def collect_live(pages):
    """Fetch at most five listing pages, one second apart, from the practice site."""
    records = []
    current_url = START_URL
    visited = set()
    with requests.Session() as session:
        session.headers["User-Agent"] = "BookDataLab/1.0 (educational practice project)"
        for page_number in range(pages):
            if current_url is None:
                break
            address = urlparse(current_url)
            if address.scheme != "https" or address.netloc != "books.toscrape.com":
                raise ValueError("Unexpected pagination link; stopped before fetching it.")
            if current_url in visited:
                raise ValueError("Repeated pagination link; stopped to avoid a loop.")
            if page_number:
                time.sleep(1)
            visited.add(current_url)
            response = session.get(current_url, timeout=(5, 20))
            response.raise_for_status()
            response.encoding = "utf-8"
            page_books, current_url = parse_books(response.text, current_url)
            records.extend(page_books)
    return records


def save_outputs(frame, output_dir, mode, raw_count):
    """Save CSV, an SQL table, a grouped report and a readable summary."""
    output_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_dir / "books.csv", index=False, encoding="utf-8-sig")
    # SQLite's transaction context does not close the connection itself.
    with closing(sqlite3.connect(output_dir / "books.sqlite")) as database:
        with database:
            frame.to_sql("books", database, if_exists="replace", index=False)
            by_rating = pd.read_sql_query(
                "SELECT rating, COUNT(*) AS book_count, "
                "ROUND(AVG(price_gbp), 2) AS average_price_gbp "
                "FROM books GROUP BY rating ORDER BY rating", database
            )
    by_rating.to_csv(output_dir / "by_rating.csv", index=False, encoding="utf-8-sig")

    cheapest = frame.sort_values(["price_gbp", "title"]).head(5)
    lines = [
        "# Book Data Lab report", "", f"Mode: {mode}",
        f"Generated (UTC): {datetime.now(timezone.utc).isoformat()}",
        "Source: locally authored synthetic sample" if mode == "DEMO" else f"Source: {START_URL}",
        "", "This is practice data. It is not real market or financial information.", "",
        f"Raw rows: {raw_count}", f"Unique books: {len(frame)}",
        f"Duplicate rows removed: {raw_count - len(frame)}",
        f"Books in stock: {int(frame['in_stock'].sum())}",
        f"Average price (GBP): {frame['price_gbp'].mean():.2f}",
        f"Lowest price (GBP): {frame['price_gbp'].min():.2f}",
        f"Highest price (GBP): {frame['price_gbp'].max():.2f}",
        "", "## Five cheapest books", "",
    ]
    for row in cheapest.itertuples(index=False):
        lines.append(f"- {row.title}: GBP {row.price_gbp:.2f}")
    (output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Use a synthetic local HTML sample; no network requests")
    parser.add_argument("--pages", type=int, choices=range(1, 6), default=1, metavar="1-5", help="Maximum live listing pages (default: 1)")
    parser.add_argument("--output", type=Path, help="Output folder; generated files in this folder are replaced")
    args = parser.parse_args(argv)
    mode = "DEMO" if args.demo else "LIVE"
    output_dir = args.output or ROOT / "output" / mode.lower()

    try:
        if args.demo:
            html = (ROOT / "samples" / "books.html").read_text(encoding="utf-8")
            records, _ = parse_books(html, "https://practice.example.invalid/catalogue/page-1.html")
        else:
            records = collect_live(args.pages)
        frame = clean_books(records)
        save_outputs(frame, output_dir, mode, len(records))
    except (requests.RequestException, ValueError, OSError, sqlite3.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Mode: {mode}")
    print(f"Saved {len(frame)} unique books. Duplicates removed: {len(records) - len(frame)}.")
    print(f"Output: {output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
