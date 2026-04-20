"""
Job Search Automation — Main Orchestrator
Runs daily at 9:30 AM IST via GitHub Actions.

Flow:
  1. Scrape LinkedIn + Indeed + Naukri in parallel
  2. Deduplicate by (title, company) hash
  3. Score every job with Claude AI
  4. Filter jobs with score >= MIN_FIT_SCORE
  5. Tailor resume bullets for qualifying jobs
  6. Append new qualifying jobs to Google Sheets
"""
import hashlib
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import MIN_FIT_SCORE
from scrapers import linkedin, indeed, naukri
from matcher import score_jobs
from resume_tailor import tailor_jobs
from sheets_output import append_to_sheet

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def _job_key(job: dict) -> str:
    """Dedup key: lowercase (title + company)."""
    raw = f"{job['title'].lower().strip()}|{job['company'].lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def scrape_all() -> list[dict]:
    """Run all three scrapers in parallel, deduplicate results."""
    scrapers = {
        "LinkedIn": linkedin.scrape,
        "Indeed":   indeed.scrape,
        "Naukri":   naukri.scrape,
    }
    all_jobs: list[dict] = []

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn): name for name, fn in scrapers.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results = future.result()
                logger.info(f"[Scraper/{name}] Returned {len(results)} jobs")
                all_jobs.extend(results)
            except Exception as e:
                logger.error(f"[Scraper/{name}] Failed: {e}")

    # Deduplicate
    seen: set[str] = set()
    unique: list[dict] = []
    for job in all_jobs:
        key = _job_key(job)
        if key not in seen:
            seen.add(key)
            unique.append(job)

    logger.info(f"[Scraper] Total unique jobs after dedup: {len(unique)}")
    return unique


def main() -> None:
    logger.info("═" * 50)
    logger.info("Job Search Automation — Starting run")
    logger.info("═" * 50)

    # Step 1: Scrape
    jobs = scrape_all()
    total_scraped = len(jobs)

    if not jobs:
        logger.warning("No jobs found across all boards. Nothing to append.")
        append_to_sheet([], total_scraped=0)
        return

    # Step 2: Score all jobs
    logger.info(f"[Main] Scoring {total_scraped} jobs...")
    jobs = score_jobs(jobs)

    # Step 3: Filter qualifying jobs
    qualifying = [j for j in jobs if j.get("score", 0) >= MIN_FIT_SCORE]
    logger.info(f"[Main] {len(qualifying)} jobs scored {MIN_FIT_SCORE}+/10")

    # Step 4: Tailor resume for qualifying jobs
    if qualifying:
        logger.info(f"[Main] Tailoring resume for {len(qualifying)} qualifying jobs...")
        qualifying = tailor_jobs(qualifying)

    # Merge tailored qualifying jobs back (rest stay un-tailored)
    tailored_keys = {_job_key(j): j for j in qualifying}
    final_jobs = []
    for job in jobs:
        key = _job_key(job)
        final_jobs.append(tailored_keys.get(key, job))

    # Step 5: Append to Google Sheets
    logger.info("[Main] Appending qualifying jobs to Google Sheets...")
    append_to_sheet(final_jobs, total_scraped=total_scraped)

    logger.info("═" * 50)
    logger.info(
        f"Run complete. Scraped: {total_scraped} | "
        f"Qualifying: {len(qualifying)} | Sheets: appended"
    )
    logger.info("═" * 50)


if __name__ == "__main__":
    main()
