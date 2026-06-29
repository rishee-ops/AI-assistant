"""
LinkedIn AI Outreach Agent
--------------------------
Usage:
    python main.py
    python main.py --your-posts "https://..." "https://..."

Flow:
    1. Log into LinkedIn (browser opens, session saved after first login)
    2. Scrape YOUR profile (Rishee Rhudr) to understand your background
    3. AI builds an ICP from your profile
    4. Search LinkedIn for matching people
    5. Show you the full plan — who will get a connection request
    6. You press Y → sends 20 connection requests (no note, free account)
    7. Then visits each connected profile's recent posts and comments
    8. Optionally replies to comments on your own posts
"""

import asyncio
import argparse
import sys

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from config import (
    LINKEDIN_EMAIL, LINKEDIN_PASSWORD, OPENAI_API_KEY,
    MAX_PROFILES_PER_KEYWORD, MIN_ICP_SCORE,
    MAX_CONNECTIONS_PER_RUN, MAX_COMMENTS_PER_RUN,
)
from dossier_parser import build_icp_from_profile
from ai_writer import write_post_comment, write_reply_to_comment, score_profile
from linkedin_browser import LinkedInBrowser

console = Console()

YOUR_LINKEDIN_NAME = "Rishee Rhudr"


def validate_env():
    missing = []
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if not LINKEDIN_EMAIL:
        missing.append("LINKEDIN_EMAIL")
    if not LINKEDIN_PASSWORD:
        missing.append("LINKEDIN_PASSWORD")
    if missing:
        console.print(f"[red]Missing .env values: {', '.join(missing)}[/red]")
        console.print("Edit .env and fill in your credentials.")
        sys.exit(1)


def show_icp(icp: dict):
    console.print(Panel.fit(
        f"[bold cyan]You:[/bold cyan] {icp['company_name']}\n"
        f"[bold cyan]Value Prop:[/bold cyan] {icp['value_proposition']}\n"
        f"[bold cyan]Target Industries:[/bold cyan] {', '.join(icp['target_industries'])}\n"
        f"[bold cyan]Target Titles:[/bold cyan] {', '.join(icp['target_job_titles'])}\n"
        f"[bold cyan]Search Keywords:[/bold cyan] {', '.join(icp['target_keywords'])}",
        title="[green]ICP built from your LinkedIn profile[/green]",
    ))


def show_plan(candidates: list[dict]):
    table = Table(title=f"Connection Plan — {len(candidates)} people", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Name", style="bold")
    table.add_column("Title")
    table.add_column("Company")
    table.add_column("Score", justify="center")
    table.add_column("Posts found", justify="center")

    for i, c in enumerate(candidates, 1):
        table.add_row(
            str(i),
            c["profile"]["name"],
            c["profile"]["title"],
            c["profile"]["company"],
            str(c["score"]),
            str(len(c.get("posts", []))),
        )
    console.print(table)


async def gather_candidates(browser: LinkedInBrowser, icp: dict) -> list[dict]:
    candidates = []
    seen_urls = set()

    for keyword in icp["target_keywords"][:4]:
        console.print(f"  Searching: [cyan]{keyword}[/cyan]")
        profiles = await browser.search_profiles(keyword, MAX_PROFILES_PER_KEYWORD)

        for profile in profiles:
            if profile["url"] in seen_urls:
                continue
            seen_urls.add(profile["url"])

            score = score_profile(icp, profile)
            if score < MIN_ICP_SCORE:
                continue

            details = await browser.get_profile_details(profile["url"])
            profile.update(details)

            posts = await browser.get_profile_recent_posts(profile["url"], max_posts=2)
            for post in posts:
                post["comment"] = write_post_comment(icp, profile, post["text"])

            candidates.append({
                "profile": profile,
                "score": score,
                "posts": posts,
            })

            console.print(f"  [green]+[/green] {profile['name']} ({profile['title']}) — score {score}")

            if len(candidates) >= MAX_CONNECTIONS_PER_RUN:
                break

        if len(candidates) >= MAX_CONNECTIONS_PER_RUN:
            break

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:MAX_CONNECTIONS_PER_RUN]


async def run_connections(candidates: list[dict], browser: LinkedInBrowser):
    console.print("\n[bold yellow]Phase 1: Sending connection requests...[/bold yellow]")
    for i, c in enumerate(candidates, 1):
        profile = c["profile"]
        console.print(f"  ({i}/{len(candidates)}) Connecting with [bold]{profile['name']}[/bold]...")
        ok = await browser.send_connection_request(profile["url"])
        console.print(f"    → {'[green]sent[/green]' if ok else '[yellow]skipped/already connected[/yellow]'}")


async def run_comments(candidates: list[dict], browser: LinkedInBrowser):
    console.print("\n[bold yellow]Phase 2: Commenting on their posts...[/bold yellow]")
    commented = 0
    for c in candidates:
        profile = c["profile"]
        for post in c.get("posts", []):
            if commented >= MAX_COMMENTS_PER_RUN:
                break
            console.print(f"  Commenting on [bold]{profile['name']}[/bold]'s post: {post['text'][:60]}...")
            ok = await browser.comment_on_post(post["element"], post["comment"])
            console.print(f"    → {'[green]commented[/green]' if ok else '[yellow]failed[/yellow]'}")
            if ok:
                commented += 1
        if commented >= MAX_COMMENTS_PER_RUN:
            break


async def handle_your_posts(browser: LinkedInBrowser, icp: dict, post_urls: list[str]):
    console.print("\n[bold yellow]Phase 3: Replying to comments on your posts...[/bold yellow]")
    replied = 0
    for post_url in post_urls:
        comments = await browser.get_comments_on_your_post(post_url)
        console.print(f"  Found {len(comments)} comment(s) on {post_url}")
        for comment in comments:
            if replied >= MAX_COMMENTS_PER_RUN:
                break
            reply = write_reply_to_comment(icp, comment["name"], comment["text"], "")
            console.print(f"  Replying to [bold]{comment['name']}[/bold]: {reply[:80]}...")
            ok = await browser.reply_to_comment(comment["element"], reply)
            console.print(f"    → {'[green]replied[/green]' if ok else '[yellow]failed[/yellow]'}")
            if ok:
                replied += 1


async def main(your_post_urls: list[str]):
    validate_env()

    browser = LinkedInBrowser(LINKEDIN_EMAIL, LINKEDIN_PASSWORD, headless=False)
    await browser.start()

    # ── Login ────────────────────────────────────────────────────────────
    console.print("\n[bold green]Step 1/4:[/bold green] Logging into LinkedIn...")
    await browser.login()
    console.print("[green]  Logged in.[/green]")

    # ── Scrape your own profile ──────────────────────────────────────────
    console.print(f"\n[bold green]Step 2/4:[/bold green] Reading your profile ({YOUR_LINKEDIN_NAME})...")
    your_profile = await browser.scrape_own_profile(YOUR_LINKEDIN_NAME)
    console.print(f"  Found: [bold]{your_profile.get('name')}[/bold] — {your_profile.get('headline')}")

    # ── Build ICP from profile ───────────────────────────────────────────
    console.print("\n[bold green]Step 3/4:[/bold green] Building ICP from your profile...")
    icp = build_icp_from_profile(your_profile)
    show_icp(icp)

    # ── Find candidates ──────────────────────────────────────────────────
    console.print("\n[bold green]Step 4/4:[/bold green] Searching for people to connect with...")
    candidates = await gather_candidates(browser, icp)
    console.print(f"\n  Found [bold]{len(candidates)}[/bold] matching profiles.\n")

    if not candidates:
        console.print("[red]No suitable profiles found. Try adjusting MIN_ICP_SCORE in config.py.[/red]")
        await browser.stop()
        return

    # ── Show plan & get approval ─────────────────────────────────────────
    show_plan(candidates)
    console.print("\n[bold yellow]Review the plan above.[/bold yellow]")
    console.print("This will send [bold]connection requests[/bold] to all of them, then [bold]comment on their posts[/bold].")
    console.print("Press [bold green]Y[/bold green] + Enter to run, or [bold red]N[/bold red] to cancel: ", end="")
    answer = input().strip().upper()

    if answer != "Y":
        console.print("[red]Cancelled.[/red]")
        await browser.stop()
        return

    # ── Phase 1: Connections ─────────────────────────────────────────────
    await run_connections(candidates, browser)

    # ── Phase 2: Comments on their posts ────────────────────────────────
    await run_comments(candidates, browser)

    # ── Phase 3: Replies on your posts ──────────────────────────────────
    if your_post_urls:
        await handle_your_posts(browser, icp, your_post_urls)

    await browser.stop()
    console.print("\n[bold green]All done![/bold green]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LinkedIn AI Outreach Agent")
    parser.add_argument(
        "--your-posts", nargs="*", default=[],
        help="Your LinkedIn post URLs to reply to comments on"
    )
    args = parser.parse_args()
    asyncio.run(main(args.your_posts))
