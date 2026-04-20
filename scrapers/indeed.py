import logging
import re
from apify_client import ApifyClient
from config import APIFY_API_KEY, KEYWORDS, LOCATIONS_INDEED

logger = logging.getLogger(__name__)

ACTOR_ID = "misceres/indeed-scraper"


def scrape(max_results_per_keyword: int = 20) -> list[dict]:
    """
    Scrape Indeed India for matching jobs posted in the last 24 hours.
    Returns normalized job dicts.
    """
    client = ApifyClient(APIFY_API_KEY)
    jobs = []

    for keyword in KEYWORDS:
        for location in LOCATIONS_INDEED:
            logger.info(f"[Indeed] Searching: '{keyword}' in '{location}'")
            try:
                run = client.actor(ACTOR_ID).call(
                    run_input={
                        "position": keyword,
                        "country": "IN",
                        "location": location,
                        "maxItems": max_results_per_keyword,
                        "parseCompanyDetails": False,
                        "saveOnlyUniqueItems": True,
                        "fromAge": 1,  # last 24 hours
                    },
                    timeout_secs=120,
                )
                dataset_id = run.get("defaultDatasetId")
                if not dataset_id:
                    continue
                for item in client.dataset(dataset_id).iterate_items():
                    job = _normalize(item)
                    if job:
                        jobs.append(job)
            except Exception as e:
                logger.warning(f"[Indeed] Error for '{keyword}' / '{location}': {e}")

    logger.info(f"[Indeed] Total raw results: {len(jobs)}")
    return jobs


def _is_recent(posted_at: str) -> bool:
    if not posted_at:
        return True
    p = posted_at.lower()
    if any(x in p for x in ("just posted", "today", "1 day")):
        return True
    match = re.search(r'(\d+)\s*day', p)
    if match and int(match.group(1)) > 1:
        return False
    if any(x in p for x in ("week", "month", "year")):
        return False
    return True


def _normalize(item: dict) -> dict | None:
    title = item.get("positionName") or item.get("title") or ""
    company = item.get("company") or ""
    location = item.get("location") or ""
    url = item.get("url") or item.get("externalApplyLink") or ""
    description = item.get("description") or item.get("summary") or ""
    posted_at = item.get("postedAt") or item.get("postingDate") or ""

    if not title or not url:
        return None

    if not _is_recent(posted_at):
        return None

    loc_lower = location.lower()
    is_relevant_location = (
        "mumbai" in loc_lower
        or "remote" in loc_lower
        or "work from home" in loc_lower
        or "wfh" in loc_lower
        or location == ""
    )
    if not is_relevant_location:
        return None

    return {
        "title": title.strip(),
        "company": company.strip(),
        "location": location.strip(),
        "url": url.strip(),
        "description": description.strip()[:4000],
        "posted_at": posted_at,
        "source": "Indeed",
    }
