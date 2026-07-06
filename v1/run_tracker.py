"""Daily orchestrator: scrape -> diff -> score -> digest -> email.

Usage:
  python run_tracker.py            # full run, sends email if .env configured
  python run_tracker.py --no-email # full run, digest saved locally only
"""
import sys
import traceback
from datetime import datetime

import db
import digest
import send_email
from config import LOG_DIR
from score import load_criteria, score_all
from sources import landsearch, landwatch
from sources.base import browser_context

SOURCES = [landwatch, landsearch]


def main(send: bool = True):
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"run-{datetime.now():%Y-%m-%d}.log"
    log_lines = []

    def log(msg):
        line = f"[{datetime.now():%H:%M:%S}] {msg}"
        print(line)
        log_lines.append(line)

    con = db.connect()
    criteria = load_criteria()
    all_new, all_drops, health = [], [], []

    with browser_context() as ctx:
        for src in SOURCES:
            name = src.SOURCE
            try:
                log(f"scraping {name}...")
                listings = src.scrape(ctx, log=log)
                diff = db.upsert_listings(con, name, listings)
                for l in diff["new"]:
                    l["source"] = name
                for l in diff["price_drops"]:
                    l["source"] = name
                all_new += diff["new"]
                all_drops += diff["price_drops"]
                db.record_run(con, name, "ok", len(listings))
                health.append({"source": name, "status": "ok", "listings": len(listings)})
                log(f"{name}: {len(listings)} listings, {len(diff['new'])} new, {len(diff['price_drops'])} drops")
            except Exception as e:
                db.record_run(con, name, "error", 0, str(e)[:300])
                health.append({"source": name, "status": "error", "listings": 0})
                log(f"{name} FAILED: {e}")
                log(traceback.format_exc(limit=3))

    seeding = con.execute("SELECT COUNT(*) c FROM runs WHERE status='ok'").fetchone()["c"] <= len(SOURCES)
    if seeding:
        log(f"first run: seeded DB with {len(all_new)} listings — skipping 'new' alerts")
        all_new = []

    new_scored = score_all(all_new, criteria)
    stats = db.market_stats(con)
    subject, html = digest.build_digest(new_scored, all_drops, stats, health, criteria["alert_score"])
    log(f"digest: {subject}")

    if send and (new_scored or all_drops or any(h["status"] == "error" for h in health)):
        try:
            sent = send_email.send(subject, html)
            log("email sent" if sent else "email skipped (no credentials)")
        except Exception as e:
            log(f"email FAILED: {e}")
    elif send:
        log("nothing to report — email skipped")

    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    con.close()


if __name__ == "__main__":
    main(send="--no-email" not in sys.argv)
