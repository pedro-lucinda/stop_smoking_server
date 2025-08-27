import logging
from typing import List, Optional
from datetime import date, datetime

from langchain_tavily import TavilySearch
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core import health as health_calc

logger = logging.getLogger(__name__)

# Search tool for general information
try:
    search = TavilySearch(max_results=3)  # Increased results for better context
    logger.info("Tavily search tool initialized")
except Exception as e:
    logger.error(f"Failed to initialize Tavily search: {e}")
    search = None

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
        # Reuse the same assumption as API (20 min per cigarette)
        minutes_per_cigarette = 20
        minutes_saved = days_since_quit * cigarettes_per_day * minutes_per_cigarette
        lines.append(f"Estimated minutes not smoked: {minutes_saved}")

    return "\n".join(lines)

@tool
def get_craving_management_tips() -> str:
    """
    Provide evidence-based tips for managing nicotine cravings.
    Use this when users ask about handling cravings or withdrawal symptoms.
    """
    return """Here are proven strategies to manage cravings:

**Immediate Relief (5-10 minutes):**
• Deep breathing exercises (4-7-8 technique)
• Drink cold water or herbal tea
• Take a short walk or stretch
• Use stress balls or fidget toys

**Medium-term Strategies:**
• Identify and avoid triggers
• Practice mindfulness meditation
• Use nicotine replacement therapy (consult doctor)
• Stay hydrated and eat regular meals

**Long-term Support:**
• Join support groups or counseling
• Exercise regularly
• Get adequate sleep
• Reward yourself for milestones

**Emergency Plan:**
1. Stop and breathe deeply
2. Drink water
3. Call a support person
4. Remember your reasons for quitting
5. Distract yourself with an activity

Remember: Cravings typically last 3-5 minutes and will get easier over time."""

@tool
def get_relapse_prevention_strategies() -> str:
    """
    Provide strategies to prevent relapse and maintain long-term abstinence.
    Use this when users ask about staying smoke-free or avoiding relapse.
    """
    return """**Relapse Prevention Strategies:**

**1. Identify High-Risk Situations:**
• Social gatherings with smokers
• Stressful work situations
• After meals or with coffee
• Driving or commuting
• Alcohol consumption

**2. Develop Coping Skills:**
• Practice saying "No, thank you" firmly
• Have an exit strategy for triggering situations
• Use stress management techniques
• Keep healthy snacks available

**3. Build a Support System:**
• Tell friends and family about your quit journey
• Join online or in-person support groups
• Consider professional counseling
• Use quit-smoking apps or hotlines

**4. Create a Healthy Routine:**
• Exercise regularly
• Practice good sleep hygiene
• Eat nutritious meals
• Find new hobbies or activities

**5. Monitor Your Progress:**
• Track smoke-free days
• Celebrate milestones
• Reflect on benefits you've experienced
• Keep a journal of your journey

**6. Emergency Response Plan:**
If you feel like smoking:
1. Wait 10 minutes before acting
2. Call a support person
3. Use deep breathing
4. Remember your reasons for quitting
5. Distract yourself with an activity

**Remember:** Relapse is not failure - it's part of the learning process. Most successful quitters attempt multiple times before succeeding permanently."""

# Compile tools list with error handling
TOOLS: List[BaseTool] = []

if search:
    TOOLS.append(search)

TOOLS.extend([
    calculate_health_improvements,
    get_craving_management_tips,
    get_relapse_prevention_strategies,
])

logger.info(f"Initialized {len(TOOLS)} tools for the agent")
