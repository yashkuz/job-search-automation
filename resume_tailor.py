"""
Resume tailoring using Claude Haiku.
For each high-scoring job, generates 4-5 tailored resume bullet points
that highlight Yash's most relevant experience using keywords from the JD.
"""
import logging
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_TAILOR_MODEL
from resume_data import RESUME_TEXT

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = (
    "You are an expert resume writer specialising in Supply Chain and Operations roles in India. "
    "Given a candidate's resume and a target job description, write 4–5 tailored resume bullet points "
    "that highlight the candidate's most relevant experience for this specific role. "
    "Rules:\n"
    "- Use strong action verbs (Led, Designed, Drove, Scaled, Optimised, etc.)\n"
    "- Include quantified achievements from the actual resume — do NOT invent numbers\n"
    "- Naturally incorporate keywords from the JD\n"
    "- Keep each bullet under 25 words\n"
    "- Return ONLY the bullet points, one per line, starting with '•'\n"
    "- Do not add headers, titles, or explanations"
)


def tailor_resume(job: dict) -> str:
    """
    Generate tailored resume bullets for a specific job.
    Returns a string of bullet points (one per line).
    """
    key_matches_str = "\n".join(f"- {m}" for m in job.get("key_matches", []))
    prompt = (
        f"CANDIDATE RESUME:\n{RESUME_TEXT}\n\n"
        f"TARGET ROLE: {job['title']} at {job['company']}\n"
        f"LOCATION: {job['location']}\n"
        f"KEY MATCHES IDENTIFIED:\n{key_matches_str}\n\n"
        f"JOB DESCRIPTION:\n{job['description']}"
    )

    try:
        response = _client.messages.create(
            model=CLAUDE_TAILOR_MODEL,
            max_tokens=600,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )
        bullets = response.content[0].text.strip()
        return bullets
    except Exception as e:
        logger.warning(f"[Tailor] Error for '{job['title']}' @ '{job['company']}': {e}")
        return "• (Resume tailoring unavailable for this job)"


def tailor_jobs(jobs: list[dict]) -> list[dict]:
    """
    Add 'tailored_bullets' field to each job in the list.
    Only processes jobs that have been scored (score field present).
    """
    for i, job in enumerate(jobs):
        logger.info(
            f"[Tailor] Tailoring {i+1}/{len(jobs)}: {job['title']} @ {job['company']}"
        )
        job["tailored_bullets"] = tailor_resume(job)
    return jobs
