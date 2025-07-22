def get_motivation_prompt(
    progress_intro: str,
    reason: str,
    goal_texts: list[str],
    days_smoke_free: int,
    language: str,
) -> str:
    """
    Build the GPT prompt for daily detailed motivation.

    Args:
        progress_intro: default progress text for days > 0
        reason: user's quit-smoking reason
        goal_texts: list of goal descriptions
        days_smoke_free: number of days since quit_date (can be 0 or negative)
    """
    # 1) Handle day-0 case
    if days_smoke_free == 0:
        progress_section = (
            "Your quit date is today; there are no measurable health "
            "improvements yet, but this marks the very first step toward "
            "long-term well-being."
        )
    else:
        progress_section = progress_intro

    # 2) JSON template (escaped braces)
    template = (
        '{{"progress": "...", "motivation": "...", '
        '"cravings": "...", "ideas": "...", "recommendations": "..."}}'
    )

    # 3) Full prompt
    prompt = f"""
You are an expert smoking-cessation coach. Produce a JSON object with exactly these keys:
progress, motivation, cravings, ideas, recommendations. It should be in the language {language}.

{template}

1. progress: {progress_section}
   Cite at least *two* different recent (past 6 months) peer-reviewed medical publications
   or authoritative health sources (e.g. 'Smith et al., Journal of Respiratory Medicine, March 2025',
   'HealthOrg April 2025').

2. motivation: A heartfelt, personalized encouragement based on the user's reason (“{reason}”)
   and goals ({', '.join(goal_texts)}). Cite at least *two* recent psychology studies
   or expert articles (e.g. 'Zheng et al., Journal of Smoking Cessation, Nov 2024',
   'PsychHealth May 2025').

3. cravings: Practical strategies to handle cravings, **including at least two mindfulness techniques**
   (e.g. mindful breathing, body scan).

4. ideas: Creative activities or habit-replacements to keep momentum, with a brief rationale.

5. recommendations: Other evidence-based tips—*do NOT* suggest using any external apps.

Return only valid JSON—no extra explanation or text.
"""
    return prompt
