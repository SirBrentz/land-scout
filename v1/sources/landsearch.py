"""LandSearch scraper — parses listing card markup from search result pages."""
import html as html_mod
import json
import re

from config import COUNTIES, MAX_PAGES_PER_COUNTY
from geo import in_range, miles_from_home
from sources.base import get_page_html, PAGE_DELAY_MS

SOURCE = "landsearch"
BASE = "https://www.landsearch.com"

ARTICLE_RE = re.compile(r'<article class="preview \$property".*?</article>', re.S)
CONTEXT_RE = re.compile(r'data-context="([^"]+)"')
ID_RE = re.compile(r'data-id="(\d+)"')
LINK_RE = re.compile(r'href="(/properties/[^"]+)"')
TITLE_RE = re.compile(
    r'preview__title">\$?([\d,]+)<span class="preview__size">([\d.,]+)\s*acres?</span>'
)
COUNTY_RE = re.compile(r'preview__subterritory">([^<]+)<')
LOCATION_RE = re.compile(r'preview__location[^>]*>([^<]+)<')


def county_url(county: str, page: int) -> str:
    slug = county.lower().replace(" ", "-")
    url = f"{BASE}/properties/{slug}-county-ar"
    if page > 1:
        url += f"/p{page}"
    return url


def parse_card(card: str) -> dict | None:
    m_id = ID_RE.search(card)
    m_title = TITLE_RE.search(card)
    m_link = LINK_RE.search(card)
    if not (m_id and m_title and m_link):
        return None
    price = int(m_title.group(1).replace(",", ""))
    acres = float(m_title.group(2).replace(",", ""))
    if not price or not acres:
        return None

    lat = lon = None
    m_ctx = CONTEXT_RE.search(card)
    if m_ctx:
        try:
            ctx_data = json.loads(html_mod.unescape(m_ctx.group(1)))
            center = ctx_data.get("center") or [None, None]
            lon, lat = center[0], center[1]
        except (ValueError, IndexError):
            pass

    m_county = COUNTY_RE.search(card)
    m_loc = LOCATION_RE.search(card)
    city = state = ""
    if m_loc:
        loc = m_loc.group(1).strip()  # "Greenbrier, AR 72058"
        parts = loc.rsplit(",", 1)
        city = parts[0].strip()
        state = parts[1].strip().split()[0] if len(parts) > 1 else ""

    return {
        "source_id": m_id.group(1),
        "url": BASE + m_link.group(1),
        "title": city or m_link.group(1),
        "price": price,
        "acres": acres,
        "price_per_acre": round(price / acres, 2),
        "county": (m_county.group(1).replace(" County", "").strip() if m_county else ""),
        "city": city,
        "state": state or "AR",
        "lat": lat,
        "lon": lon,
        "miles_away": round(miles_from_home(lat, lon), 1) if lat and lon else None,
        "has_house": False,  # cards don't say; LandSearch is land-focused
        "types": "",
    }


def scrape(ctx, log=print) -> list[dict]:
    results, seen = [], set()
    for county in COUNTIES:
        prev_first_id = None
        for page_num in range(1, MAX_PAGES_PER_COUNTY + 1):
            url = county_url(county, page_num)
            try:
                html = get_page_html(ctx, url, wait_ms=PAGE_DELAY_MS)
            except RuntimeError:
                if page_num == 1:
                    raise  # first page blocked means the source is down
                break  # past the last page can 404/redirect — treat as end
            cards = ARTICLE_RE.findall(html)
            if not cards:
                break
            first_id = ID_RE.search(cards[0])
            first_id = first_id.group(1) if first_id else None
            if first_id and first_id == prev_first_id:
                break  # site served the same page again — end of pagination
            prev_first_id = first_id
            added = 0
            for card in cards:
                n = parse_card(card)
                if n is None or n["source_id"] in seen:
                    continue
                if not in_range(n["lat"], n["lon"]):
                    continue
                seen.add(n["source_id"])
                results.append(n)
                added += 1
            log(f"  landsearch {county} p{page_num}: {len(cards)} cards, {added} kept")
    return results
