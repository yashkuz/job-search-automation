import logging
import urllib.parse
import urllib.request
import json
from apify_client import ApifyClient
from config import APIFY_API_KEY, KEYWORDS, LOCATIONS_NAUKRI

logger = logging.getLogger(__name__)

ACTOR_ID = "bebity/naukri-jobs-scraper"

NAUKRI_API_URL = "https://www.naukri.com/jobapi/v3/search"
NAUKRI_HEADERS = {
    "appid": "109",
    "systemid": "109",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.naukri.com/",
}


def scrape(max_results_per_keyword: int = 20) -> list[dict]:
    jobs = _scrape_via_apify(max_results_per_keyword)
    if not jobs:
        logger.info("[Naukri] Apify returned 0 results — trying direct API fallback")
        jobs = _scrape_via_direct_api(max_results_per_keyword)
    logger.info(f"[Naukri] Total raw results: {len(jobs)}")
    return jobs


def _scrape_via_apify(max_results_per_keyword: int) -> list[dict]:
    client = ApifyClient(APIFY_API_KEY)
    jobs = []
    for keyword in KEYWORDS:
        for location in LOCATIONS_NAUKRI:
            logger.info(f"[Naukri/Apify] Searching: '{keyword}' in '{location}'")
            try:
                run = client.actor(ACTOR_ID).call(
                    run_input={
                        "keyword": keyword,
                        "location": location,
                        "freshness": "1",
                        "maxItems": max_results_per_keyword,
                    },
                    timeout_secs=120,
                )
                dataset_id = run.get("defaultDatasetId")
                if not dataset_id:
                    continue
                for item in client.dataset(dataset_id).iterate_items():
                    job = _normalize_apify(item)
                    if job:
                        jobs.append(job)
            except Exception as e:
                logger.warning(f"[Naukri/Apify] Error for '{keyword}': {e}")
    return jobs


def _normalize_apify(item: dict) -> dict | None:
    title = item.get("title") or item.get("jobTitle") or ""
    company = item.get("companyName") or item.get("company") or ""
    location = item.get("location") or item.get("jobLocation") or ""
    url = item.get("jdURL") or item.get("url") or ""
    description = item.get("jobDescription") or item.get("description") or ""
    posted_at = item.get("createdDate") or item.get("postedAt") or ""

    if not title or not url:
        return None
    if not _is_relevant_location(location):
        return None

    return {
        "title": title.strip(),
        "company": company.strip(),
        "location": location.strip(),
        "url": url.strip(),
        "description": description.strip()[:4000],
        "posted_at": posted_at,
        "source": "Naukri",
    }


def _scrape_via_direct_api(max_results_per_keyword: int) -> list[dict]:
    jobs = []
    for keyword in KEYWORDS[:5]:
        for location in LOCATIONS_NAUKRI:
            try:
                params = urllib.parse.urlencode({
                    "noOfResults": max_results_per_keyword,
                    "urlType": "search_by_keyword",
                    "searchType": "adv",
                    "keyword": keyword,
                    "location": location,
                    "jobAge": 1,
                    "src": "jobsearchDesk",
                    "latLong": "",
                })
                req = urllib.request.Request(
                    f"{NAUKRI_API_URL}?{params}",
                    headers=NAUKRI_HEADERS,
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode())

                for item in data.get("jobDetails", []):
                    job = _normalize_direct(item)
                    if job:
                        jobs.append(job)
            except Exception as e:
                logger.warning(f"[Naukri/Direct] Error for '{keyword}': {e}")
    return jobs


def _normalize_direct(item: dict) -> dict | None:
    title = item.get("title") or ""
    company = (item.get("companyName") or {}).get("label") or ""
    location_list = item.get("placeholders", [])
    location = next(
        (p.get("label", "") for p in location_list if p.get("type") == "location"), ""
    )
    jd_url = item.get("jdURL") or ""
    url = f"https://www.naukri.com{jd_url}" if jd_url.startswith("/") else jd_url
    description = item.get("jobDescription") or ""
    posted_at = item.get("createdDate") or ""

    if not title or not url:
        return None
    if not _is_relevant_location(location):
        return None

    return {
        "title": title.strip(),
        "company": company.strip(),
        "location": location.strip(),
        "url": url.strip(),
        "description": description.strip()[:4000],
        "posted_at": posted_at,
        "source": "Naukri",
    }


def _is_relevant_location(location: str) -> bool:
    loc_lower = location.lower()
    return (
        "mumbai" in loc_lower
        or "remote" in loc_lower
        or "work from home" in loc_lower
        or "wfh" in loc_lower
        or location.strip() == ""
    )
