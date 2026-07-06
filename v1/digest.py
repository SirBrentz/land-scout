"""Build the HTML digest email from a run's results."""
from datetime import datetime

from config import DIGEST_DIR


def _card(l: dict, badge: str = "") -> str:
    ppa = l.get("price_per_acre")
    miles = l.get("miles_away")
    reasons = l.get("score_reasons") or []
    old = l.get("old_price")
    price_line = f"${l['price']:,}"
    if old:
        price_line = f"<s style='color:#999'>${old:,}</s> &rarr; <b>${l['price']:,}</b>"
    return f"""
    <div style="border:1px solid #ddd;border-radius:8px;padding:14px 16px;margin:10px 0;background:#fff">
      <div style="font-size:15px">
        {f'<span style="background:#166534;color:#fff;border-radius:4px;padding:2px 8px;font-size:12px;margin-right:8px">{badge}</span>' if badge else ''}
        <a href="{l['url']}" style="color:#1d4ed8;text-decoration:none;font-weight:600">
          {l.get('acres', '?')} acres — {l.get('city') or l.get('county', '')}, {l.get('county', '')} Co.
        </a>
      </div>
      <div style="margin-top:6px;font-size:14px;color:#111">
        {price_line}
        {f" &middot; ${ppa:,.0f}/acre" if ppa else ""}
        {f" &middot; {miles} mi away" if miles is not None else ""}
        {f" &middot; score <b>{l['score']}</b>" if 'score' in l else ""}
        &middot; via {l['source'] if 'source' in l else ''}
      </div>
      {f'<div style="margin-top:4px;font-size:12px;color:#666">{" · ".join(reasons)}</div>' if reasons else ''}
    </div>"""


def build_digest(new_scored: list[dict], drops: list[dict], stats: dict,
                 source_health: list[dict], alert_score: int) -> tuple[str, str]:
    """Returns (subject, html)."""
    today = datetime.now().strftime("%Y-%m-%d")
    top = [l for l in new_scored if l["score"] >= alert_score]
    rest = [l for l in new_scored if 0 < l["score"] < alert_score]
    skipped = len(new_scored) - len(top) - len(rest)

    subject = f"Land Scout {today}: {len(top)} top match{'es' if len(top) != 1 else ''}, {len(new_scored)} new, {len(drops)} price drop{'s' if len(drops) != 1 else ''}"

    sections = [f"""
    <div style="font-family:Segoe UI,Arial,sans-serif;max-width:680px;margin:0 auto;background:#f6f7f9;padding:20px">
    <h2 style="margin:0 0 4px">Land Scout — {today}</h2>
    <div style="color:#555;font-size:13px;margin-bottom:16px">Within ~45 mi of Greenbrier, AR</div>"""]

    if top:
        sections.append(f"<h3 style='margin:18px 0 4px'>&#127775; Top matches (score &ge; {alert_score})</h3>")
        sections += [_card(l, "TOP MATCH") for l in top]
    if drops:
        sections.append("<h3 style='margin:18px 0 4px'>&#128201; Price drops</h3>")
        sections += [_card(l) for l in drops]
    if rest:
        sections.append(f"<h3 style='margin:18px 0 4px'>New listings ({len(rest)})</h3>")
        sections += [_card(l) for l in rest[:25]]
        if len(rest) > 25:
            sections.append(f"<div style='color:#666;font-size:13px'>…and {len(rest) - 25} more lower-scoring new listings (in the local database).</div>")
    if skipped:
        sections.append(f"<div style='color:#666;font-size:13px;margin-top:8px'>{skipped} new listings scored 0 (failed acreage/budget/red-flag gates) — tracked but not shown.</div>")
    if not (top or drops or rest):
        sections.append("<p>No new listings or price drops today.</p>")

    if stats.get("by_county"):
        rows = "".join(
            f"<tr><td style='padding:3px 10px 3px 0'>{c}</td><td style='padding:3px 10px'>{v['n']}</td><td style='padding:3px 10px'>${v['median_ppa']:,.0f}</td></tr>"
            for c, v in stats["by_county"].items() if v["median_ppa"]
        )
        sections.append(f"""
        <h3 style='margin:18px 0 4px'>Market snapshot</h3>
        <table style="font-size:13px;border-collapse:collapse;background:#fff;border:1px solid #ddd;border-radius:8px;padding:8px">
        <tr style="color:#666"><th align="left" style="padding:3px 10px 3px 0">County</th><th align="left" style="padding:3px 10px">Tracked</th><th align="left" style="padding:3px 10px">Median $/acre</th></tr>
        {rows}</table>""")

    health = " &middot; ".join(
        f"{h['source']}: {'&#9989;' if h['status'] == 'ok' else '&#10060;'} {h['listings']}"
        for h in source_health
    )
    sections.append(f"<div style='margin-top:20px;color:#888;font-size:12px'>Sources — {health}</div></div>")

    html = "".join(sections)
    DIGEST_DIR.mkdir(exist_ok=True)
    (DIGEST_DIR / f"digest-{today}.html").write_text(html, encoding="utf-8")
    return subject, html
