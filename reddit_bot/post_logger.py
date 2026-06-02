"""Tracks what the bot has posted to avoid duplicates and provide an audit trail."""

import json
import logging
from datetime import datetime
from pathlib import Path

from config import POST_LOG_PATH

logger = logging.getLogger(__name__)


def _load() -> list:
    path = Path(POST_LOG_PATH)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def _save(log: list):
    Path(POST_LOG_PATH).write_text(
        json.dumps(log, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def log_post(title: str, url: str, post_type: str):
    log = _load()
    log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "type": "post",
        "post_type": post_type,
        "title": title,
        "url": url,
    })
    _save(log)
    logger.info(f"Logged post: {title[:60]}")


def log_reply(post_url: str, comment_snippet: str):
    log = _load()
    log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "type": "reply",
        "post_url": post_url,
        "comment_snippet": comment_snippet[:100],
    })
    _save(log)


def already_replied_today(post_url: str) -> bool:
    """Prevent replying to the same post more than once per day."""
    today = datetime.utcnow().date().isoformat()
    for entry in _load():
        if (
            entry.get("type") == "reply"
            and entry.get("post_url") == post_url
            and entry.get("timestamp", "").startswith(today)
        ):
            return True
    return False


def posts_today() -> int:
    today = datetime.utcnow().date().isoformat()
    return sum(
        1 for e in _load()
        if e.get("type") == "post" and e.get("timestamp", "").startswith(today)
    )


def print_summary():
    log = _load()
    posts = [e for e in log if e.get("type") == "post"]
    replies = [e for e in log if e.get("type") == "reply"]
    print(f"\n{'='*50}")
    print(f"Bot activity summary")
    print(f"{'='*50}")
    print(f"Total posts:   {len(posts)}")
    print(f"Total replies: {len(replies)}")
    if posts:
        print(f"\nLast 5 posts:")
        for p in posts[-5:]:
            print(f"  [{p['timestamp'][:10]}] {p['title'][:60]}")
    print(f"{'='*50}\n")
