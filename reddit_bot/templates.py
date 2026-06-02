"""
Post templates for r/Landremotejobs.
Each template targets a high-SEO thread type that ranks well on Google.
Variables wrapped in {curly_braces} are filled by the content generator.
"""

TEMPLATES = [
    # --- TIPS & HOW-TO (highest Google ranking potential) ---
    {
        "type": "tips",
        "title_pattern": "{number} remote job search mistakes that are costing you interviews (and how to fix them)",
        "body_pattern": (
            "I've been in the remote hiring space for a while and I keep seeing the same patterns. "
            "Here are the mistakes that quietly kill your chances:\n\n"
            "{tips_list}\n\n"
            "What would you add to this list? Curious what others have seen."
        ),
        "seo_keywords": ["remote job search", "remote job mistakes", "land remote job"],
    },
    {
        "type": "tips",
        "title_pattern": "How I landed a {role} remote role in {timeframe} — full breakdown",
        "body_pattern": (
            "Sharing this because I wish I had this roadmap when I started.\n\n"
            "**Background:** {background}\n\n"
            "**What I did differently:** {strategy}\n\n"
            "**The timeline:** {timeline}\n\n"
            "**Tools/resources that actually helped:** {tools}\n\n"
            "Ask me anything."
        ),
        "seo_keywords": ["how to land remote job", "remote job tips", "remote work"],
    },
    # --- DISCUSSION STARTERS (high engagement = Google signal) ---
    {
        "type": "discussion",
        "title_pattern": "What's the most underrated skill for landing remote jobs in {year}?",
        "body_pattern": (
            "I'll start: async communication. Being able to write a clear, "
            "complete Slack message or email that doesn't require 3 follow-ups is "
            "genuinely rare and hiring managers notice it immediately.\n\n"
            "What do you think? What skill do you wish more people talked about?"
        ),
        "seo_keywords": ["remote job skills", "remote work skills 2026", "land remote job"],
    },
    {
        "type": "discussion",
        "title_pattern": "If you've managed a remote team, share your worst hiring mistake (and what you learned)",
        "body_pattern": (
            "I'm asking because understanding what managers dread helps job seekers "
            "position themselves better.\n\n"
            "I'll go first: {personal_example}\n\n"
            "What's yours?"
        ),
        "seo_keywords": ["remote team management", "remote hiring", "remote work mistakes"],
    },
    # --- SUCCESS STORIES (community trust builders) ---
    {
        "type": "success_story",
        "title_pattern": "Weekly wins thread — drop your remote job victories here ({month} {year})",
        "body_pattern": (
            "Every week I see people quietly succeeding in this community and never sharing it. "
            "Let's change that.\n\n"
            "Drop your win below — big or small. Got an interview? Negotiated better pay? "
            "Finally heard back after 3 months of silence? All wins count.\n\n"
            "I'll start: {personal_win}"
        ),
        "seo_keywords": ["remote job wins", "remote job success", "land remote work"],
    },
    # --- COMPARISON / RESOURCE (best for evergreen Google traffic) ---
    {
        "type": "resource",
        "title_pattern": "Best platforms to find remote jobs in {year} — honest breakdown after trying them all",
        "body_pattern": (
            "I've spent the last {months} months testing every major remote job board. "
            "Here's my honest take:\n\n"
            "{platform_breakdown}\n\n"
            "**Bottom line:** {conclusion}\n\n"
            "Happy to go deeper on any of these if you have questions."
        ),
        "seo_keywords": ["best remote job sites", "remote job boards", "find remote jobs 2026"],
    },
    {
        "type": "resource",
        "title_pattern": "Remote job interview cheat sheet — questions they actually ask + how to answer",
        "body_pattern": (
            "After going through {number}+ remote interviews, these questions come up constantly:\n\n"
            "{questions_and_answers}\n\n"
            "Save this for your next interview. Feel free to add ones I missed."
        ),
        "seo_keywords": ["remote job interview questions", "remote interview tips", "work from home interview"],
    },
]

# Post type weights — adjust to control posting frequency per type
# Higher number = posts more often
TEMPLATE_WEIGHTS = {
    "tips": 35,
    "discussion": 30,
    "success_story": 20,
    "resource": 15,
}
