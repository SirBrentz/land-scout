"""Shared configuration for land-scout."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent

DB_PATH = ROOT / "listings.db"
CRITERIA_PATH = ROOT / "criteria.yaml"
DIGEST_DIR = PROJECT / "digests"
LOG_DIR = PROJECT / "logs"
ENV_PATH = ROOT / ".env"

# Home point: Greenbrier, AR
HOME_LAT = 35.234
HOME_LON = -92.387
RADIUS_MILES = 45.0  # straight-line proxy for ~1 hour drive

# Counties within roughly 1 hour of Greenbrier
COUNTIES = [
    "Faulkner",
    "Conway",
    "Van Buren",
    "Cleburne",
    "White",
    "Perry",
    "Pulaski",
]

MAX_PAGES_PER_COUNTY = 8  # per source; DB dedupe makes deeper paging unnecessary daily


def load_env() -> dict:
    """Tiny .env parser (KEY=VALUE lines, # comments)."""
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env
