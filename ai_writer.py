"""
Uses OpenAI to write personalized LinkedIn messages, post comments, and
replies to comments on the user's own posts — all based on ICP + context.
"""

from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def _chat(prompt: str, temperature: float = 0.7) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def write_connection_note(icp: dict, profile: dict) -> str:
    """Write a personalized connection request note (max 300 chars)."""
    prompt = f"""
Write a LinkedIn connection request note. Keep it under 280 characters.
Be human, warm, not salesy. Reference something specific from their profile.

Your company: {icp['company_name']}
What you offer: {icp['value_proposition']}
Tone: {icp['tone']}

Their profile:
- Name: {profile.get('name', 'there')}
- Title: {profile.get('title', '')}
- Company: {profile.get('company', '')}
- Headline: {profile.get('headline', '')}

Write ONLY the note text, no quotes, no labels.
"""
    return _chat(prompt, temperature=0.8)


def write_post_comment(icp: dict, profile: dict, post_text: str) -> str:
    """Write a thoughtful comment on someone's LinkedIn post."""
    prompt = f"""
Write a genuine, insightful LinkedIn comment on the post below.
- Sound like a real person, not a bot
- Add value: share a perspective, ask a smart question, or validate with experience
- Max 3 sentences
- Tone: {icp['tone']}
- You represent: {icp['company_name']} ({icp['value_proposition']})
- Post author: {profile.get('name', '')} ({profile.get('title', '')})

POST:
{post_text[:800]}

Write ONLY the comment text.
"""
    return _chat(prompt, temperature=0.85)


def write_reply_to_comment(icp: dict, commenter_name: str, comment_text: str, your_post_text: str) -> str:
    """Write a reply to someone who commented on YOUR post."""
    prompt = f"""
Someone commented on your LinkedIn post. Write a warm, engaging reply.
- Be conversational and genuine
- Max 2-3 sentences
- Tone: {icp['tone']}
- You are: {icp['company_name']}

Your original post:
{your_post_text[:400]}

{commenter_name} commented:
{comment_text[:400]}

Write ONLY the reply text.
"""
    return _chat(prompt, temperature=0.85)


def score_profile(icp: dict, profile: dict) -> int:
    """Score a LinkedIn profile 0-100 for ICP fit."""
    prompt = f"""
Score this LinkedIn profile from 0 to 100 for fit with the Ideal Customer Profile.
Return ONLY the integer score, nothing else.

ICP:
- Target industries: {icp['target_industries']}
- Target job titles: {icp['target_job_titles']}
- Pain points solved: {icp['pain_points']}

Profile:
- Title: {profile.get('title', '')}
- Company: {profile.get('company', '')}
- Headline: {profile.get('headline', '')}
- About: {profile.get('about', '')[:300]}
"""
    try:
        return int(_chat(prompt, temperature=0.1))
    except ValueError:
        return 50
