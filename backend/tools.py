"""Database tools kept separate from agent prompting and UI rendering."""

from pathlib import Path
import sqlite3
from models import ProductCard, ProductInfo, StockLine, StockLookup

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "campus_customs.db"


def search_products(query: str, limit: int = 4) -> list[ProductCard]:
    terms = [term.rstrip("s").strip(".,?!") for term in query.lower().split() if len(term) > 2]
    limit = min(max(limit, 1), 8)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute("SELECT product_id, name, price, description, image_file_path, colors, search_tags, garment_type FROM catalogue ORDER BY name").fetchall()
        scored = []
        for row in rows:
            haystack = " ".join(str(row[key]) for key in ("name", "description", "colors", "search_tags", "garment_type")).lower()
            name = row["name"].lower()
            score = sum(term in haystack for term in terms) + sum(3 for term in terms if term in name)
            if score or not terms:
                scored.append((score, row))
        scored.sort(key=lambda item: (-item[0], item[1]["name"]))
        return [ProductCard(product_id=row["product_id"], name=row["name"], price=row["price"], image_url=f"/images/{Path(row['image_file_path']).name}", description=row["description"]) for _, row in scored[:limit]]
    finally:
        connection.close()


def inventory_for(product_id: str) -> list[dict[str, int | str]]:
    connection = sqlite3.connect(DB_PATH)
    try:
        return [{"size": row[0], "quantity": row[1]} for row in connection.execute("SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY size", (product_id,))]
    finally:
        connection.close()


def product_info(product_id: str) -> ProductInfo | None:
    """Return authoritative catalogue description and price for one product."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute("SELECT product_id, name, description, price, colors, garment_type FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        return ProductInfo(**dict(row)) if row else None
    finally:
        connection.close()


def product_by_id(product_id: str) -> ProductInfo | None:
    """Resolve the exact product in page context before broader searching."""
    return product_info(product_id)


def stock_lookup(product_id: str, size: str | None = None) -> StockLookup | None:
    """Return actual stock, optionally narrowed to the requested size."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        product = connection.execute("SELECT name FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if not product:
            return None
        rows = connection.execute("SELECT size, quantity FROM inventory WHERE product_id = ? AND (? IS NULL OR lower(size) = lower(?)) ORDER BY size", (product_id, size, size)).fetchall()
        return StockLookup(product_id=product_id, product_name=product["name"], requested_size=size, lines=[StockLine(size=row["size"], quantity=row["quantity"], in_stock=row["quantity"] > 0) for row in rows])
    finally:
        connection.close()
