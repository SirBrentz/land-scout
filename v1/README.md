# land-scout v1 — tracker

Daily scrape of LandWatch + LandSearch for land within ~45 mi of Greenbrier, AR,
scored against `criteria.yaml`, with an email digest of new matches and price drops.

## Setup (one-time)
1. `pip install -r requirements.txt` and `python -m playwright install chromium`
   (real Chrome must also be installed — scrapers use `channel="chrome"` headed
   off-screen because both sites block headless Chromium).
2. Copy `.env.example` → `.env`, add a Gmail app password.
3. `python run_tracker.py --no-email` — first run seeds the database (no alerts).
4. `powershell -ExecutionPolicy Bypass -File register-task.ps1` — daily 7 AM task.

## Files
- `run_tracker.py` — orchestrator (scrape → diff → score → digest → email)
- `sources/landwatch.py` — parses `window.serverState` JSON (includes $/acre + price-change data)
- `sources/landsearch.py` — parses listing card DOM
- `criteria.yaml` — all tunable alert rules (acreage floor, $/acre caps per county, keywords)
- `db.py` — SQLite (`listings.db`), new/price-drop detection
- `digest.py` — HTML email builder; copies archived to `../digests/`
- `geo.py` — 45-mile haversine filter from Greenbrier (35.234, -92.387)

## Behavior notes
- Email is only sent when there's something to report (new match, price drop, or a source erroring).
- One source failing doesn't kill the run; digest footer shows per-source health.
- Listings scoring 0 (fail hard gates) are still stored — history is useful for market stats.
