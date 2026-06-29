"""
Builds an ICP either from a PDF dossier or from the user's own LinkedIn profile data.
"""

import json
import pdfplumber
from openai import OpenAI
from config import OPENAI_API_KEY


client = OpenAI(api_key=OPENAI_API_KEY)


def extract_pdf_text(pdf_path: str) -> str:
    text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text.append(t)
    return "\n".join(text)


def build_icp(pdf_path: str) -> dict:
    """Parse dossier and return structured ICP dict."""
    raw_text = extract_pdf_text(pdf_path)
    if not raw_text.strip():
        raise ValueError("Could not extract any text from the PDF.")

    prompt = f"""
You are a B2B sales strategist. Read the following business dossier and extract a
structured Ideal Customer Profile (ICP).

Return ONLY valid JSON with these exact keys:
{{
  "target_industries": ["list of industries"],
  "target_job_titles": ["list of job titles to connect with"],
  "target_keywords": ["keywords to search on LinkedIn"],
  "pain_points": ["pain points this product/service solves"],
  "value_proposition": "one sentence value prop",
  "tone": "professional | friendly | formal",
  "company_name": "name of the company from the dossier",
  "product_summary": "2-3 sentence summary of what they offer"
}}

DOSSIER:
{raw_text[:6000]}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def build_icp_from_profile(profile: dict) -> dict:
    """Build ICP by analysing the user's own LinkedIn profile scraped data."""
    prompt = f"""
You are a LinkedIn outreach strategist. Based on this person's LinkedIn profile,
infer who they should be connecting with to grow their network and business.

Return ONLY valid JSON with these exact keys:
{{
  "target_industries": ["industries most relevant to reach out to"],
  "target_job_titles": ["job titles of people they should connect with"],
  "target_keywords": ["3-5 LinkedIn search keywords to find those people"],
  "pain_points": ["problems their background suggests they can help with"],
  "value_proposition": "one sentence on what value this person offers",
  "tone": "professional",
  "company_name": "{profile.get('name', 'the user')}",
  "product_summary": "brief summary of their professional background"
}}

PROFILE:
Name: {profile.get('name', '')}
Headline: {profile.get('headline', '')}
About: {profile.get('about', '')[:1000]}
Experience: {profile.get('experience', '')[:500]}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
