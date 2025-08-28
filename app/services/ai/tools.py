import logging
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from collections import Counter
import asyncio

from langchain_tavily import TavilySearch
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core import health as health_calc
from app.models.craving import Craving
from app.models.preference import Preference

logger = logging.getLogger(__name__)

# Search tool for general information
try:
    search = TavilySearch(max_results=3)  # Increased results for better context
    logger.info("Tavily search tool initialized")
except Exception as e:
    logger.error(f"Failed to initialize Tavily search: {e}")
    search = None

# Create async engine for tools
async_engine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)

# Domain-specific tools for smoking cessation

class HealthCalculatorInput(BaseModel):
    quit_date: str = Field(..., description="The date when the user quit smoking (YYYY-MM-DD)")
    cigarettes_per_day: Optional[int] = Field(None, description="Number of cigarettes smoked per day")

@tool
def calculate_health_improvements(quit_date: str, cigarettes_per_day: Optional[int] = None) -> str:
    """
    Summarize health improvements using the same formulas as the API (`app.core.health`).
    Inputs:
      - quit_date: YYYY-MM-DD
      - cigarettes_per_day: optional, to estimate money/time benefits
    """
    try:
        quit_dt = datetime.strptime(quit_date, "%Y-%m-%d").date()
    except Exception:
        return "Invalid quit_date. Use format YYYY-MM-DD."

    days_since_quit = (date.today() - quit_dt).days
    if days_since_quit < 0:
        return f"Your quit date is in the future ({-days_since_quit} days from now)."

    nicotine_expelled = health_calc.calculate_nicotine_expelled(days_since_quit)
    carbon_monoxide = health_calc.calculate_carbon_monoxide_level(days_since_quit)
    pulse_rate = health_calc.calculate_pulse_rate(days_since_quit)
    oxygen_levels = health_calc.calculate_oxygen_levels(days_since_quit)
    taste_smell = health_calc.calculate_taste_and_smell(days_since_quit)
    breathing = health_calc.calculate_breathing(days_since_quit)
    energy = health_calc.calculate_energy_levels(days_since_quit)
    circulation = health_calc.calculate_circulation(days_since_quit)
    gum_texture = health_calc.calculate_gum_texture(days_since_quit)
    immunity_lung = health_calc.calculate_immunity_and_lung_function(days_since_quit)
    heart_disease = health_calc.calculate_reduced_risk_of_heart_disease(days_since_quit)
    lung_cancer = health_calc.calculate_decreased_risk_of_lung_cancer(days_since_quit)
    heart_attack = health_calc.calculate_decreased_risk_of_heart_attack(days_since_quit)
    life_hours = health_calc.calculate_life_regained_in_hours(days_since_quit)

    lines = [
        f"Days since quit: {days_since_quit}",
        f"Nicotine expelled: {nicotine_expelled}%",
        f"Carbon monoxide normalization: {carbon_monoxide}%",
        f"Pulse rate improvement: {pulse_rate}%",
        f"Oxygen levels: {oxygen_levels}%",
        f"Taste & smell: {taste_smell}%",
        f"Breathing: {breathing}%",
        f"Energy levels: {energy}%",
        f"Circulation: {circulation}%",
        f"Gum texture: {gum_texture}%",
        f"Immunity & lung function: {immunity_lung}%",
        f"Reduced heart disease risk: {heart_disease}%",
        f"Reduced lung cancer risk: {lung_cancer}%",
        f"Reduced heart attack risk: {heart_attack}%",
        f"Estimated life regained: {life_hours} hours",
    ]

    if cigarettes_per_day is not None and cigarettes_per_day >= 0:
        minutes_per_cigarette = 20
        minutes_saved = days_since_quit * cigarettes_per_day * minutes_per_cigarette
        lines.append(f"Estimated minutes not smoked: {minutes_saved}")

    return "\n".join(lines)

# ---------- New Tools ----------

@tool
def detect_triggers_from_cravings(cravings: Optional[List[Dict[str, Any]]] = None, top_n: int = 3, window_days: Optional[int] = None) -> str:
    """
    Analyze recent cravings and return top triggers.
    Input: cravings list (items may include: date, time, activity, company, feeling),
           optional top_n (default 3), optional window_days to filter recent items.
    Output: ranked triggers for activity, company, time-of-day, feelings, with brief tips.
    """
    if not cravings:
        return (
            "No cravings provided to analyze. Please share a few recent entries as a JSON array, e.g.:\n"
            "[{\"date\": \"2025-01-22\", \"time\": \"14:30\", \"activity\": \"after lunch\", \"company\": \"coworkers\", \"feeling\": \"stressed\"}, ...]"
        )

    # Optional window filter by date field (YYYY-MM-DD)
    filtered = cravings
    if window_days is not None and window_days > 0:
        try:
            cutoff = date.today().toordinal() - window_days
            def _keep(item: Dict[str, Any]) -> bool:
                d = item.get("date") or item.get("day")
                if not d:
                    return True
                try:
                    dt = datetime.fromisoformat(str(d)).date()
                    return dt.toordinal() >= cutoff
                except Exception:
                    return True
            filtered = [c for c in cravings if _keep(c)]
        except Exception:
            filtered = cravings

    def bucket_time(t: Optional[str]) -> Optional[str]:
        if not t:
            return None
        try:
            hh = int(str(t)[:2])
        except Exception:
            return None
        if 5 <= hh < 12:
            return "morning"
        if 12 <= hh < 17:
            return "afternoon"
        if 17 <= hh < 22:
            return "evening"
        return "night"

    counts = {
        "activity": Counter(),
        "company": Counter(),
        "time": Counter(),
        "feeling": Counter(),
    }

    for c in filtered:
        if c.get("activity"):
            counts["activity"][str(c.get("activity")).strip().lower()] += 1
        if c.get("company"):
            counts["company"][str(c.get("company")).strip().lower()] += 1
        if c.get("feeling"):
            counts["feeling"][str(c.get("feeling")).strip().lower()] += 1
        # naive time extraction from optional time or datetime
        t = c.get("time") or c.get("datetime") or c.get("created_at")
        bucket = bucket_time(str(t)[11:13] if t else None)  # expects HH from ISO
        if bucket:
            counts["time"][bucket] += 1

    def top(counter: Counter) -> List[str]:
        return [f"{k} ({v})" for k, v in counter.most_common(top_n) if k]

    lines: List[str] = []
    lines.append("Top triggers (counts in parentheses):")
    lines.append(f"- Activity: {', '.join(top(counts['activity'])) or 'n/a'}")
    lines.append(f"- Company: {', '.join(top(counts['company'])) or 'n/a'}")
    lines.append(f"- Time of day: {', '.join(top(counts['time'])) or 'n/a'}")
    lines.append(f"- Feelings: {', '.join(top(counts['feeling'])) or 'n/a'}")

    tips: Dict[str, str] = {
        "morning": "Prepare a morning routine (water + 2-min breath) before triggers.",
        "afternoon": "Schedule a 5-min walk after lunch to reset.",
        "evening": "Replace late snacks with herbal tea; plan a wind-down routine.",
        "night": "Practice 4-7-8 breathing before bed; avoid caffeine late.",
    }
    suggested = []
    for tod, _ in counts["time"].most_common(1):
        if tod in tips:
            suggested.append(f"For {tod}: {tips[tod]}")
    if counts["activity"]:
        act, _ = counts["activity"].most_common(1)[0]
        suggested.append(f"When {act}: pre-plan a 5-minute alternative (stretch, water, quick text).")
    if suggested:
        lines.append("Suggestions:")
        lines.extend([f"- {s}" for s in suggested])

    return "\n".join(lines)

async def _fetch_cravings_async(user_id: int, window_days: int) -> List[Dict[str, Any]]:
    """Async helper to fetch cravings from database."""
    async with AsyncSessionLocal() as session:
        cutoff = date.today() - timedelta(days=max(window_days, 1))
        stmt = select(Craving).where(Craving.user_id == user_id)
        try:
            stmt = stmt.where(Craving.date >= cutoff)
        except Exception:
            pass
        rows = (await session.execute(stmt)).scalars().all()
        
        cravings = []
        for r in rows:
            cravings.append({
                "date": getattr(r, "date", None),
                "time": None,
                "activity": getattr(r, "activity", None),
                "company": getattr(r, "company", None),
                "feeling": getattr(r, "feeling", None),
            })
        return cravings

@tool
def detect_triggers_from_db(user_id: int, window_days: int = 14, top_n: int = 3) -> str:
    """
    Fetch user's recent cravings directly from the database and detect top triggers.
    Inputs: user_id (int), window_days (default 14), top_n (default 3)
    Output: ranked triggers with brief tips (same format as detect_triggers_from_cravings).
    """
    try:
        # Run async function in sync context
        cravings = asyncio.run(_fetch_cravings_async(user_id, window_days))
        # Reuse analysis function
        return detect_triggers_from_cravings.invoke({
            "cravings": cravings,
            "top_n": top_n,
            "window_days": window_days,
        })
    except Exception as e:
        logger.error(f"detect_triggers_from_db failed: {e}")
        return "Could not analyze cravings from the database right now. Please try again later."

async def _fetch_user_preferences_async(user_id: int) -> Optional[Preference]:
    """Async helper to fetch user preferences from database."""
    async with AsyncSessionLocal() as session:
        stmt = select(Preference).where(Preference.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

@tool
def get_user_savings_data(user_id: int) -> str:
    """
    Fetch user's quit data and calculate money/time saved since quitting.
    Input: user_id (int)
    Output: comprehensive savings breakdown including money saved, time regained, and health benefits.
    """
    try:
        # Run async function in sync context
        pref = asyncio.run(_fetch_user_preferences_async(user_id))
        
        if not pref:
            return "No quit data found. Please set up your preferences first."
        
        quit_date = pref.quit_date
        cig_per_day = pref.cig_per_day or 0
        cig_price = pref.cig_price or 0
        
        days = (date.today() - quit_date).days
        if days < 0:
            return f"Your quit date is in the future ({-days} days from now)."
        
        # Calculate savings
        money_saved = days * cig_per_day * max(cig_price, 0)
        minutes_per_cigarette = 20
        hours_saved = (days * cig_per_day * minutes_per_cigarette) / 60.0
        
        # Get health improvements
        nicotine_expelled = health_calc.calculate_nicotine_expelled(days)
        carbon_monoxide = health_calc.calculate_carbon_monoxide_level(days)
        life_hours = health_calc.calculate_life_regained_in_hours(days)
        
        lines = [
            f"💰 **Financial Savings**",
            f"Days since quit: {days}",
            f"Previous consumption: {cig_per_day} cigarettes/day",
            f"Price per cigarette: ${cig_price:.2f}",
            f"Money saved: ${money_saved:.2f}",
            "",
            f"⏰ **Time Regained**",
            f"Hours of life regained: {life_hours:.1f} hours",
            f"Time not spent smoking: {hours_saved:.1f} hours",
            "",
            f"🏥 **Health Progress**",
            f"Nicotine expelled: {nicotine_expelled}%",
            f"Carbon monoxide normalized: {carbon_monoxide}%",
        ]
        
        # Add motivational milestones
        if days >= 1:
            lines.append(f"🎉 You've been smoke-free for {days} days!")
        if days >= 7:
            lines.append("🌟 One week milestone reached!")
        if days >= 30:
            lines.append("🏆 One month milestone reached!")
        if days >= 90:
            lines.append("💪 Three months - your risk of heart disease is decreasing!")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"get_user_savings_data failed: {e}")
        return "Could not fetch your savings data right now. Please try again later."

@tool
def savings_estimator(quit_date: str, cig_per_day: int, cig_price: float) -> str:
    """
    Estimate money and time saved since quitting.
    Inputs: quit_date (YYYY-MM-DD), cig_per_day (int), cig_price (price per cigarette).
    Output: money_saved (currency), hours_saved (float).
    """
    try:
        quit_dt = datetime.strptime(quit_date, "%Y-%m-%d").date()
    except Exception:
        return "Invalid quit_date. Use format YYYY-MM-DD."

    days = (date.today() - quit_dt).days
    if days < 0:
        return f"Your quit date is in the future ({-days} days)."

    money_saved = days * cig_per_day * max(cig_price, 0)
    minutes_per_cigarette = 20
    hours_saved = (days * cig_per_day * minutes_per_cigarette) / 60.0
    return (
        f"Days since quit: {days}\n"
        f"Estimated money saved: {money_saved:.2f}\n"
        f"Estimated life/time regained: {hours_saved:.1f} hours"
    )

@tool
def goal_coach(context: Optional[str] = None, triggers: Optional[List[str]] = None) -> str:
    """
    Suggest 2–3 SMART goals tailored to user's context/triggers. Pure coaching utility.
    Inputs: context (free text), triggers (list of strings)
    Output: short SMART goals + first tiny action.
    """
    ctx = (context or "").strip()
    trig = ", ".join(triggers or [])
    goals: List[str] = []

    base = "This week"
    goals.append(f"{base}, replace one smoking trigger with a 2-minute breathing break after each meal (Mon–Fri). Measure: 5/5 days.")
    goals.append(f"{base}, walk 10 minutes after lunch on 4 days. Measure: 4/4.")
    if trig:
        goals.append(f"{base}, prepare an IF-THEN plan for top trigger ({trig}). e.g., IF urge after coffee THEN drink water + 4-7-8 for 2 min.")
    else:
        goals.append(f"{base}, prepare an IF-THEN plan for your top trigger. Write it down and practice once daily.")

    next_step = "Next step: pick one goal, schedule it on your calendar, and set a reminder."
    header = f"Context: {ctx}" if ctx else ""
    lines = [l for l in [header] if l]
    lines.append("SMART goals:")
    for i, g in enumerate(goals[:3], 1):
        lines.append(f"{i}. {g}")
    lines.append(next_step)
    return "\n".join(lines)

@tool
def evidence_lookup(query: str) -> str:
    """
    Look up recent, reputable sources for a cessation-related question.
    Returns 3 concise bullets with title + source + link.
    """
    if not search:
        return "Search is not configured. Please set TAVILY_API_KEY."
    try:
        res = search.invoke({"query": query})
        items = []
        if isinstance(res, dict) and "results" in res:
            items = res["results"]
        elif isinstance(res, list):
            items = res
        else:
            items = [res]
        bullets: List[str] = []
        for it in items[:3]:
            title = it.get("title") if isinstance(it, dict) else str(it)
            url = it.get("url") if isinstance(it, dict) else ""
            source = it.get("source") or it.get("domain") or ""
            bullet = f"• {title} — {source} {url}"
            bullets.append(bullet)
        return "\n".join(bullets) if bullets else "No results found."
    except Exception as e:
        logger.error(f"Evidence lookup failed: {e}")
        return "Search failed. Please try again later."

# Compile tools list with error handling
TOOLS: List[BaseTool] = []

if search:
    TOOLS.append(search)

TOOLS.extend([
    calculate_health_improvements,
    detect_triggers_from_cravings,
    detect_triggers_from_db,
    get_user_savings_data,
    savings_estimator,
    goal_coach,
    evidence_lookup,
])

logger.info(f"Initialized {len(TOOLS)} tools for the agent")
