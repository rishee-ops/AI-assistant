# Feedback Enhancement Sync → "AI for Women"

A small, production-ready Python automation that:

1. **Reads** raw student feedback from a source Google Sheet (the
   **`SA response evening`** tab).
2. **Identifies relevant rows** — those whose course matches the configured
   program filter (default: *Training Program on Using AI for Business
   Growth*).
3. **Rewrites the feedback professionally** into polished, authentic,
   presentation-ready testimonials (Claude API, with an offline fallback).
4. **Appends the results into ONLY the `AI for Women` tab** of the destination
   sheet — safely, idempotently, with full logging.

It is a **Google Sheets automation + feedback enhancement workflow**, not a
forecasting system.

---

## Safety guarantees

These are enforced in code, not just documented:

- **Only the `AI for Women` tab is ever written to.** The destination tab is
  opened by exact title and re-checked before any write
  (`sheets.py::open_destination`). No other tab/sheet is touched.
- **Appends only.** Rows are added below existing data with
  `append_rows(..., insert_data_option="INSERT_ROWS")`. Existing cells,
  formatting, and formulas are never overwritten.
- **Column structure preserved.** Output rows are built in the destination's
  own header order, read live at runtime.
- **No duplicates.** Every source row gets a stable key (email + course +
  topic + date). A row is skipped if its key already exists in the
  destination *or* in the local state file.
- **Faithful rewrites.** The rewrite prompt forbids inventing achievements,
  exaggerating, or changing meaning. Junk inputs (`NA`, `-`, empty) are
  skipped, not fabricated.

---

## Architecture

```
main.py                     CLI entry point (flags, exit codes)
feedback_sync/
  config.py                 env-var config + validation
  logging_setup.py          console + rotating file logging
  sheets.py                 gspread auth, retries, fuzzy headers, write guard
  rewriter.py               Anthropic + offline rule-based engines
  state.py                  local dedupe state (atomic JSON)
  workflow.py               orchestration (read→filter→rewrite→dedupe→append)
tests/                      offline unit + end-to-end tests (no network)
deploy/                     systemd timer, crontab, GitHub Actions
```

The source→destination column mapping is **fuzzy** (case / whitespace / `?`
insensitive), so the real headers — e.g. `"Which course are you giving
feedback for "` (trailing space) — match the configured names cleanly.

---

## 1. Prerequisites

- Python 3.10+
- A Google Cloud **service account** with the Sheets API enabled
- The service-account email shared on **both** spreadsheets:
  - Source → **Viewer**
  - Destination → **Editor**
- (For LLM rewriting) an **Anthropic API key**

### Create the service account

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) →
   create/select a project.
2. **APIs & Services → Library** → enable **Google Sheets API** and
   **Google Drive API**.
3. **APIs & Services → Credentials → Create credentials → Service account**.
4. Open the new service account → **Keys → Add key → JSON**. Download it as
   `service_account.json` (keep it secret; it is git-ignored).
5. Copy the service account's email (looks like
   `name@project.iam.gserviceaccount.com`).
6. In each Google Sheet, click **Share** and add that email
   (Source = Viewer, Destination = Editor).

---

## 2. Install

```bash
git clone <this-repo> && cd ai-assistant
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

---

## 3. Configure

```bash
cp .env.example .env
# then edit .env
```

Key variables (full list in `.env.example`):

| Variable | Purpose | Default |
|---|---|---|
| `GOOGLE_SERVICE_ACCOUNT_FILE` | path to the JSON key | `./service_account.json` |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | inline JSON (overrides file) | — |
| `SOURCE_SPREADSHEET_ID` | source workbook id | preset |
| `SOURCE_WORKSHEET_TITLE` | source tab | `SA response evening` |
| `DEST_SPREADSHEET_ID` | destination workbook id | preset |
| `DEST_WORKSHEET_TITLE` | **only** tab written to | `AI for Women` |
| `PROGRAM_COLUMN` | source column to filter on | `Which course are you giving feedback for?` |
| `PROGRAM_FILTER` | comma-sep substrings (any-match) | `Training Program on Using AI for Business Growth` |
| `FEEDBACK_COLUMN` | raw feedback column (auto if blank) | `We value your feedback. Please let us know more.` |
| `ROW_ID_COLUMN` | stable id for dedupe | `Email address` |
| `REWRITE_ENGINE` | `anthropic` or `rule` | `anthropic` |
| `ANTHROPIC_API_KEY` | required for `anthropic` | — |
| `REWRITE_MODEL` | Claude model | `claude-sonnet-4-6` |
| `DRY_RUN` | preview without writing | `false` |

> **Tip:** to add more programs, set
> `PROGRAM_FILTER=Training Program on Using AI for Business Growth,SkillArbitrage`.

---

## 4. Run

```bash
# Preview — reads + rewrites + logs, but writes NOTHING:
python main.py --dry-run

# Real run:
python main.py

# Force the offline rewriter (no API key needed, lighter polish):
python main.py --engine rule
```

Exit codes: `0` success · `1` fatal error · `2` bad config · `3` completed
with row-level errors. Logs stream to the console and to
`logs/feedback_sync.log` (rotated).

A run prints a summary like:

```
Run complete: source_rows=237 relevant=237 skipped_no_feedback=95 \
duplicates=0 rewritten=142 appended=142 errors=0 dry_run=False
```

---

## 5. Schedule daily automation

Pick one of three options under `deploy/`:

### a) systemd timer (recommended on a Linux server)

```bash
sudo useradd -r -s /usr/sbin/nologin feedbacksync
sudo mkdir -p /opt/feedback-sync && sudo chown feedbacksync /opt/feedback-sync
# copy the project there, create .venv, install requirements, and place .env
sudo chmod 600 /opt/feedback-sync/.env

sudo cp deploy/systemd/feedback-sync.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now feedback-sync.timer
systemctl list-timers feedback-sync.timer      # verify schedule
journalctl -u feedback-sync.service -n 50       # view last run
```

### b) cron

```bash
crontab -e        # paste & edit the line from deploy/crontab.example
```

### c) GitHub Actions

Copy `deploy/github-actions-daily.yml` to
`.github/workflows/feedback-sync.yml` and add the repo secrets
`GOOGLE_SERVICE_ACCOUNT_JSON` and `ANTHROPIC_API_KEY`.

---

## 6. Tests

```bash
pip install pytest
python -m pytest -q
```

The suite is fully offline (fake Sheets client, rule rewriter) and covers
header resolution, junk filtering, program matching, destination column
ordering, serial numbering, dedupe, and idempotent re-runs.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Source tab '...' not found. Available tabs: [...]` | Tab title mismatch — copy an exact title from the list shown. |
| `Destination tab 'AI for Women' not found` | Share the destination with the service account and check the title. |
| `403 PERMISSION_DENIED` | The service-account email isn't shared on the sheet (or wrong role). |
| `REWRITE_ENGINE=anthropic requires ANTHROPIC_API_KEY` | Set the key, or use `--engine rule`. |
| Everything skipped as `skipped_no_feedback` | The feedback column was empty/junk; check `FEEDBACK_COLUMN`. |
| Rows appear filtered out | Check `PROGRAM_COLUMN` / `PROGRAM_FILTER` against the real course text. |

Transient Google/Anthropic API errors are retried automatically with
exponential backoff (2s → 4s → 8s → 16s).
