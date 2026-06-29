import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# Your LinkedIn profile name (used to scrape your own profile for ICP)
YOUR_LINKEDIN_NAME = "Rishee Rhudra"

# Companies whose employees should never receive connection requests or comments
EXCLUDED_COMPANIES = ["lawsikho", "law sikho", "skillarbitrage", "skill arbitrage"]

# How many profiles to fetch per search keyword before scoring
MAX_PROFILES_PER_KEYWORD = 8

# Minimum ICP score (0-100) to include a profile
MIN_ICP_SCORE = 60

# Max connection requests per run (LinkedIn daily limit ~20-25 is safe)
MAX_CONNECTIONS_PER_RUN = 20

# Max post comments per run
MAX_COMMENTS_PER_RUN = 10

# Your own LinkedIn post URLs to monitor for comments/replies
YOUR_POST_URLS: list[str] = []
