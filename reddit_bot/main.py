"""
Entry point for the Reddit bot.

Usage:
    python main.py post        # Generate and publish one post right now
    python main.py reply       # Scan and reply to comments right now
    python main.py schedule    # Start the full scheduler (long-running)
    python main.py summary     # Print activity log summary
    python main.py preview     # Preview a generated post (no posting)
"""

import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

HELP = __doc__


def cmd_post():
    from scheduler import run_post_job
    run_post_job()


def cmd_reply():
    from scheduler import run_reply_job
    run_reply_job()


def cmd_schedule():
    from scheduler import start
    start()


def cmd_summary():
    from post_logger import print_summary
    print_summary()


def cmd_preview():
    """Preview a generated post without publishing it."""
    from content_generator import generate_post
    print("\nGenerating preview post...\n")
    post = generate_post()
    print(f"{'='*60}")
    print(f"POST TYPE : {post['post_type'].upper()}")
    print(f"{'='*60}")
    print(f"TITLE:\n{post['title']}\n")
    print(f"BODY:\n{post['body']}")
    print(f"{'='*60}\n")


COMMANDS = {
    "post": cmd_post,
    "reply": cmd_reply,
    "schedule": cmd_schedule,
    "summary": cmd_summary,
    "preview": cmd_preview,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(HELP)
        sys.exit(1)
    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()
