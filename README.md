# LinkedIn AI Outreach Agent

Uploads a PDF dossier → AI builds your ideal customer profile → finds matching people on LinkedIn → writes personalized messages → shows you the full plan → you approve with one keypress → it runs everything.

## Setup

```bash
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
# Fill in .env with your OpenAI key + LinkedIn credentials
```

## Run

```bash
# Basic — connect + comment on their posts
python main.py --dossier uploads/your_dossier.pdf

# Also reply to comments on YOUR posts
python main.py --dossier uploads/your_dossier.pdf \
  --your-posts "https://www.linkedin.com/feed/update/urn:li:activity:..." \
               "https://www.linkedin.com/feed/update/urn:li:activity:..."
```

## What it does

1. Reads your PDF → extracts ICP (industries, titles, pain points, tone)
2. Opens LinkedIn in a visible browser window
3. Logs in (saves session so you only do it once)
4. Searches for people matching your ICP keywords
5. Scores each profile with AI (only keeps 60+/100 matches)
6. Writes a personalized connection note for each
7. Finds their 2 most recent posts + writes a relevant comment for each
8. Shows you a table of everyone + what will be sent
9. **You press Y** → it sends everything
10. Visits your own posts + replies to every comment with an AI-written reply

## Limits (safe daily usage)
- Max 15 connection requests per run
- Max 10 comments per run
- Human-like random delays between every action

## Files
```
main.py              ← entry point
dossier_parser.py    ← PDF → ICP via OpenAI
ai_writer.py         ← generates messages/comments
linkedin_browser.py  ← Playwright automation
config.py            ← settings & limits
uploads/             ← put your PDF here
session/             ← saved LinkedIn session (auto-created)
logs/                ← action logs
```
