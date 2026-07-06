"""SQLite store for listings; detects new / price-dropped / stale between runs."""
import sqlite3
from datetime import datetime, timezone

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    source        TEXT NOT NULL,
    source_id     TEXT NOT NULL,
    url           TEXT,
    title         TEXT,
    price         INTEGER,
    acres         REAL,
    price_per_acre REAL,
    county        TEXT,
    city          TEXT,
    state         TEXT,
    lat           REAL,
    lon           REAL,
    miles_away    REAL,
    has_house     INTEGER,
    types         TEXT,
    first_seen    TEXT,
    last_seen     TEXT,
    prev_price    INTEGER,
    price_changed TEXT,
    PRIMARY KEY (source, source_id)
);
CREATE TABLE IF NOT EXISTS runs (
    run_at   TEXT,
    source   TEXT,
    status   TEXT,
    listings INTEGER,
    note     TEXT
);
"""


def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def upsert_listings(con, source: str, listings: list[dict]) -> dict:
    """Insert/update scraped listings. Returns {'new': [...], 'price_drops': [...]}."""
    ts = now_iso()
    new, drops = [], []
    for l in listings:
        row = con.execute(
            "SELECT price FROM listings WHERE source=? AND source_id=?",
            (source, l["source_id"]),
        ).fetchone()
        if row is None:
            con.execute(
                """INSERT INTO listings (source, source_id, url, title, price, acres,
                   price_per_acre, county, city, state, lat, lon, miles_away, has_house,
                   types, first_seen, last_seen)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (source, l["source_id"], l.get("url"), l.get("title"), l.get("price"),
                 l.get("acres"), l.get("price_per_acre"), l.get("county"), l.get("city"),
                 l.get("state"), l.get("lat"), l.get("lon"), l.get("miles_away"),
                 int(bool(l.get("has_house"))), l.get("types"), ts, ts),
            )
            new.append(l)
        else:
            old_price = row["price"]
            if l.get("price") and old_price and l["price"] < old_price:
                drops.append({**l, "old_price": old_price})
                con.execute(
                    """UPDATE listings SET price=?, prev_price=?, price_changed=?,
                       last_seen=?, url=?, title=?, acres=?, price_per_acre=?, miles_away=?
                       WHERE source=? AND source_id=?""",
                    (l["price"], old_price, ts, ts, l.get("url"), l.get("title"),
                     l.get("acres"), l.get("price_per_acre"), l.get("miles_away"),
                     source, l["source_id"]),
                )
            else:
                con.execute(
                    """UPDATE listings SET last_seen=?, price=COALESCE(?, price),
                       acres=COALESCE(?, acres), price_per_acre=COALESCE(?, price_per_acre)
                       WHERE source=? AND source_id=?""",
                    (ts, l.get("price"), l.get("acres"), l.get("price_per_acre"),
                     source, l["source_id"]),
                )
    con.commit()
    return {"new": new, "price_drops": drops}


def record_run(con, source: str, status: str, count: int, note: str = ""):
    con.execute(
        "INSERT INTO runs (run_at, source, status, listings, note) VALUES (?,?,?,?,?)",
        (now_iso(), source, status, count, note),
    )
    con.commit()


def market_stats(con) -> dict:
    """Median $/acre overall and per county for currently-tracked listings."""
    def median(vals):
        vals = sorted(v for v in vals if v)
        if not vals:
            return None
        mid = len(vals) // 2
        return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2

    rows = con.execute(
        "SELECT county, price_per_acre FROM listings WHERE price_per_acre > 0 AND acres >= 10"
    ).fetchall()
    by_county = {}
    for r in rows:
        by_county.setdefault(r["county"] or "?", []).append(r["price_per_acre"])
    return {
        "total_tracked": len(rows),
        "median_ppa": median([r["price_per_acre"] for r in rows]),
        "by_county": {c: {"n": len(v), "median_ppa": median(v)} for c, v in sorted(by_county.items())},
    }
