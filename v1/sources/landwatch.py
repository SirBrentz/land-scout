"""LandWatch scraper — parses the embedded window.serverState JSON."""
import json
import re

from config import COUNTIES, MAX_PAGES_PER_COUNTY
from geo import in_range, miles_from_home
from sources.base import get_page_html, PAGE_DELAY_MS

SOURCE = "landwatch"
BASE = "https://www.landwatch.com"

STATE_RE = re.compile(r'window\.serverState = "(.*?)";\s*</script>', re.S)


def county_url(county: str, page: int) -> str:
    slug = county.lower().replace(" ", "-")
    url = f"{BASE}/arkansas-land-for-sale/{slug}-county"
    if page > 1:
        url += f"/page-{page}"
    return url


def parse_server_state(html: str) -> dict:
    m = STATE_RE.search(html)
    if not m:
        raise RuntimeError("serverState not found in page")
    return json.loads(json.loads('"' + m.group(1) + '"'))


def normalize(p: dict) -> dict | None:
    price = p.get("price") or 0
    acres = p.get("acres") or 0
    lat, lon = p.get("latitude"), p.get("longitude")
    if not price or not acres:
        return None  # auction/no-price entries aren't trackable
    return {
        "source_id": str(p.get("lwPropertyId") or p.get("id")),
        "url": BASE + p.get("canonicalUrl", ""),
        "title": p.get("title") or p.get("imageAltTextDisplay") or "",
        "price": int(price),
        "acres": float(acres),
        "price_per_acre": round(price / acres, 2),
        "county": (p.get("county") or "").replace(" County", ""),
        "city": p.get("city") or "",
        "state": p.get("stateAbbreviation") or "AR",
        "lat": lat,
        "lon": lon,
        "miles_away": round(miles_from_home(lat, lon), 1) if lat and lon else None,
        "has_house": bool(p.get("hasHouse")),
        "types": p.get("propertyTypesLabel") or "",
    }


def scrape(ctx, log=print) -> list[dict]:
    results, seen = [], set()
    for county in COUNTIES:
        for page_num in range(1, MAX_PAGES_PER_COUNTY + 1):
            url = county_url(county, page_num)
            html = get_page_html(ctx, url, wait_ms=PAGE_DELAY_MS)
            state = parse_server_state(html)
            sr = state.get("searchPage", {}).get("searchResults", {})
            props = sr.get("propertyResults", [])
            if not props:
                break
            added = 0
            for p in props:
                n = normalize(p)
                if n is None or n["source_id"] in seen:
                    continue
                if not in_range(n["lat"], n["lon"]):
                    continue
                seen.add(n["source_id"])
                results.append(n)
                added += 1
            log(f"  landwatch {county} p{page_num}: {len(props)} listings, {added} kept")
            total = sr.get("totalCount", 0)
            if page_num * 25 >= total:
                break
    return results
