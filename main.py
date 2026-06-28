"""
LinkedIn AI Outreach Agent
--------------------------
Usage:
    python main.py --dossier uploads/your_dossier.pdf
    python main.py --dossier uploads/your_dossier.pdf --your-posts "https://..." "https://..."

Flow:
    1. Parse PDF → build ICP with OpenAI
    2. Search LinkedIn for matching profiles
    3. Score & rank profiles
    4. Show you the full plan (who + what will be sent)
    5. You press Y to approve → it runs everything automatically
"""

import asyncio
import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from config import (
    LINKEDIN_EMAIL, LINKEDIN_PASSWORD, OPENAI_API_KEY,
    MAX_PROFILES_PER_KEYWORD, MIN_ICP_SCORE,
    MAX_CONNECTIONS_PER_RUN, MAX_COMMENTS_PER_RUN,
)
from dossier_parser import build_icp
from ai_writer import write_connection_note, write_post_comment, write_reply_to_comment, score_profile
from linkedin_browser import LinkedInBrowser

console = Console()


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
        console.print("Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)


def show_icp(icp: dict):
    console.print(Panel.fit(
        f"[bold cyan]Company:[/bold cyan] {icp['company_name']}\n"
        f"[bold cyan]Value Prop:[/bold cyan] {icp['value_proposition']}\n"
        f"[bold cyan]Industries:[/bold cyan] {', '.join(icp['target_industries'])}\n"
        f"[bold cyan]Job Titles:[/bold cyan] {', '.join(icp['target_job_titles'])}\n"
        f"[bold cyan]Keywords:[/bold cyan] {', '.join(icp['target_keywords'])}\n"
        f"[bold cyan]Tone:[/bold cyan] {icp['tone']}",
        title="[green]Ideal Customer Profile extracted from dossier[/green]",
    ))


def show_plan(candidates: list[dict]):
    table = Table(title="Action Plan — Review Before Approving", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Name", style="bold")
    table.add_column("Title")
    table.add_column("Score", justify="center")
    table.add_column("Action")
    table.add_column("Message preview", max_width=50)

    for i, c in enumerate(candidates, 1):
        action = "Connect + Comment" if c.get("posts") else "Connect"
        table.add_row(
            str(i),
            c["profile"]["name"],
            c["profile"]["title"],
            str(c["score"]),
            action,
            c["connection_note"][:80] + "...",
        )

    console.print(table)


async def gather_candidates(browser: LinkedInBrowser, icp: dict) -> list[dict]:
    """Search LinkedIn, score profiles, generate messages — return ranked list."""
    candidates = []
    seen_urls = set()

    keywords = icp["target_keywords"][:4]  # limit searches

    for keyword in keywords:
        console.print(f"  Searching: [cyan]{keyword}[/cyan]")
        profiles = await browser.search_profiles(keyword, MAX_PROFILES_PER_KEYWORD)

        for profile in profiles:
            if profile["url"] in seen_urls:
                continue
            seen_urls.add(profile["url"])

            # Score the profile
            score = score_profile(icp, profile)
            if score < MIN_ICP_SCORE:
                continue

            # Get more profile detail
            details = await browser.get_profile_details(profile["url"])
            profile.update(details)

            # Write connection note
            note = write_connection_note(icp, profile)

            # Get recent posts
            posts = await browser.get_profile_recent_posts(profile["url"], max_posts=2)

            # Write comments for each post
            for post in posts:
                post["comment"] = write_post_comment(icp, profile, post["text"])

            candidates.append({
                "profile": profile,
                "score": score,
                "connection_note": note,
                "posts": posts,
            })

            if len(candidates) >= MAX_CONNECTIONS_PER_RUN:
                break

        if len(candidates) >= MAX_CONNECTIONS_PER_RUN:
            break

    # Sort by score descending
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:MAX_CONNECTIONS_PER_RUN]


async def handle_your_posts(browser: LinkedInBrowser, icp: dict, post_urls: list[str], your_post_text: str = ""):
    """Reply to comments on your own posts."""
    replied = 0
    for post_url in post_urls:
        if replied >= MAX_COMMENTS_PER_RUN:
            break
        console.print(f"\n[cyan]Checking your post:[/cyan] {post_url}")
        comments = await browser.get_comments_on_your_post(post_url)
        console.print(f"  Found {len(comments)} comment(s)")

        for comment in comments:
            if replied >= MAX_COMMENTS_PER_RUN:
                break
            reply = write_reply_to_comment(icp, comment["name"], comment["text"], your_post_text)
            console.print(f"  Replying to [bold]{comment['name']}[/bold]: {reply[:80]}...")
            ok = await browser.reply_to_comment(comment["element"], reply)
            status = "[green]OK[/green]" if ok else "[red]FAILED[/red]"
            console.print(f"  → {status}")
            replied += 1


async def run_outreach(candidates: list[dict], browser: LinkedInBrowser):
    """Execute the approved plan."""
    for i, c in enumerate(candidates, 1):
        profile = c["profile"]
        console.print(f"\n[bold]({i}/{len(candidates)}) {profile['name']}[/bold] — {profile['title']}")

        # Send connection request
        console.print(f"  Sending connection request...")
        ok = await browser.send_connection_request(profile["url"], c["connection_note"])
        console.print(f"  Connection: {'[green]sent[/green]' if ok else '[yellow]skipped/failed[/yellow]'}")

        # Comment on their posts
        for post in c.get("posts", []):
            console.print(f"  Commenting on post: {post['text'][:50]}...")
            ok = await browser.comment_on_post(post["element"], post["comment"])
            console.print(f"  Comment: {'[green]posted[/green]' if ok else '[yellow]failed[/yellow]'}")


async def main(dossier_path: str, your_post_urls: list[str]):
    validate_env()

    # ── Step 1: Parse dossier ──────────────────────────────────────────────
    console.print("\n[bold green]Step 1/4:[/bold green] Reading dossier...")
    icp = build_icp(dossier_path)
    show_icp(icp)

    # ── Step 2: Open LinkedIn ─────────────────────────────────────────────
    console.print("\n[bold green]Step 2/4:[/bold green] Opening LinkedIn...")
    browser = LinkedInBrowser(LINKEDIN_EMAIL, LINKEDIN_PASSWORD, headless=False)
    await browser.start()
    await browser.login()
    console.print("[green]  Logged in.[/green]")

    # ── Step 3: Find & score profiles, write messages ────────────────────
    console.print("\n[bold green]Step 3/4:[/bold green] Searching for target profiles...")
    candidates = await gather_candidates(browser, icp)
    console.print(f"\n  Found [bold]{len(candidates)}[/bold] matching profiles.\n")

    # ── Show plan and ask for approval ───────────────────────────────────
    show_plan(candidates)

    console.print("\n[bold yellow]Review the plan above.[/bold yellow]")
    console.print("Press [bold green]Y[/bold green] + Enter to run everything, or [bold red]N[/bold red] to cancel: ", end="")
    answer = input().strip().upper()

    if answer != "Y":
        console.print("[red]Cancelled.[/red]")
        await browser.stop()
        return

    # ── Step 4: Execute ───────────────────────────────────────────────────
    console.print("\n[bold green]Step 4/4:[/bold green] Running outreach...")
    await run_outreach(candidates, browser)

    # ── Handle replies on your own posts ─────────────────────────────────
    if your_post_urls:
        console.print("\n[bold green]Bonus:[/bold green] Replying to comments on your posts...")
        await handle_your_posts(browser, icp, your_post_urls)

    await browser.stop()
    console.print("\n[bold green]Done![/bold green] All actions completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LinkedIn AI Outreach Agent")
    parser.add_argument("--dossier", required=True, help="Path to your PDF dossier")
    parser.add_argument("--your-posts", nargs="*", default=[], help="Your LinkedIn post URLs to reply to comments on")
    args = parser.parse_args()

    if not Path(args.dossier).exists():
        console.print(f"[red]Dossier not found: {args.dossier}[/red]")
        sys.exit(1)

    asyncio.run(main(args.dossier, args.your_posts))
