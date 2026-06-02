"""
Browser automation layer using Playwright.
Handles Reddit login, posting, and replying without using Reddit's API.
"""

import time
import random
import logging
from contextlib import contextmanager

from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeout

from config import REDDIT_USERNAME, REDDIT_PASSWORD, SUBREDDIT, HEADLESS_BROWSER

logger = logging.getLogger(__name__)

REDDIT_BASE = "https://www.reddit.com"


def _human_delay(min_s: float = 0.8, max_s: float = 2.5):
    """Random sleep to mimic human pacing."""
    time.sleep(random.uniform(min_s, max_s))


def _type_like_human(page: Page, selector: str, text: str):
    """Type text with random delays between keystrokes."""
    page.click(selector)
    for char in text:
        page.keyboard.type(char)
        time.sleep(random.uniform(0.05, 0.18))


@contextmanager
def reddit_session():
    """Context manager that yields an authenticated Playwright page."""
    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(
            headless=HEADLESS_BROWSER,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        try:
            _login(page)
            yield page
        finally:
            browser.close()


def _login(page: Page):
    """Log into Reddit using username/password."""
    logger.info("Logging into Reddit...")
    page.goto(f"{REDDIT_BASE}/login", wait_until="networkidle")
    _human_delay(1.5, 3.0)

    # Fill username
    page.wait_for_selector('input[name="username"]', timeout=15000)
    _type_like_human(page, 'input[name="username"]', REDDIT_USERNAME)
    _human_delay()

    # Fill password
    _type_like_human(page, 'input[name="password"]', REDDIT_PASSWORD)
    _human_delay()

    # Submit
    page.keyboard.press("Enter")
    page.wait_for_url(f"{REDDIT_BASE}/**", timeout=20000)
    _human_delay(2.0, 4.0)
    logger.info("Login successful.")


def submit_post(page: Page, title: str, body: str) -> str:
    """
    Submit a text post to the configured subreddit.
    Returns the URL of the created post.
    """
    submit_url = f"{REDDIT_BASE}/r/{SUBREDDIT}/submit"
    logger.info(f"Navigating to submit page: {submit_url}")
    page.goto(submit_url, wait_until="networkidle")
    _human_delay(2.0, 4.0)

    # Select "Text" post type if tabs exist
    try:
        text_tab = page.locator('[data-test-id="post-type-tab-text"], button:has-text("Text")')
        if text_tab.count() > 0:
            text_tab.first.click()
            _human_delay()
    except Exception:
        pass

    # Title field
    title_selectors = [
        'textarea[placeholder*="Title"]',
        'textarea[name="title"]',
        '[data-test-id="post-title-input"]',
        '#post-title',
    ]
    title_field = None
    for sel in title_selectors:
        try:
            page.wait_for_selector(sel, timeout=5000)
            title_field = sel
            break
        except PlaywrightTimeout:
            continue

    if not title_field:
        raise RuntimeError("Could not find post title field on submit page.")

    page.click(title_field)
    page.fill(title_field, title)
    _human_delay()

    # Body field (rich text editor or plain textarea)
    body_selectors = [
        '.public-DraftEditor-content',
        '[data-test-id="post-body-input"]',
        'textarea[placeholder*="body"]',
        'div[contenteditable="true"]',
    ]
    body_field = None
    for sel in body_selectors:
        try:
            page.wait_for_selector(sel, timeout=5000)
            body_field = sel
            break
        except PlaywrightTimeout:
            continue

    if body_field:
        page.click(body_field)
        # For contenteditable divs, type character by character
        for line in body.split("\n"):
            page.keyboard.type(line)
            page.keyboard.press("Enter")
            _human_delay(0.3, 0.8)
    _human_delay(1.0, 2.0)

    # Submit button
    submit_selectors = [
        'button[type="submit"]:has-text("Post")',
        'button:has-text("Submit")',
        '[data-test-id="post-submit-button"]',
    ]
    for sel in submit_selectors:
        try:
            btn = page.locator(sel)
            if btn.count() > 0 and btn.first.is_enabled():
                btn.first.click()
                break
        except Exception:
            continue

    # Wait for redirect to the new post
    page.wait_for_url(f"**/r/{SUBREDDIT}/comments/**", timeout=30000)
    post_url = page.url
    logger.info(f"Post submitted: {post_url}")
    return post_url


def get_recent_posts(page: Page, limit: int = 20) -> list[dict]:
    """
    Fetch recent posts from the subreddit.
    Returns list of dicts with keys: title, url, comment_count
    """
    logger.info(f"Fetching recent posts from r/{SUBREDDIT}...")
    page.goto(f"{REDDIT_BASE}/r/{SUBREDDIT}/new", wait_until="networkidle")
    _human_delay(2.0, 3.5)

    posts = []
    post_elements = page.locator('article, [data-testid="post-container"], [data-full-name^="t3_"]').all()

    for el in post_elements[:limit]:
        try:
            title_el = el.locator('h3, [data-click-id="text"] h1').first
            link_el = el.locator('a[data-click-id="body"], a[href*="/comments/"]').first
            title = title_el.inner_text() if title_el.count() > 0 else ""
            href = link_el.get_attribute("href") if link_el.count() > 0 else ""
            if href and not href.startswith("http"):
                href = f"{REDDIT_BASE}{href}"
            if title and href:
                posts.append({"title": title.strip(), "url": href, "comments": []})
        except Exception:
            continue

    logger.info(f"Found {len(posts)} posts.")
    return posts


def get_unanswered_comments(page: Page, post_url: str) -> list[dict]:
    """
    Visit a post and return top-level comments that have no replies yet.
    Returns list of dicts with keys: text, element_id
    """
    page.goto(post_url, wait_until="networkidle")
    _human_delay(2.0, 3.5)

    # Get post body for context
    post_body = ""
    try:
        post_body = page.locator('[data-test-id="post-content"] p, .usertext-body p').first.inner_text()
    except Exception:
        pass

    # Collect top-level comments with 0 replies
    comments = []
    comment_elements = page.locator('div[id^="thing_t1_"]').all()

    for el in comment_elements[:10]:
        try:
            comment_text_el = el.locator('.md p, [data-testid="comment"] p').first
            reply_count = el.locator('div[id^="thing_t1_"]').count()
            if comment_text_el.count() > 0 and reply_count == 0:
                text = comment_text_el.inner_text().strip()
                element_id = el.get_attribute("id") or ""
                if text and len(text) > 10:
                    comments.append({
                        "text": text,
                        "element_id": element_id,
                        "post_body": post_body,
                    })
        except Exception:
            continue

    return comments


def post_reply(page: Page, post_url: str, comment_element_id: str, reply_text: str) -> bool:
    """
    Reply to a specific comment on a post.
    Returns True if successful.
    """
    page.goto(post_url, wait_until="networkidle")
    _human_delay(2.0, 3.0)

    try:
        # Find the comment and click its Reply button
        comment_el = page.locator(f"#{comment_element_id}")
        reply_btn = comment_el.locator('button:has-text("Reply"), a:has-text("reply")').first
        reply_btn.click()
        _human_delay(1.0, 2.0)

        # Find the textarea that appeared
        reply_input = comment_el.locator('textarea, .public-DraftEditor-content').first
        reply_input.click()
        for line in reply_text.split("\n"):
            page.keyboard.type(line)
            page.keyboard.press("Enter")
            _human_delay(0.2, 0.6)

        # Submit
        save_btn = comment_el.locator('button:has-text("Save"), button[type="submit"]').first
        save_btn.click()
        _human_delay(2.0, 3.0)
        logger.info(f"Reply posted to comment {comment_element_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to post reply to {comment_element_id}: {e}")
        return False
