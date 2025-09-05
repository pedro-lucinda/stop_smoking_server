import logging
from typing import Generator
from uuid import uuid4
from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from fastapi import Security
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth0 import get_current_user
from app.api.v1.dependencies.auth0 import oauth2_scheme
from app.api.v1.dependencies.db import get_async_db
from app.models.preference import Preference
from app.models.user import User
from app.schemas.chat import ChatIn, ThreadOut
from app.services.ai.agent import agent
from app.services.ai.tools import user_context_tool
from app.utils.ai import _event, _extract_text, _iter_tool_calls, _to_json, sse

logger = logging.getLogger(__name__)

# Pre-processing filter for non-smoking questions
def _is_non_smoking_question(question: str) -> bool:
    """Check if the question is clearly unrelated to smoking cessation."""
    question_lower = question.lower().strip()
    
    # Smoking-related keywords that should be allowed
    smoking_keywords = [
        "smoke", "smoking", "cigarette", "cigarettes", "tobacco", "nicotine", 
        "quit", "quitting", "cessation", "craving", "cravings", "withdrawal",
        "relapse", "relapsed", "diary", "progress", "goal", "goals",
        "health", "lung", "cancer", "heart", "breathing", "addiction",
        "vape", "vaping", "e-cigarette", "hookah", "pipe", "cigar",
        "secondhand", "passive", "smoke-free", "smokefree", "nonsmoker"
    ]
    
    # Check if question contains any smoking-related keywords
    has_smoking_keyword = any(keyword in question_lower for keyword in smoking_keywords)
    
    # If it has smoking keywords, it's likely related to smoking cessation
    if has_smoking_keyword:
        return False
    
    # Non-smoking question patterns that should be refused
    non_smoking_patterns = [
        # Geography and general knowledge
        "capital of", "what country", "where is", "population of",
        "who invented", "when was", "how to cook", "what is the weather",
        "what is", "who is", "when did", "how many", "how much",
        
        # Technology and programming
        "how to code", "programming", "python", "javascript", "html",
        "computer", "software", "app", "website", "database",
        
        # Entertainment and media
        "movie", "film", "actor", "actress", "song", "music", "book",
        "game", "sport", "team", "player",
        
        # Science and education (non-health related)
        "physics", "chemistry", "biology", "math", "history", "literature",
        "philosophy", "economics", "politics", "law", "art", "design",
        
        # Personal advice (non-smoking related)
        "relationship", "dating", "marriage", "divorce", "parenting",
        "career", "job", "interview", "resume", "salary",
        
        # Health topics unrelated to smoking
        "diet", "exercise", "weight loss", "fitness", "yoga", "meditation",
        "sleep", "stress", "anxiety", "depression", "therapy"
    ]
    
    # Check if question matches non-smoking patterns
    matches_non_smoking = any(pattern in question_lower for pattern in non_smoking_patterns)
    
    return matches_non_smoking

# Post-processing filter for non-smoking responses
def _is_non_smoking_response(response_text: str, original_question: str) -> bool:
    """Check if the AI response answers a non-smoking question that should have been refused."""
    question_lower = original_question.lower().strip()
    response_lower = response_text.lower().strip()
    
    # Geography questions and responses
    geography_patterns = [
        ("capital of", ["brasília", "capital", "city"]),
        ("what country", ["country", "nation"]),
        ("where is", ["located", "in", "country"]),
        ("population of", ["population", "people", "million"]),
    ]
    
    # General knowledge patterns
    knowledge_patterns = [
        ("who invented", ["invented", "created", "developed"]),
        ("when was", ["in", "year", "century"]),
        ("how to cook", ["cook", "recipe", "ingredients"]),
        ("what is the weather", ["weather", "temperature", "forecast"]),
    ]
    
    all_patterns = geography_patterns + knowledge_patterns
    
    # Check if question is non-smoking and response contains typical answer patterns
    for question_pattern, response_indicators in all_patterns:
        if question_pattern in question_lower:
            # Check if it's about smoking (e.g., "capital of smoking cessation")
            smoking_keywords = ["smok", "tobacco", "nicotine", "cigarette", "quit", "cessation", "craving"]
            if not any(keyword in question_lower for keyword in smoking_keywords):
                # It's a non-smoking question, check if response answers it
                if any(indicator in response_lower for indicator in response_indicators):
                    return True
    
    return False


def _get_smoking_refusal_response() -> str:
    """Get the standard refusal response for non-smoking questions."""
    return "I'm sorry, but I can only help with smoking cessation and tobacco-related questions. I cannot answer questions about other topics. Is there anything about quitting smoking or managing tobacco cravings I can help you with instead?"

router = APIRouter()

EVENT_TOKEN = "token"
EVENT_TOOL_CALL = "tool_call"
EVENT_TOOL_RESULT = "tool_result"
EVENT_ERROR = "error"

@router.post("/thread", response_model=ThreadOut, dependencies=[Depends(get_current_user)])
def create_thread() -> ThreadOut:
    """Create a new chat thread for the user."""
    thread_id = str(uuid4())
    logger.info(f"Created new chat thread: {thread_id}")
    return ThreadOut(thread_id=thread_id)


@router.post("/threads/{thread_id}/stream", dependencies=[Depends(get_current_user)])
async def chat_stream(
    thread_id: str = Path(..., min_length=1),
    payload: ChatIn = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    raw_token: str = Security(oauth2_scheme),
):
    """
    Streams assistant output and tool activity as Server-Sent Events.
    
    Events:
        - {"event":"tool_call","tool":str,"args":dict}
        - {"event":"token","text":str}
        - {"event":"tool_result","tool":str,"content":str}
        - {"event":"error","message":str}
    """
    # Check if agent is available
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is currently unavailable"
        )
    
    # Get user's full preference information for context
    user_context = {}
    try:
        from sqlalchemy.orm import selectinload
        pref_result = await db.execute(
            select(Preference)
            .options(selectinload(Preference.goals))
            .where(Preference.user_id == current_user.id)
        )
        preference = pref_result.scalar_one_or_none()
        
        if preference:
            days_since_quit = (date.today() - preference.quit_date).days
            
            # Convert goals to dict format
            goals_data = []
            if preference.goals:
                goals_data = [
                    {
                        "id": goal.id,
                        "description": goal.description,
                        "is_completed": goal.is_completed
                    }
                    for goal in preference.goals
                ]
            
            user_context = {
                "user_id": str(current_user.id),
                "quit_date": preference.quit_date.isoformat(),
                "days_since_quit": days_since_quit,
                "quit_reason": preference.reason,
                "cigarettes_per_day": preference.cig_per_day or 0,
                "years_smoking": preference.years_smoking or 0,
                "cigarette_price": preference.cig_price or 0,
                "language": preference.language or "en-us",
                "goals": goals_data,
            }
            logger.info(f"Loaded full user context for {current_user.id}: {days_since_quit} days smoke-free, {len(goals_data)} goals")
        else:
            logger.info(f"No preferences found for user {current_user.id}")
    except Exception as e:
        logger.warning(f"Could not load user context: {e}")
    
    # Load recent cravings and diary entries for additional context
    try:
        from app.models.craving import Craving
        from app.models.diary import Diary
        from datetime import timedelta
        
        # Get recent cravings (last 30 days)
        recent_date = date.today() - timedelta(days=30)
        cravings_result = await db.execute(
            select(Craving)
            .where(Craving.user_id == current_user.id)
            .where(Craving.date >= recent_date)
            .order_by(Craving.date.desc())
            .limit(20)  # Limit to recent 20 entries
        )
        cravings = cravings_result.scalars().all()
        
        # Get recent diary entries (last 30 days)
        diary_result = await db.execute(
            select(Diary)
            .where(Diary.user_id == current_user.id)
            .where(Diary.date >= recent_date)
            .order_by(Diary.date.desc())
            .limit(20)  # Limit to recent 20 entries
        )
        diary_entries = diary_result.scalars().all()
        
        # Convert to dict format
        cravings_data = [
            {
                "id": craving.id,
                "date": craving.date.isoformat(),
                "comments": craving.comments,
                "have_smoked": craving.have_smoked,
                "desire_range": craving.desire_range or 0,
                "number_of_cigarets_smoked": craving.number_of_cigarets_smoked or 0,
                "feeling": craving.feeling,
                "activity": craving.activity,
                "company": craving.company
            }
            for craving in cravings
        ]
        
        diary_data = [
            {
                "id": entry.id,
                "date": entry.date.isoformat(),
                "notes": entry.notes,
                "have_smoked": entry.have_smoked,
                "craving_range": entry.craving_range or 0,
                "number_of_cravings": entry.number_of_cravings or 0,
                "number_of_cigarets_smoked": entry.number_of_cigarets_smoked or 0
            }
            for entry in diary_entries
        ]
        
        # Add to user context if it exists
        if user_context:
            user_context["recent_cravings"] = cravings_data
            user_context["recent_diary_entries"] = diary_data
            
        logger.info(f"Loaded activity data for {current_user.id}: {len(cravings_data)} cravings, {len(diary_data)} diary entries")
        
    except Exception as e:
        logger.warning(f"Could not load activity data: {e}")
    
    # Debug log the user_context
    logger.info(f"Final user_context: {user_context}")
    
    # SET CONTEXT IN GLOBAL TOOL - This ensures tools always have access to user data
    if user_context:
        user_context_tool.set_context(str(current_user.id), user_context)
        logger.info(f"Set global context for user {current_user.id} with {len(user_context)} fields")

    cfg = {"configurable": {"thread_id": thread_id, "checkpoint_ns": "chat"}}

    def gen() -> Generator[str, None, None]:
        try:
            # PRE-PROCESSING: Check for obvious non-smoking questions
            message_lower = payload.message.lower().strip()
            
            # Check if this is a non-smoking question and refuse immediately
            if _is_non_smoking_question(payload.message):
                logger.info(f"Refusing non-smoking question: {payload.message[:100]}...")
                refusal_response = _get_smoking_refusal_response()
                
                # Stream the refusal response as if it came from the AI
                for word in refusal_response.split():
                    yield _event(EVENT_TOKEN, text=word + " ")
                return
            
            # Build structured initial state for the custom agent
            initial_state = {
                "messages": [{"role": "user", "content": payload.message}],
            }
            # Attach structured user context if available 
            # IMPORTANT: Always pass fresh user context for each message to ensure context persistence
            if user_context:
                user_data = {
                    "user_id": str(current_user.id),
                    "quit_date": user_context.get("quit_date"),
                    "days_since_quit": user_context.get("days_since_quit"),
                    "quit_reason": user_context.get("quit_reason"),
                    "cigarettes_per_day": user_context.get("cigarettes_per_day"),
                    "years_smoking": user_context.get("years_smoking"),
                    "cigarette_price": user_context.get("cigarette_price"),
                    "language": user_context.get("language"),
                    "goals": user_context.get("goals"),
                    "recent_cravings": user_context.get("recent_cravings"),
                    "recent_diary_entries": user_context.get("recent_diary_entries"),
                }
                initial_state.update(user_data)
                
                # FORCE CONTEXT PERSISTENCE: Ensure conversation_context gets refreshed with current data
                # This prevents context loss when topics change and come back
                if "conversation_context" not in initial_state:
                    initial_state["conversation_context"] = {}
                initial_state["conversation_context"].update(user_data)
                
                # CRITICAL: Also store context in a persistent way that survives message exchanges
                # Store in both places to ensure it's never lost
                for key, value in user_data.items():
                    initial_state[key] = value
                
                logger.info(f"FORCE UPDATED both initial_state and conversation_context with {len(user_data)} fields")
                logger.info(f"Context includes cravings: {bool(user_context.get('recent_cravings'))}")
                if user_context.get('recent_cravings'):
                    logger.info(f"Cravings count: {len(user_context['recent_cravings'])}")
            else:
                logger.info("No user_context available - user likely needs to set up preferences")
            # Provide bearer token for API-backed tools (never echo it)
            initial_state["auth_token"] = raw_token

            stream = agent.stream(
                initial_state,
                config=cfg,
                stream_mode="messages",
            )

            for msg, meta in stream:
                node = meta.get("langgraph_node")

                if node == "agent":
                    # tool calls requested by the assistant
                    for name, args in _iter_tool_calls(msg):
                        if name:
                            yield _event(EVENT_TOOL_CALL, tool=name, args=args)

                    # assistant token chunks
                    text = _extract_text(msg)
                    if text:
                        yield _event(EVENT_TOKEN, text=text)
                    continue

                # tool node produced a result
                content = getattr(msg, "content", None)
                if content is not None:
                    normalized = content if isinstance(content, str) else _to_json(content)
                    yield _event(EVENT_TOOL_RESULT, tool=node, content=normalized)
                    
        except Exception as e:
            logger.error(f"Error in chat stream for thread {thread_id}: {e}")
            yield _event(EVENT_ERROR, message="An error occurred while processing your request. Please try again.")

    return sse(gen())


@router.get("/health")
async def chat_health_check():
    """Check if the chat service is available."""
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is unavailable"
        )
    return {"status": "healthy", "agent_available": True}