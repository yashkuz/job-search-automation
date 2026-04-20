"""
Email digest builder and sender.
Sends a rich HTML email with scored job cards + tailored resume bullets.
"""
import smtplib
import ssl
import logging
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, DIGEST_TO, MIN_FIT_SCORE

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

# Score badge colours
def _score_color(score: int) -> str:
    if score >= 9:
        return "#1a7f37"   # dark green
    if score >= 7:
        return "#0969da"   # blue
    if score >= 5:
        return "#9a6700"   # amber
    return "#d1242f"       # red


def _score_label(score: int) -> str:
    if score >= 9:
        return "Excellent fit"
    if score >= 7:
        return "Strong fit"
    if score >= 5:
        return "Moderate fit"
    return "Weak fit"


def _source_icon(source: str) -> str:
    icons = {"LinkedIn": "🔵", "Indeed": "🟣", "Naukri": "🟠"}
    return icons.get(source, "⚪")


def _build_job_card(job: dict) -> str:
    score = job.get("score", 0)
    color = _score_color(score)
    label = _score_label(score)
    bullets_raw = job.get("tailored_bullets", "")
    bullet_lines = [
        line.strip().lstrip("•").strip()
        for line in bullets_raw.splitlines()
        if line.strip() and line.strip() != "•"
    ]
    bullets_html = "".join(f"<li>{b}</li>" for b in bullet_lines)
    red_flags = job.get("red_flags", [])
    flags_html = ""
    if red_flags:
        flags_items = "".join(f"<li>{f}</li>" for f in red_flags)
        flags_html = f"""
        <div style="margin-top:10px;padding:8px 12px;background:#fff8c5;border-left:3px solid #d4a017;border-radius:4px;font-size:13px;">
          <strong>⚠ Things to address:</strong>
          <ul style="margin:4px 0 0 0;padding-left:18px;">{flags_items}</ul>
        </div>"""

    return f"""
    <div style="background:#ffffff;border:1px solid #d0d7de;border-radius:8px;padding:20px;margin-bottom:18px;font-family:Arial,sans-serif;">
      <!-- Header row -->
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
        <div>
          <span style="font-size:13px;color:#57606a;">{_source_icon(job['source'])} {job['source']}</span>
          <h3 style="margin:4px 0 2px 0;font-size:17px;color:#24292f;">{job['title']}</h3>
          <p style="margin:0;font-size:14px;color:#57606a;">{job['company']} &nbsp;·&nbsp; {job['location']}</p>
          <p style="margin:4px 0 0 0;font-size:12px;color:#8c959f;">Posted: {job.get('posted_at','—')}</p>
        </div>
        <div style="text-align:center;min-width:72px;">
          <div style="background:{color};color:#fff;font-size:28px;font-weight:bold;border-radius:8px;padding:8px 14px;display:inline-block;">{score}/10</div>
          <div style="font-size:11px;color:{color};font-weight:600;margin-top:4px;">{label}</div>
        </div>
      </div>

      <!-- Reasoning -->
      <div style="margin-top:12px;padding:10px 14px;background:#f6f8fa;border-radius:6px;font-size:14px;color:#24292f;line-height:1.5;">
        {job.get('reasoning','')}
      </div>

      <!-- Key matches -->
      <div style="margin-top:12px;">
        <strong style="font-size:13px;color:#1a7f37;">✓ Key Matches:</strong>
        <ul style="margin:4px 0 0 0;padding-left:18px;font-size:13px;color:#24292f;">
          {"".join(f"<li>{m}</li>" for m in job.get('key_matches',[]))}
        </ul>
      </div>

      <!-- Tailored bullets -->
      {f'''<div style="margin-top:12px;">
        <strong style="font-size:13px;color:#0969da;">📝 Tailored Resume Highlights for this role:</strong>
        <ul style="margin:4px 0 0 0;padding-left:18px;font-size:13px;color:#24292f;line-height:1.6;">
          {bullets_html}
        </ul>
      </div>''' if bullets_html else ''}

      {flags_html}

      <!-- CTA -->
      <div style="margin-top:16px;">
        <a href="{job['url']}" style="display:inline-block;background:#0969da;color:#fff;padding:9px 20px;border-radius:6px;text-decoration:none;font-size:14px;font-weight:600;">
          View &amp; Apply →
        </a>
      </div>
    </div>"""


def build_html(jobs: list[dict], total_scraped: int) -> str:
    now_ist = datetime.now(IST)
    date_str = now_ist.strftime("%A, %d %B %Y")
    qualifying = [j for j in jobs if j.get("score", 0) >= MIN_FIT_SCORE]

    cards_html = "".join(_build_job_card(j) for j in qualifying) if qualifying else (
        '<p style="color:#57606a;font-size:15px;">No jobs scored 7+ today. Check back tomorrow!</p>'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daily Job Digest</title></head>
<body style="margin:0;padding:0;background:#f6f8fa;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f6f8fa;padding:24px 0;">
    <tr><td align="center">
      <table width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;">

        <!-- Header -->
        <tr><td style="background:#24292f;padding:28px 32px;border-radius:10px 10px 0 0;">
          <h1 style="margin:0;color:#fff;font-size:22px;">📋 Your Daily Job Digest</h1>
          <p style="margin:6px 0 0;color:#8c959f;font-size:14px;">{date_str} &nbsp;·&nbsp; Delivered at 9:30 AM IST</p>
        </td></tr>

        <!-- Summary bar -->
        <tr><td style="background:#fff;padding:16px 32px;border-bottom:1px solid #d0d7de;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="text-align:center;">
                <div style="font-size:28px;font-weight:bold;color:#24292f;">{total_scraped}</div>
                <div style="font-size:12px;color:#57606a;">Jobs Scraped</div>
              </td>
              <td style="text-align:center;">
                <div style="font-size:28px;font-weight:bold;color:#0969da;">{len(qualifying)}</div>
                <div style="font-size:12px;color:#57606a;">Scored 7+/10</div>
              </td>
              <td style="text-align:center;">
                <div style="font-size:28px;font-weight:bold;color:#1a7f37;">{sum(1 for j in qualifying if j.get('score',0)>=9)}</div>
                <div style="font-size:12px;color:#57606a;">Excellent Fits (9+)</div>
              </td>
              <td style="text-align:center;">
                <div style="font-size:28px;font-weight:bold;color:#57606a;">24h</div>
                <div style="font-size:12px;color:#57606a;">Fresh Postings Only</div>
              </td>
            </tr>
          </table>
        </td></tr>

        <!-- Job cards -->
        <tr><td style="padding:24px 32px;">
          {cards_html}
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f6f8fa;padding:20px 32px;border-top:1px solid #d0d7de;border-radius:0 0 10px 10px;text-align:center;">
          <p style="margin:0;font-size:12px;color:#8c959f;">
            Sourced from LinkedIn · Indeed · Naukri &nbsp;|&nbsp;
            Scored by Claude AI &nbsp;|&nbsp;
            Locations: Mumbai / Remote (India)
          </p>
          <p style="margin:6px 0 0;font-size:11px;color:#b1b8c0;">
            This digest is generated automatically. Always verify job details before applying.
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def build_plain_text(jobs: list[dict], total_scraped: int) -> str:
    now_ist = datetime.now(IST)
    date_str = now_ist.strftime("%A, %d %B %Y")
    qualifying = [j for j in jobs if j.get("score", 0) >= MIN_FIT_SCORE]
    lines = [
        f"DAILY JOB DIGEST — {date_str}",
        f"Jobs scraped: {total_scraped}  |  Scored 7+: {len(qualifying)}",
        "=" * 60,
    ]
    for job in qualifying:
        lines += [
            "",
            f"[{job['score']}/10] {job['title']}",
            f"Company : {job['company']}",
            f"Location: {job['location']}",
            f"Source  : {job['source']}",
            f"Posted  : {job.get('posted_at', '—')}",
            f"URL     : {job['url']}",
            f"Summary : {job.get('reasoning', '')}",
        ]
        if job.get("tailored_bullets"):
            lines.append("Tailored bullets:")
            for b in job["tailored_bullets"].splitlines():
                if b.strip():
                    lines.append(f"  {b.strip()}")
        lines.append("-" * 60)
    return "\n".join(lines)


def send_digest(jobs: list[dict], total_scraped: int) -> None:
    """Build and send the HTML digest email via Gmail SMTP."""
    now_ist = datetime.now(IST)
    date_str = now_ist.strftime("%d %b %Y")
    qualifying_count = sum(1 for j in jobs if j.get("score", 0) >= MIN_FIT_SCORE)

    subject = f"Job Digest {date_str} — {qualifying_count} role{'s' if qualifying_count != 1 else ''} matched (7+/10)"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = DIGEST_TO

    plain = build_plain_text(jobs, total_scraped)
    html  = build_html(jobs, total_scraped)

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, DIGEST_TO, msg.as_string())

    logger.info(f"[Email] Digest sent to {DIGEST_TO} — {qualifying_count} qualifying jobs")
