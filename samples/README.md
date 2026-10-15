# Sample data

The lab ships no third-party or private data. `generate.py` synthesises a
Superstore-shaped dataset (`orders`, `returns`, `people`) with neutral, made-up
values: no real people, companies, or places.

```bash
python samples/generate.py --rows 2000 --out data
```

This writes `data/orders.csv`, `data/returns.csv`, and `data/people.csv`.

## Bring your own data

Replace the generated CSVs with your own export that uses the same column names,
or point the loaders at a different directory with `DATA_DIR=/path`. The gold
question set in `textsql/gold.py` assumes the Superstore schema; adjust it to
match if your columns differ.
