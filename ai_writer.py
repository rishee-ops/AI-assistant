"""
Uses Claude to write humanized LinkedIn comments and replies.
Every comment reads like a real person sharing a genuine opinion —
not a bot, not a generic "Great post!", not salesy.
"""

import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _ask(prompt: str) -> str:
    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def write_post_comment(icp: dict, profile: dict, post_text: str) -> str:
    """
    Write a humanized, opinionated comment on someone's LinkedIn post.
    Sounds like a knowledgeable professional, not a bot.
    """
    prompt = f"""
You are writing a LinkedIn comment as {icp['company_name']}, a real professional
with genuine experience in {', '.join(icp['target_industries'][:2])}.

Read the post carefully and write a comment that:
- Opens with a specific reaction to something actually said in the post (not "Great post!")
- Shares a real opinion, counter-point, or lived experience — something that adds to the conversation
- Is 2-4 sentences, written in a natural, conversational tone — like texting a smart colleague
- Ends with either a follow-up thought or a genuine question that invites dialogue
- Uses no hashtags, no emojis, no corporate buzzwords like "leverage" or "synergy"
- Does NOT mention your company or pitch anything
- Reads like it was written by a thoughtful human who actually read the post

Post by {profile.get('name', 'someone')} ({profile.get('title', '')}):
\"\"\"{post_text[:1000]}\"\"\"

Write ONLY the comment. No labels, no quotes around it.
"""
    return _ask(prompt)


def write_reply_to_comment(icp: dict, commenter_name: str, comment_text: str, your_post_text: str) -> str:
    """
    Reply to someone who commented on your post.
    Warm, engaged, continues the conversation naturally.
    """
    prompt = f"""
You are {icp['company_name']} replying to a comment on your LinkedIn post.

Write a reply that:
- Directly engages with what {commenter_name} actually said — no generic "Thanks for sharing!"
- Either builds on their point, respectfully challenges it, or adds a new angle
- Feels like a real back-and-forth conversation, not a PR response
- Is 2-3 sentences max, natural and warm
- No hashtags, no emojis, no buzzwords

Your post:
\"\"\"{your_post_text[:400]}\"\"\"

{commenter_name} wrote:
\"\"\"{comment_text[:400]}\"\"\"

Write ONLY the reply. No labels, no quotes.
"""
    return _ask(prompt)


def score_profile(icp: dict, profile: dict) -> int:
    """Score a LinkedIn profile 0–100 for ICP fit. Returns integer."""
    prompt = f"""
Score this LinkedIn profile from 0 to 100 based on how well it fits the target audience below.
Return ONLY the integer. No explanation.

Target audience:
- Industries: {icp['target_industries']}
- Job titles: {icp['target_job_titles']}
- Context: {icp['value_proposition']}

Profile:
- Title: {profile.get('title', '')}
- Company: {profile.get('company', '')}
- Headline: {profile.get('headline', '')}
- About: {profile.get('about', '')[:300]}
"""
    try:
        return int(_ask(prompt))
    except ValueError:
        return 50


def build_icp_from_profile(profile: dict) -> dict:
    """Build ICP by analysing the user's own LinkedIn profile data."""
    import json
    prompt = f"""
You are a LinkedIn growth strategist. Based on this professional's LinkedIn profile,
identify who they should be connecting with to grow their network and opportunities.

Return ONLY valid JSON with exactly these keys:
{{
  "target_industries": ["2-3 most relevant industries"],
  "target_job_titles": ["4-6 job titles of people worth connecting with"],
  "target_keywords": ["4 LinkedIn search keywords to find those people"],
  "pain_points": ["problems this person's background can help solve"],
  "value_proposition": "one sentence on what value this person offers",
  "tone": "professional",
  "company_name": "{profile.get('name', 'Rishee Rhudra')}",
  "product_summary": "2 sentence summary of their professional background"
}}

Profile:
Name: {profile.get('name', '')}
Headline: {profile.get('headline', '')}
About: {profile.get('about', '')[:1000]}
Experience: {profile.get('experience', '')[:500]}
"""
    raw = _ask(prompt)
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
