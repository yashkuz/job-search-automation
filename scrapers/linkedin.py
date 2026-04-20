import logging
import urllib.parse
from apify_client import ApifyClient
from config import APIFY_API_KEY, KEYWORDS, LOCATIONS_LINKEDIN

logger = logging.getLogger(__name__)

ACTOR_ID = "curious_coder/linkedin-jobs-scraper"


def _build_search_url(keyword: str, location: str) -> str:
    params = {
        "keywords": keyword,
        "location": location,
        "f_TPR": "r86400",  # past 24 hours
        "sortBy": "DD",     # date descending
    }
    return "https://www.linkedin.com/jobs/search/?" + urllib.parse.urlencode(params)


def scrape(max_results_per_keyword: int = 25) -> list[dict]:
    client = ApifyClient(APIFY_API_KEY)
    jobs = []

    for keyword in KEYWORDS:
        for location in LOCATIONS_LINKEDIN:
            logger.info(f"[LinkedIn] Searching: '{keyword}' in '{location}'")
            try:
                url = _build_search_url(keyword, location)
                run = client.actor(ACTOR_ID).call(
                    run_input={
                        "urls": [url],
                        "maxJobs": max_results_per_keyword,
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
    url = item.get("jobUrl") or item.get("url") or item.get("applyUrl") or ""
    description = item.get("description") or item.get("jobDescription") or ""
    posted_at = item.get("postedAt") or item.get("datePosted") or item.get("publishedAt") or ""

    if not title or not url:
        return None

    loc_lower = location.lower()
    if not (
        "mumbai" in loc_lower
        or "remote" in loc_lower
        or "work from home" in loc_lower
        or "wfh" in loc_lower
        or location == ""
    ):
        return None

    return {
        "title": title.strip(),
        "company": company.strip(),
        "location": location.strip(),
        "url": url.strip(),
        "description": description.strip()[:4000],
        "posted_at": posted_at,
        "source": "LinkedIn",
    }
