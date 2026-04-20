# Job Search Automation — Setup Guide

Every day at **9:30 AM IST** qualifying Supply Chain / Operations jobs posted in the last 24 hours are automatically appended to your Google Sheet, each scored out of 10 with tailored resume bullets.

---

## What you need (one-time, ~30 minutes)

### 1. Apify API Key (Free)
1. Go to **https://apify.com** → Sign Up (free account)
2. Dashboard → **Settings** → **Integrations** → **API tokens**
3. Copy your **Personal API token**

### 2. Anthropic API Key (~$3–5/month)
1. Go to **https://console.anthropic.com** → Sign Up (separate from claude.ai)
2. **Settings** → **API Keys** → **Create Key**
3. Copy the key (starts with `sk-ant-...`)
4. Add a credit card under **Billing** → **Payment methods**
   - You'll only be charged for actual usage (~$3–5/month for this script)

### 3. Google Sheets + Service Account (Free)

#### 3a — Create the Google Sheet
1. Go to **https://sheets.google.com** → create a new blank spreadsheet
2. Name it `Job Search Results` (or anything you like)
3. Copy the **Sheet ID** from the URL:
   `https://docs.google.com/spreadsheets/d/`**`THIS_LONG_ID`**`/edit`

#### 3b — Create a Google Cloud Service Account
1. Go to **https://console.cloud.google.com**
2. Create a new project — name it `job-search-bot`
3. **APIs & Services** → **+ Enable APIs and Services** → search **Google Sheets API** → Enable
4. Go to **APIs & Services** → **Credentials** → **+ Create Credentials** → **Service account**
5. Name it `job-search-bot` → **Create and Continue** → **Done**
6. Click the service account → **Keys** tab → **Add Key** → **Create new key** → **JSON**
7. A `.json` file downloads — keep it safe, never commit it to git

#### 3c — Share the Sheet with the Service Account
1. Open the downloaded JSON file in a text editor
2. Copy the `client_email` value (e.g. `job-search-bot@your-project.iam.gserviceaccount.com`)
3. Open your Google Sheet → **Share** → paste that email → role: **Editor** → **Send**

#### 3d — Prepare the JSON for GitHub Secrets
You'll paste the entire contents of the JSON file as a GitHub Secret — GitHub handles multi-line values correctly.

### 4. GitHub Repository (Free)
1. Go to **https://github.com** → **New repository**
2. Name it `job-search-automation`, set it to **Private**
3. Don't initialise with README

---

## Deploy the code

Open a terminal in `C:\Users\yashk\job_search\` and run:

```bash
git init
git add .
git commit -m "Initial job search automation"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/job-search-automation.git
git push -u origin main
```

---

## Add secrets to GitHub

1. Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** for each of the following:

| Secret Name | Value |
|---|---|
| `APIFY_API_KEY` | Your Apify personal API token |
| `ANTHROPIC_API_KEY` | Your Anthropic API key (`sk-ant-...`) |
| `GOOGLE_SHEET_ID` | The long ID from your Google Sheet URL |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | The entire contents of the downloaded JSON key file |

---

## Test it immediately

Once secrets are added, go to your repo on GitHub:
1. Click **Actions** tab
2. Click **Daily Job Search Digest**
3. Click **Run workflow** → **Run workflow**

The first run will take ~5–10 minutes. Open your Google Sheet after — you'll see a header row added automatically and one row per qualifying job.

---

## What the sheet looks like

| Date Added | Title | Company | Location | Score (/10) | Reasoning | Key Matches | Red Flags | Tailored Bullets | URL | Source | Posted At |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-04-20 | Head of Operations | Acme Corp | Mumbai | 8 | Strong fit because… | Vendor mgmt, P&L… | None | • Led supply chain… | https://… | LinkedIn | 1 day ago |

Each daily run appends only **new** rows. Jobs already in the sheet (matched by URL) are skipped automatically.

---

## Monitor Apify usage

- Go to **https://apify.com/billing** to see your monthly credit usage
- Free tier: $5/month — sufficient for daily scraping
- You'll get an email from Apify before any charges kick in

---

## Project structure

```
job_search/
├── main.py              # Orchestrator (run this)
├── config.py            # API keys + search params
├── resume_data.py       # Your resume as text (for Claude AI)
├── matcher.py           # Claude AI job scoring
├── resume_tailor.py     # Claude AI resume tailoring
├── sheets_output.py     # Google Sheets row appender
├── email_digest.py      # (kept, not used)
├── scrapers/
│   ├── linkedin.py      # LinkedIn scraper (Apify)
│   ├── indeed.py        # Indeed scraper (Apify)
│   └── naukri.py        # Naukri scraper (Apify + fallback)
├── .github/workflows/
│   └── job_search.yml   # GitHub Actions cron (daily 9:30 AM IST)
├── requirements.txt
├── .env.example         # Template for local testing
└── .gitignore           # Excludes .env from git
```

---

## Local testing (optional)

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env:
#   GOOGLE_SHEET_ID — your sheet ID
#   GOOGLE_SERVICE_ACCOUNT_JSON — paste the full JSON on a single line
python main.py
```
