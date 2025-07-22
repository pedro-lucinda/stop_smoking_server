import json
import re
from datetime import date

import openai
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.motivation import DailyMotivation
from app.models.preference import Preference
from app.prompts.motivation import get_motivation_prompt
from app.schemas.motivation import DetailedMotivationOut

openai.api_key = settings.openai_api_key


def generate_and_save_for_user(db: Session, user_id: int) -> DailyMotivation:
    """
    Generate today's motivation for a single user, store it (replacing
    any existing row for today), and return the DailyMotivation record.
    """
    # 1) load preference
    pref: Preference = db.query(Preference).filter_by(user_id=user_id).first()
    if not pref:
        raise ValueError(f"No preference set for user {user_id}")

    today = date.today()
    # 2) delete stale
    db.query(DailyMotivation).filter_by(user_id=user_id, date=today).delete()

    # 3) compute progress intro
    days = (today - pref.quit_date).days
    if days < 0:
        intro = (
            f"Your quit date is coming up in {-days} days. "
            "Use this time to prepare—visualize your success and set healthy routines."
        )
    elif days == 0:
        intro = (
            "Your quit date is today; there are no measurable health "
            "improvements yet, but this marks the very first step toward "
            "long-term well-being."
        )
    else:
        intro = (
            f"After {days} days smoke-free, significant health improvements "
            "include enhanced lung function and a steadier heart rate."
        )

    # 4) build & call OpenAI
    prompt = get_motivation_prompt(
        intro, pref.reason, [g.description for g in pref.goals], days, pref.language
    )
    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a caring, evidence-based coach."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=700,
        temperature=0.7,
    )
    raw = resp.choices[0].message.content.strip()
    clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE)
    data = json.loads(clean)
    mot = DetailedMotivationOut.model_validate(data)

    # 5) persist
    record = DailyMotivation(
        user_id=user_id,
        date=today,
        progress=mot.progress,
        motivation=mot.motivation,
        cravings=mot.cravings,
        ideas=mot.ideas,
        recommendations=mot.recommendations,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
