"""
Scheduler — runs the posting and reply loops on a time-based cadence.
Uses APScheduler so it works as a long-running process without cron.
"""

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import POST_HOURS, REPLY_CHECK_INTERVAL_MIN, REPLY_SCAN_LIMIT
from content_generator import generate_post, generate_reply
from browser import reddit_session, submit_post, get_recent_posts, get_unanswered_comments, post_reply
from post_logger import log_post, log_reply, already_replied_today, posts_today

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

MAX_POSTS_PER_DAY = 3


def run_post_job():
    """Generate and publish one post."""
    if posts_today() >= MAX_POSTS_PER_DAY:
        logger.info("Daily post limit reached, skipping.")
        return

    logger.info("Generating post content...")
    post_data = generate_post()
    title = post_data["title"]
    body = post_data["body"]
    post_type = post_data["post_type"]

    logger.info(f"Posting [{post_type}]: {title[:70]}")
    with reddit_session() as page:
        url = submit_post(page, title, body)
    log_post(title, url, post_type)
    logger.info(f"Done. Post live at: {url}")


def run_reply_job():
    """Scan recent posts and reply to unanswered comments."""
    logger.info("Scanning for reply opportunities...")
    with reddit_session() as page:
        posts = get_recent_posts(page, limit=REPLY_SCAN_LIMIT)
        replied = 0
        for post in posts:
            if already_replied_today(post["url"]):
                continue
            comments = get_unanswered_comments(page, post["url"])
            if not comments:
                continue
            # Reply to at most one comment per post per run
            comment = comments[0]
            reply_text = generate_reply(
                post_title=post["title"],
                post_body=comment.get("post_body", ""),
                comment_text=comment["text"],
            )
            success = post_reply(page, post["url"], comment["element_id"], reply_text)
            if success:
                log_reply(post["url"], comment["text"])
                replied += 1
            if replied >= 5:  # cap replies per run to stay safe
                break
    logger.info(f"Reply run done. Replied to {replied} comments.")


def start():
    sched = BlockingScheduler(timezone="UTC")

    # Post jobs at configured hours
    for hour in POST_HOURS:
        sched.add_job(
            run_post_job,
            trigger=CronTrigger(hour=hour, minute=0),
            id=f"post_{hour}h",
            name=f"Reddit post at {hour:02d}:00 UTC",
            misfire_grace_time=300,
        )

    # Reply job runs on interval
    sched.add_job(
        run_reply_job,
        trigger="interval",
        minutes=REPLY_CHECK_INTERVAL_MIN,
        id="reply_scan",
        name="Reddit reply scanner",
        misfire_grace_time=120,
    )

    logger.info(
        f"Scheduler started.\n"
        f"  Post hours (UTC): {POST_HOURS}\n"
        f"  Reply check every: {REPLY_CHECK_INTERVAL_MIN} min"
    )
    sched.start()


if __name__ == "__main__":
    start()
