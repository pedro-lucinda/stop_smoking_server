import json
import re
from datetime import date

from fastapi import HTTPException

# If you have openai>=1.x:
from openai import AsyncOpenAI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.motivation import DailyMotivation
from app.models.preference import Preference
from app.prompts.motivation import get_motivation_prompt
from app.schemas.motivation import DetailedMotivationOut

client = AsyncOpenAI(api_key=settings.openai_api_key)


async def generate_and_save_for_user(db: AsyncSession, user_id: int) -> DailyMotivation:
    """
    Generate today's motivation for a single user, store it (replacing
    any existing row for today), and return the DailyMotivation record.
    """
    # 1) load preference WITH goals eagerly to avoid async lazy-loads
    pref_res = await db.execute(
        select(Preference)
        .options(selectinload(Preference.goals))
        .where(Preference.user_id == user_id)
    )
    pref: Preference | None = pref_res.scalar_one_or_none()
    if not pref:
        raise HTTPException(
            status_code=400, detail=f"No preference set for user {user_id}"
        )

    today = date.today()

    # 2) delete stale row for today (idempotent)
    await db.execute(
        delete(DailyMotivation).where(
            DailyMotivation.user_id == user_id,
            DailyMotivation.date == today,
        )
    )

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

    # 4) build & call OpenAI (async)
    goal_descriptions = [g.description for g in (pref.goals or [])]
    prompt = get_motivation_prompt(
        intro, pref.reason, goal_descriptions, days, pref.language
    )

    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a caring, evidence-based coach."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2000,
        temperature=0.7,
    )

    raw = resp.choices[0].message.content.strip()
    clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE)

    try:
        data = json.loads(clean)
        mot = DetailedMotivationOut.model_validate(data)
    except Exception as e:
        raise HTTPException(status_code=502, detail="Invalid model response") from e

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
    await db.commit()
    await db.refresh(record)
    return record
