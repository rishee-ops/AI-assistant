"""Central configuration for the Reddit bot."""
import os
from dotenv import load_dotenv

load_dotenv()

# Reddit credentials (for browser login)
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME", "")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD", "")

# Target subreddit
SUBREDDIT = os.getenv("SUBREDDIT", "Landremotejobs")

# Anthropic / Claude API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"

# Posting schedule (hour of day in UTC, 24h format)
POST_HOURS = [9, 15, 20]          # 3 posts per day
REPLY_CHECK_INTERVAL_MIN = 30     # check for new comments every 30 min

# How many recent posts to scan for reply opportunities
REPLY_SCAN_LIMIT = 20

# Headless browser (False = visible browser window, True = background)
HEADLESS_BROWSER = os.getenv("HEADLESS_BROWSER", "true").lower() == "true"

# Paths
STYLE_GUIDE_PATH = "style_guide.txt"
POST_LOG_PATH = "post_log.json"
