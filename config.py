import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
APIFY_API_KEY       = os.environ["APIFY_API_KEY"]
ANTHROPIC_API_KEY   = os.environ["ANTHROPIC_API_KEY"]
GOOGLE_SHEET_ID             = os.environ["GOOGLE_SHEET_ID"]
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]

# ── Scoring ───────────────────────────────────────────────────────────────────
MIN_FIT_SCORE = int(os.environ.get("MIN_FIT_SCORE", "7"))

# ── Search Parameters ─────────────────────────────────────────────────────────
KEYWORDS = [
    "Head of Operations",
    "VP Operations",
    "Supply Chain Manager",
    "Senior Manager Supply Chain",
    "Director Supply Chain",
    "Program Manager Operations",
    "Head of Supply Chain",
    "Operations Lead",
    "Central Operations Manager",
    "Supply Chain Lead",
    "GM Operations",
]

# Locations: Mumbai on-site/hybrid only + India-wide remote
LOCATIONS_LINKEDIN = ["Mumbai, Maharashtra, India"]
LOCATIONS_INDEED   = ["Mumbai", "Remote"]
LOCATIONS_NAUKRI   = ["Mumbai", "Work from Home"]

# Claude model for bulk scoring (cheap + fast)
CLAUDE_SCORING_MODEL  = "claude-haiku-4-5-20251001"
# Claude model for resume tailoring (slightly more capable)
CLAUDE_TAILOR_MODEL   = "claude-haiku-4-5-20251001"
