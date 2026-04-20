"""
LinkedIn job scraper using Apify actor: apify/linkedin-jobs-scraper
Returns jobs posted in the last 24 hours matching Supply Chain / Operations keywords.
"""
import logging
from apify_client import ApifyClient
from config import APIFY_API_KEY, KEYWORDS, LOCATIONS_LINKEDIN

logger = logging.getLogger(__name__)

# Apify actor for LinkedIn Jobs
ACTOR_ID = "curious_coder/linkedin-jobs-scraper"


def scrape(max_results_per_keyword: int = 25) -> list[dict]:
    """
    Scrape LinkedIn for matching jobs posted in the last 24 hours.
    Returns a list of job dicts with keys:
      title, company, location, url, description, posted_at, source
    """
    client = ApifyClient(APIFY_API_KEY)
    jobs = []

    for keyword in KEYWORDS:
        for location in LOCATIONS_LINKEDIN:
            logger.info(f"[LinkedIn] Searching: '{keyword}' in '{location}'")
            try:
                run = client.actor(ACTOR_ID).call(
                    run_input={
                        "searchTerms": [keyword],
                        "location": location,
                        "dateSincePosted": "past24Hours",
                        "maxResults": max_results_per_keyword,
                        "proxy": {"useApifyProxy": True},
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
                logger.warning(f"[LinkedIn] Error for '{keyword}' / '{location}': {e}")

    logger.info(f"[LinkedIn] Total raw results: {len(jobs)}")
    return jobs


def _normalize(item: dict) -> dict | None:
    title = item.get("title") or item.get("jobTitle") or ""
    company = item.get("companyName") or item.get("company") or ""
    location = item.get("location") or item.get("jobLocation") or ""
    url = item.get("jobUrl") or item.get("url") or ""
    description = item.get("description") or item.get("jobDescription") or ""
    posted_at = item.get("postedAt") or item.get("datePosted") or ""

    if not title or not url:
        return None

    # Filter: include Mumbai on-site, Mumbai hybrid, or remote roles
    loc_lower = location.lower()
    is_relevant_location = (
        "mumbai" in loc_lower
        or "remote" in loc_lower
        or "work from home" in loc_lower
        or "wfh" in loc_lower
        or location == ""  # unknown location — include and let scorer decide
    )
    if not is_relevant_location:
        return None

    return {
        "title": title.strip(),
        "company": company.strip(),
        "location": location.strip(),
        "url": url.strip(),
        "description": description.strip()[:4000],  # cap to keep tokens low
        "posted_at": posted_at,
        "source": "LinkedIn",
    }
