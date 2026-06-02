"""
Generates post content and replies using Claude AI,
guided by the user's personal style guide and SEO-optimized templates.
"""

import random
import re
from datetime import datetime
from pathlib import Path

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, STYLE_GUIDE_PATH, SUBREDDIT
from templates import TEMPLATES, TEMPLATE_WEIGHTS


def _load_style_guide() -> str:
    path = Path(STYLE_GUIDE_PATH)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _pick_template() -> dict:
    """Weighted-random template selection."""
    pool = []
    for t in TEMPLATES:
        weight = TEMPLATE_WEIGHTS.get(t["type"], 10)
        pool.extend([t] * weight)
    return random.choice(pool)


def _system_prompt(style_guide: str) -> str:
    return f"""You are a Reddit content writer for r/{SUBREDDIT}, a community about landing and thriving in remote jobs.

Your posts must:
- Sound like a real person sharing genuine experience (not marketing copy)
- Be conversational, direct, and occasionally use casual language
- Include specific details, numbers, and examples — vagueness kills credibility
- End with a question or call to action to drive comments (comments = Google ranking signal)
- Be SEO-smart: titles should mirror real Google search queries naturally
- Never use buzzwords like "revolutionize", "game-changer", "synergy", or "leverage"
- Vary sentence length. Mix short punchy lines with longer ones.

**The community (r/{SUBREDDIT}):**
- People trying to find, land, or succeed in remote work
- Mix of job seekers, remote employees, and some remote managers
- Values: authentic advice, real experience, practical tips
- Tone: helpful, honest, sometimes blunt, low BS tolerance

**Writing style to match (from the owner's examples):**
{style_guide if style_guide else "No examples provided yet — use the community tone described above."}
"""


def generate_post() -> dict:
    """
    Generate a complete Reddit post (title + body).
    Returns {"title": str, "body": str, "post_type": str}
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    style_guide = _load_style_guide()
    template = _pick_template()
    now = datetime.now()

    user_message = f"""Generate a Reddit post for r/{SUBREDDIT} using this template as a guide.

**Template type:** {template['type']}
**Title pattern:** {template['title_pattern']}
**Body pattern:** {template['body_pattern']}
**SEO keywords to weave in naturally:** {', '.join(template['seo_keywords'])}
**Current month/year:** {now.strftime('%B %Y')}

Instructions:
- Fill in all {{variables}} with specific, believable content
- The title must be a natural sentence someone would actually Google
- Body should be 150-300 words — enough to be valuable, short enough to read
- End with a genuine question to prompt comments
- Return ONLY a JSON object with keys "title" and "body" — no other text

Example format:
{{"title": "...", "body": "..."}}"""

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=_system_prompt(style_guide),
        messages=[{"role": "user", "content": user_message}],
    )

    raw = message.content[0].text.strip()
    # Extract JSON even if model wraps it in markdown code blocks
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if json_match:
        import json
        data = json.loads(json_match.group())
        return {
            "title": data.get("title", ""),
            "body": data.get("body", ""),
            "post_type": template["type"],
        }

    raise ValueError(f"Could not parse post from model response:\n{raw}")


def generate_reply(post_title: str, post_body: str, comment_text: str) -> str:
    """
    Generate a reply to a comment on a post.
    Returns the reply text as a string.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    style_guide = _load_style_guide()

    user_message = f"""Write a Reddit reply for r/{SUBREDDIT}.

**Post title:** {post_title}
**Post body (excerpt):** {post_body[:400]}
**Comment to reply to:** {comment_text}

Instructions:
- Add genuine value — a tip, a personal experience, a useful question, or a clear answer
- Match the energy and tone of the comment
- 2-5 sentences max. Reddit replies should be tight.
- Don't start with "I", "Great", "Thanks", or anything sycophantic
- Return ONLY the reply text, nothing else"""

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=256,
        system=_system_prompt(style_guide),
        messages=[{"role": "user", "content": user_message}],
    )

    return message.content[0].text.strip()
