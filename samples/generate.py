"""Generate a synthetic, Superstore-shaped sample dataset.

The lab needs a realistic analytical schema (orders / returns / people) to run
text-to-SQL evaluation against, but ships no third-party or private data. This
script deterministically synthesises neutral demo rows: no real people, no real
companies, no real places. Run it once to produce CSVs under ``data/``.

    python samples/generate.py --rows 2000 --out data

Bring your own data: replace the generated CSVs with your own export that has
the same columns, or point the warehouse loader at a different directory.
"""

from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

CATEGORIES = {
    "Furniture": ["Bookcases", "Chairs", "Tables"],
    "Office Supplies": ["Binders", "Paper", "Storage"],
    "Technology": ["Phones", "Accessories", "Machines"],
}
SEGMENTS = ["Consumer", "Corporate", "Home Office"]
REGIONS = ["Central", "East", "South", "West"]
SHIP_MODES = ["Standard Class", "Second Class", "First Class", "Same Day"]
# Neutral, generated place/person labels (not real).
COUNTRIES = ["Demoland", "Sampleton", "Testovia"]
PEOPLE = {"Central": "Alex Rivera", "East": "Sam Okoro", "South": "Lee Nguyen", "West": "Robin Diaz"}


def _rows(n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    start = date(2022, 1, 1)
    rows = []
    for i in range(n):
        cat = rng.choice(list(CATEGORIES))
        sub = rng.choice(CATEGORIES[cat])
        order_date = start + timedelta(days=rng.randint(0, 1000))
        ship_date = order_date + timedelta(days=rng.randint(1, 7))
        cust_id = f"CU-{rng.randint(1000, 1099)}"
        sales = round(rng.uniform(10, 2000), 2)
        quantity = rng.randint(1, 9)
        discount = rng.choice([0.0, 0.1, 0.15, 0.2, 0.3])
        # Profit loosely correlated with sales and eroded by discount.
        profit = round(sales * rng.uniform(-0.1, 0.4) - sales * discount * 0.5, 2)
        rows.append(
            {
                "order_id": f"OR-{2022 + i % 3}-{i:06d}",
                "order_date": order_date.isoformat(),
                "ship_date": ship_date.isoformat(),
                "ship_mode": rng.choice(SHIP_MODES),
                "customer_id": cust_id,
                "customer_name": f"Customer {cust_id[-4:]}",
                "segment": rng.choice(SEGMENTS),
                "country": rng.choice(COUNTRIES),
                "region": rng.choice(REGIONS),
                "category": cat,
                "sub_category": sub,
                "product_name": f"{sub} item {rng.randint(1, 50)}",
                "sales": sales,
                "quantity": quantity,
                "discount": discount,
                "profit": profit,
            }
        )
    return rows


def write_dataset(out_dir: Path, rows: int, seed: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    orders = _rows(rows, seed)

    with (out_dir / "orders.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(orders[0].keys()))
        w.writeheader()
        w.writerows(orders)

    rng = random.Random(seed + 1)
    returned = {o["order_id"] for o in orders if rng.random() < 0.08}
    with (out_dir / "returns.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["order_id", "returned"])
        for o in orders:
            w.writerow([o["order_id"], "Yes" if o["order_id"] in returned else "No"])

    with (out_dir / "people.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["region", "person"])
        for region, person in PEOPLE.items():
            w.writerow([region, person])

    print(f"Wrote {len(orders)} orders, {len(returned)} returns, {len(PEOPLE)} people to {out_dir}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rows", type=int, default=2000, help="number of order rows")
    ap.add_argument("--seed", type=int, default=42, help="deterministic seed")
    ap.add_argument("--out", type=Path, default=Path("data"), help="output directory")
    args = ap.parse_args()
    write_dataset(args.out, args.rows, args.seed)


if __name__ == "__main__":
    main()
