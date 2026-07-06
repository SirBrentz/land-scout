# land-scout

Land market research + automated listing tracker for buying land within ~1 hour of Greenbrier, Arkansas.

**📄 Market report (GitHub Pages):** https://sirbrentz.github.io/land-scout/

- `research/` — market-education reports (price benchmarks, due diligence, buying mechanics, derived alert criteria)
- `v1/` — the tracker: daily Playwright scrape of land-listing sites → SQLite → scored against `criteria.yaml` → email digest of new matches and price drops

Private project. See `commits.txt` for change history.
