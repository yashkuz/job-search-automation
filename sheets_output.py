import json
import logging
from datetime import datetime, timezone, timedelta

import gspread
from google.oauth2.service_account import Credentials

from config import GOOGLE_SHEET_ID, GOOGLE_SERVICE_ACCOUNT_JSON, MIN_FIT_SCORE

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

HEADERS = [
    "Date Added",       # A
    "Title",            # B
    "Company",          # C
    "Location",         # D
    "Score (/10)",      # E
    "Reasoning",        # F
    "Key Matches",      # G
    "Red Flags",        # H
    "Tailored Bullets", # I
    "URL",              # J  ← dedup key (col_values index 10)
    "Source",           # K
    "Posted At",        # L
]

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_worksheet() -> gspread.Worksheet:
    info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(GOOGLE_SHEET_ID).sheet1


def _ensure_headers(ws: gspread.Worksheet) -> None:
    existing = ws.get_all_values()
    if not existing or existing[0] != HEADERS:
        ws.update("A1", [HEADERS])


def _build_row(job: dict, date_str: str) -> list:
    return [
        date_str,
        job.get("title", ""),
        job.get("company", ""),
        job.get("location", ""),
        job.get("score", ""),
        job.get("reasoning", ""),
        ", ".join(job.get("key_matches", [])),
        ", ".join(job.get("red_flags", [])),
        job.get("tailored_bullets", ""),
        job.get("url", ""),
        job.get("source", ""),
        job.get("posted_at", ""),
    ]


def append_to_sheet(jobs: list[dict], total_scraped: int) -> None:
    qualifying = [j for j in jobs if j.get("score", 0) >= MIN_FIT_SCORE]
    if not qualifying:
        logger.info(
            f"[Sheets] No qualifying jobs (score {MIN_FIT_SCORE}+). "
            f"Total scraped: {total_scraped}."
        )
        return

    try:
        ws = _get_worksheet()
        _ensure_headers(ws)

        existing_urls: set[str] = set(ws.col_values(10))  # column J, 1-based

        date_str = datetime.now(IST).strftime("%Y-%m-%d")
        rows_to_add = []
        skipped = 0

        for job in qualifying:
            url = job.get("url", "")
            if url and url in existing_urls:
                skipped += 1
                continue
            rows_to_add.append(_build_row(job, date_str))

        if rows_to_add:
            ws.append_rows(rows_to_add, value_input_option="USER_ENTERED")
            logger.info(
                f"[Sheets] Appended {len(rows_to_add)} new rows. "
                f"Skipped {skipped} duplicates. Total scraped: {total_scraped}."
            )
        else:
            logger.info(
                f"[Sheets] All {skipped} qualifying jobs already in sheet."
            )

    except Exception as e:
        logger.error(f"[Sheets] Failed to write to Google Sheet: {e}", exc_info=True)
