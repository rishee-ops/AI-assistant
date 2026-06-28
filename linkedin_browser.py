"""
Playwright-based LinkedIn automation.
Handles: login (with session save/restore), profile search, connection requests,
post commenting, and replying to comments on the user's own posts.
"""

import json
import time
import random
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Page, BrowserContext

SESSION_FILE = Path("session/linkedin_session.json")


def _human_delay(min_s: float = 1.5, max_s: float = 4.0):
    time.sleep(random.uniform(min_s, max_s))


async def _async_human_delay(min_s: float = 1.5, max_s: float = 4.0):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def _type_like_human(page: Page, selector: str, text: str):
    await page.click(selector)
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.05, 0.15))


class LinkedInBrowser:
    def __init__(self, email: str, password: str, headless: bool = False):
        self.email = email
        self.password = password
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context: BrowserContext = None
        self.page: Page = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=["--start-maximized"],
        )
        if SESSION_FILE.exists():
            self.context = await self.browser.new_context(
                storage_state=str(SESSION_FILE),
                viewport={"width": 1280, "height": 900},
            )
        else:
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 900},
            )
        self.page = await self.context.new_page()

    async def stop(self):
        await self.context.storage_state(path=str(SESSION_FILE))
        await self.browser.close()
        await self.playwright.stop()

    async def login(self) -> bool:
        """Login to LinkedIn. Returns True if already logged in or login succeeded."""
        await self.page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        await _async_human_delay(2, 4)

        if "feed" in self.page.url:
            return True  # already logged in via saved session

        await self.page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        await _async_human_delay(1, 2)

        await _type_like_human(self.page, "#username", self.email)
        await _async_human_delay(0.5, 1)
        await _type_like_human(self.page, "#password", self.password)
        await _async_human_delay(0.5, 1)
        await self.page.click('button[type="submit"]')
        await _async_human_delay(3, 5)

        if "feed" in self.page.url or "checkpoint" not in self.page.url:
            await self.context.storage_state(path=str(SESSION_FILE))
            return True

        # Handle 2FA / CAPTCHA — wait for user to complete manually
        print("\n[!] LinkedIn requires verification. Please complete it in the browser window.")
        print("    Press Enter here once you are logged in...")
        input()
        await self.context.storage_state(path=str(SESSION_FILE))
        return True

    async def search_profiles(self, keyword: str, max_results: int = 10) -> list[dict]:
        """Search LinkedIn People for a keyword, return basic profile data."""
        search_url = (
            f"https://www.linkedin.com/search/results/people/"
            f"?keywords={keyword.replace(' ', '%20')}&origin=GLOBAL_SEARCH_HEADER"
        )
        await self.page.goto(search_url, wait_until="domcontentloaded")
        await _async_human_delay(2, 4)

        profiles = []
        cards = await self.page.query_selector_all(".entity-result__item")

        for card in cards[:max_results]:
            try:
                name_el = await card.query_selector(".entity-result__title-text a span[aria-hidden='true']")
                name = (await name_el.inner_text()).strip() if name_el else ""

                url_el = await card.query_selector(".entity-result__title-text a")
                url = await url_el.get_attribute("href") if url_el else ""
                url = url.split("?")[0] if url else ""

                subtitle_el = await card.query_selector(".entity-result__primary-subtitle")
                subtitle = (await subtitle_el.inner_text()).strip() if subtitle_el else ""

                secondary_el = await card.query_selector(".entity-result__secondary-subtitle")
                company = (await secondary_el.inner_text()).strip() if secondary_el else ""

                if name and url:
                    profiles.append({
                        "name": name,
                        "url": url,
                        "title": subtitle,
                        "company": company,
                        "headline": subtitle,
                        "about": "",
                    })
            except Exception:
                continue

        return profiles

    async def get_profile_details(self, profile_url: str) -> dict:
        """Visit a profile page and scrape more details."""
        await self.page.goto(profile_url, wait_until="domcontentloaded")
        await _async_human_delay(2, 4)

        about = ""
        try:
            about_el = await self.page.query_selector(".pv-about__summary-text span[aria-hidden='true']")
            if not about_el:
                about_el = await self.page.query_selector("div[data-generated-suggestion-target] span[aria-hidden='true']")
            if about_el:
                about = (await about_el.inner_text()).strip()
        except Exception:
            pass

        return {"about": about}

    async def send_connection_request(self, profile_url: str, note: str) -> bool:
        """Navigate to profile and send a connection request with a note."""
        await self.page.goto(profile_url, wait_until="domcontentloaded")
        await _async_human_delay(2, 4)

        try:
            # Click Connect button (may be inside More dropdown)
            connect_btn = await self.page.query_selector('button[aria-label*="Connect"]')
            if not connect_btn:
                more_btn = await self.page.query_selector('button[aria-label*="More actions"]')
                if more_btn:
                    await more_btn.click()
                    await _async_human_delay(1, 2)
                    connect_btn = await self.page.query_selector('div[aria-label*="Connect"]')

            if not connect_btn:
                return False

            await connect_btn.click()
            await _async_human_delay(1, 2)

            # Click "Add a note"
            add_note_btn = await self.page.query_selector('button[aria-label="Add a note"]')
            if add_note_btn:
                await add_note_btn.click()
                await _async_human_delay(1, 2)
                textarea = await self.page.query_selector("#custom-message")
                if textarea:
                    await _type_like_human(self.page, "#custom-message", note[:280])
                    await _async_human_delay(1, 2)

            # Send
            send_btn = await self.page.query_selector('button[aria-label="Send now"]')
            if not send_btn:
                send_btn = await self.page.query_selector('button[aria-label="Send invitation"]')
            if send_btn:
                await send_btn.click()
                await _async_human_delay(2, 3)
                return True

        except Exception as e:
            print(f"    [!] Connection error: {e}")

        return False

    async def get_profile_recent_posts(self, profile_url: str, max_posts: int = 3) -> list[dict]:
        """Get recent posts from a profile's activity page."""
        activity_url = profile_url.rstrip("/") + "/recent-activity/all/"
        await self.page.goto(activity_url, wait_until="domcontentloaded")
        await _async_human_delay(2, 4)

        posts = []
        post_els = await self.page.query_selector_all(".feed-shared-update-v2")

        for el in post_els[:max_posts]:
            try:
                text_el = await el.query_selector(".feed-shared-text span[dir='ltr']")
                text = (await text_el.inner_text()).strip() if text_el else ""

                # Get post URL via share button aria
                post_url = ""
                try:
                    timestamp_el = await el.query_selector("a.app-aware-link[href*='activity']")
                    if timestamp_el:
                        post_url = await timestamp_el.get_attribute("href")
                        post_url = post_url.split("?")[0]
                except Exception:
                    pass

                if text:
                    posts.append({"text": text, "url": post_url, "element": el})
            except Exception:
                continue

        return posts

    async def comment_on_post(self, post_element, comment_text: str) -> bool:
        """Click comment box on a post element and submit a comment."""
        try:
            comment_btn = await post_element.query_selector("button.comment-button")
            if not comment_btn:
                comment_btn = await post_element.query_selector('button[aria-label*="comment"]')
            if comment_btn:
                await comment_btn.click()
                await _async_human_delay(1, 2)

            editor = await post_element.query_selector(".ql-editor")
            if not editor:
                editor = await post_element.query_selector("[contenteditable='true']")
            if editor:
                await editor.click()
                await asyncio.sleep(0.5)
                for char in comment_text:
                    await self.page.keyboard.type(char)
                    await asyncio.sleep(random.uniform(0.04, 0.12))
                await _async_human_delay(1, 2)
                await self.page.keyboard.press("Control+Return")
                await _async_human_delay(2, 3)
                return True
        except Exception as e:
            print(f"    [!] Comment error: {e}")
        return False

    async def get_comments_on_your_post(self, post_url: str) -> list[dict]:
        """Visit your own post and collect comments to reply to."""
        await self.page.goto(post_url, wait_until="domcontentloaded")
        await _async_human_delay(2, 4)

        comments = []
        comment_els = await self.page.query_selector_all(".comments-comment-item")

        for el in comment_els:
            try:
                name_el = await el.query_selector(".comments-post-meta__name-text")
                name = (await name_el.inner_text()).strip() if name_el else "Someone"

                text_el = await el.query_selector(".comments-comment-item__main-content span[dir='ltr']")
                text = (await text_el.inner_text()).strip() if text_el else ""

                if text:
                    comments.append({"name": name, "text": text, "element": el})
            except Exception:
                continue

        return comments

    async def reply_to_comment(self, comment_element, reply_text: str) -> bool:
        """Click Reply on a comment and post the reply."""
        try:
            reply_btn = await comment_element.query_selector('button[aria-label*="Reply"]')
            if not reply_btn:
                reply_btn = await comment_element.query_selector(".comments-comment-social-bar__reply-action-button")
            if reply_btn:
                await reply_btn.click()
                await _async_human_delay(1, 2)

            editor = await comment_element.query_selector("[contenteditable='true']")
            if editor:
                await editor.click()
                await asyncio.sleep(0.3)
                for char in reply_text:
                    await self.page.keyboard.type(char)
                    await asyncio.sleep(random.uniform(0.04, 0.12))
                await _async_human_delay(1, 2)
                await self.page.keyboard.press("Control+Return")
                await _async_human_delay(2, 3)
                return True
        except Exception as e:
            print(f"    [!] Reply error: {e}")
        return False
