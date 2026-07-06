"""Score listings 0-100 against criteria.yaml rules."""
import yaml

from config import CRITERIA_PATH


def load_criteria() -> dict:
    with open(CRITERIA_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def score_listing(l: dict, c: dict) -> tuple[int, list[str]]:
    """Returns (score, reasons). Listings failing hard gates score 0."""
    reasons = []

    acres = l.get("acres") or 0
    price = l.get("price") or 0
    ppa = l.get("price_per_acre") or 0
    county = l.get("county") or ""
    text = f"{l.get('title', '')} {l.get('types', '')}".lower()

    # Hard gates
    if acres < c["min_acres"]:
        return 0, [f"under {c['min_acres']} acres"]
    if price > c["max_price"]:
        return 0, [f"over ${c['max_price']:,} budget ceiling"]
    if l.get("miles_away") is not None and l["miles_away"] > c["max_miles"]:
        return 0, ["outside radius"]
    for kw in c["red_flag_keywords"]:
        if kw.lower() in text:
            return 0, [f"red flag: {kw}"]

    score = 40
    reasons.append("passes acreage/budget/distance gates (+40)")

    # Price vs county benchmark: up to +30
    cap = c["max_ppa_by_county"].get(county, c["default_max_ppa"])
    if ppa and ppa <= cap:
        discount = (cap - ppa) / cap  # 0..1, deeper below cap = better deal
        pts = 15 + round(15 * min(discount * 2, 1))
        score += pts
        reasons.append(f"${ppa:,.0f}/ac vs {county or 'area'} cap ${cap:,} (+{pts})")
    elif ppa:
        reasons.append(f"${ppa:,.0f}/ac above {county or 'area'} cap ${cap:,} (+0)")

    # Acreage sweet spot: up to +15
    if acres >= 40:
        score += 15
        reasons.append("40+ acres (+15)")
    elif acres >= 20:
        score += 10
        reasons.append("20+ acres (+10)")
    else:
        score += 5
        reasons.append("10+ acres (+5)")

    # Bonus keywords: +5 each, max +15
    hits = [kw for kw in c["bonus_keywords"] if kw.lower() in text]
    if hits:
        pts = min(len(hits) * 5, 15)
        score += pts
        reasons.append(f"features: {', '.join(hits)} (+{pts})")

    return min(score, 100), reasons


def score_all(listings: list[dict], criteria: dict | None = None) -> list[dict]:
    c = criteria or load_criteria()
    out = []
    for l in listings:
        s, reasons = score_listing(l, c)
        out.append({**l, "score": s, "score_reasons": reasons})
    out.sort(key=lambda x: -x["score"])
    return out
