"""
Job fit scorer using Claude Haiku.
For each job, returns a score (1–10), reasoning, key matches, and red flags.
Uses prompt caching on the resume text to minimise API cost.
"""
import json
import logging
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_SCORING_MODEL
from resume_data import RESUME_TEXT

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = (
    "You are an expert senior recruiter in India specialising in Supply Chain, "
    "Logistics, and Operations roles. Given a candidate's resume and a job description, "
    "evaluate the fit and respond ONLY with valid JSON in this exact format:\n"
    '{"score": <int 1-10>, "reasoning": "<2 sentences>", '
    '"key_matches": ["<match 1>", "<match 2>", "<match 3>"], '
    '"red_flags": ["<flag>"] }\n'
    "Score guide: 9-10 = near-perfect, 7-8 = strong, 5-6 = moderate, 1-4 = weak.\n"
    "Be strict. Only give 8+ if the role is genuinely a great match for the candidate's "
    "seniority, domain expertise, and location constraints."
)


def score_job(job: dict) -> dict:
    """
    Score a single job against Yash's resume.
    Augments the job dict with: score, reasoning, key_matches, red_flags.
    Returns the augmented dict (score=-1 on error).
    """
    prompt = (
        f"CANDIDATE RESUME:\n{RESUME_TEXT}\n\n"
        f"JOB TO EVALUATE:\n"
        f"Title: {job['title']}\n"
        f"Company: {job['company']}\n"
        f"Location: {job['location']}\n"
        f"Source: {job['source']}\n"
        f"Description:\n{job['description']}"
    )

    try:
        response = _client.messages.create(
            model=CLAUDE_SCORING_MODEL,
            max_tokens=512,
            system=[
                # Cache the system prompt — it's identical for every call
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        job["score"]       = int(result.get("score", 0))
        job["reasoning"]   = result.get("reasoning", "")
        job["key_matches"] = result.get("key_matches", [])
        job["red_flags"]   = result.get("red_flags", [])
    except Exception as e:
        logger.warning(f"[Matcher] Error scoring '{job['title']}' @ '{job['company']}': {e}")
        job["score"]       = -1
        job["reasoning"]   = ""
        job["key_matches"] = []
        job["red_flags"]   = []

    return job


def score_jobs(jobs: list[dict]) -> list[dict]:
    """Score all jobs. Returns list sorted by score descending."""
    scored = []
    for i, job in enumerate(jobs):
        logger.info(f"[Matcher] Scoring {i+1}/{len(jobs)}: {job['title']} @ {job['company']}")
        scored.append(score_job(job))
    scored.sort(key=lambda j: j["score"], reverse=True)
    return scored
