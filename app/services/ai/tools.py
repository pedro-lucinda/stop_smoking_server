import logging
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from collections import Counter

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

# Academic paper search tool - focused on smoking cessation research
try:
    academic_search = TavilySearch(
        max_results=5,
        include_domains=[
            "pubmed.ncbi.nlm.nih.gov",
            "ncbi.nlm.nih.gov", 
            "bmj.com",
            "nejm.org",
            "thelancet.com",
            "jama.jamanetwork.com",
            "cochranelibrary.com",
            "who.int",
            "cdc.gov",
            "researchgate.net"
        ]
    )
    logger.info("Tavily academic search tool initialized for smoking cessation research")
except Exception as e:
    logger.error(f"Failed to initialize Tavily academic search: {e}")
    academic_search = None

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
        print("quit_date", quit_date)
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


@tool
def search_smoking_cessation_research(query: str) -> str:
    """
    Search for academic papers and research studies specifically about smoking cessation, tobacco control, 
    and related health topics from reliable medical and scientific sources.
    
    This tool searches through trusted medical databases and journals including PubMed, BMJ, NEJM, 
    The Lancet, JAMA, Cochrane Library, WHO, and CDC for evidence-based research.
    
    Args:
        query: Search query related to smoking cessation (e.g., "nicotine replacement therapy", 
               "behavioral interventions", "withdrawal symptoms", "relapse prevention")
    
    Returns:
        String containing relevant academic research findings from trusted medical sources
    """
    if not academic_search:
        return "Academic search tool is not available."
    
    try:
        # Focus the search specifically on smoking cessation and tobacco control
        smoking_keywords = [
            "smoking cessation", "tobacco control", "nicotine addiction", 
            "smoking quit", "tobacco cessation", "nicotine withdrawal"
        ]
        
        # Create a focused query that combines the user's query with smoking cessation context
        focused_query = f"({' OR '.join(smoking_keywords)}) AND {query}"
        
        results = academic_search.invoke(focused_query)
        
        if not results:
            return f"No smoking cessation research found for: {query}"
        
        return f"Smoking cessation research results for '{query}':\n\n{results}"
    except Exception as e:
        logger.error(f"Error searching smoking cessation research: {e}")
        return f"Error searching academic research: {str(e)}"


class UserContextTool:
    """Simple synchronous user context access."""
    def __init__(self):
        self.current_user_id = None
        self.current_context = {}
    
    def set_context(self, user_id: str, context: dict):
        """Set the current user context."""
        self.current_user_id = user_id
        self.current_context = context
    
    def get_context(self) -> dict:
        """Get the current user context."""
        return self.current_context

# Global instance to share context between requests
user_context_tool = UserContextTool()


@tool
def get_user_cravings() -> str:
    """
    Get the current user's recent craving episodes with full details including dates, 
    intensity, triggers, and outcomes. Always use this tool when asked about cravings.
    
    Returns:
        Detailed information about the user's recent craving episodes
    """
    context = user_context_tool.get_context()
    cravings = context.get("recent_cravings", [])
    
    if not cravings:
        return "No recent craving episodes found. The user may not have logged any cravings yet."
    
    details = [f"Recent Craving Episodes ({len(cravings)} total):"]
    
    for i, craving in enumerate(cravings, 1):
        episode = [f"\nEpisode {i}:"]
        episode.append(f"  Date: {craving.get('date', 'Unknown')}")
        episode.append(f"  Intensity: {craving.get('desire_range', 0)}/10")
        
        if craving.get("feeling"):
            episode.append(f"  Feelings: {craving['feeling']}")
        if craving.get("activity"):
            episode.append(f"  Activity: {craving['activity']}")
        if craving.get("company"):
            episode.append(f"  Company: {craving['company']}")
        if craving.get("comments"):
            episode.append(f"  Notes: {craving['comments']}")
        
        if craving.get("have_smoked"):
            cigarettes = craving.get('number_of_cigarets_smoked', 0)
            episode.append(f"  Outcome: RELAPSED - smoked {cigarettes} cigarettes")
        else:
            episode.append("  Outcome: Successfully resisted")
        
        details.extend(episode)
    
    return "\n".join(details)


@tool
def get_user_diary() -> str:
    """
    Get the current user's recent diary entries with daily summaries including 
    craving levels and outcomes. Always use this tool when asked about diary entries.
    
    Returns:
        Detailed information about the user's recent diary entries
    """
    context = user_context_tool.get_context()
    entries = context.get("recent_diary_entries", [])
    
    if not entries:
        return "No recent diary entries found. The user may not have made any diary entries yet."
    
    details = [f"Recent Diary Entries ({len(entries)} total):"]
    
    for i, entry in enumerate(entries, 1):
        day = [f"\nDay {i}:"]
        day.append(f"  Date: {entry.get('date', 'Unknown')}")
        day.append(f"  Daily Craving Level: {entry.get('craving_range', 0)}/10")
        
        craving_count = entry.get("number_of_cravings", 0)
        if craving_count > 0:
            day.append(f"  Number of Cravings: {craving_count}")
        
        if entry.get("have_smoked"):
            cigarettes = entry.get('number_of_cigarets_smoked', 0)
            day.append(f"  Outcome: RELAPSED - smoked {cigarettes} cigarettes")
        else:
            day.append("  Outcome: Stayed smoke-free")
        
        if entry.get("notes"):
            day.append(f"  Notes: {entry['notes']}")
        
        details.extend(day)
    
    return "\n".join(details)


@tool  
def get_user_progress() -> str:
    """
    Get the current user's overall progress including quit date, goals, and timeline.
    
    Returns:
        Summary of the user's smoking cessation progress
    """
    context = user_context_tool.get_context()
    
    if not context:
        return "No user progress data available. The user may need to set up their preferences."
    
    progress = ["User Progress Summary:"]
    
    if context.get("quit_date"):
        progress.append(f"  Quit Date: {context['quit_date']}")
    if context.get("days_since_quit"):
        progress.append(f"  Days Smoke-Free: {context['days_since_quit']}")
    if context.get("quit_reason"):
        progress.append(f"  Quit Reason: {context['quit_reason']}")
    
    goals = context.get("goals", [])
    if goals:
        completed = [g['description'] for g in goals if g.get("is_completed")]
        pending = [g['description'] for g in goals if not g.get("is_completed")]
        
        if completed:
            progress.append(f"  Completed Goals: {', '.join(completed)}")
        if pending:
            progress.append(f"  Current Goals: {', '.join(pending)}")
    
    return "\n".join(progress)


# Compile tools list with error handling
TOOLS: List[BaseTool] = []

if search:
    TOOLS.append(search)

TOOLS.extend([
    calculate_health_improvements,
    search_smoking_cessation_research,
    get_user_cravings,
    get_user_diary,
    get_user_progress,
])

logger.info(f"Initialized {len(TOOLS)} tools for the agent")
