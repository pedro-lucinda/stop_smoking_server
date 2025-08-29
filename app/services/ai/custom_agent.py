"""
Custom LangGraph agent implementation for smoking cessation coaching.
This provides more control over the agent's behavior and better integration with user data.
"""

import logging
from typing import Any, Dict, List, Optional, TypedDict
from datetime import date
from typing_extensions import Annotated

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages

from app.core.config import settings
from app.prompts.chat import SYSTEM_POLICY

logger = logging.getLogger(__name__)

# State definition
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: Optional[str]
    quit_date: Optional[str]
    days_since_quit: Optional[int]
    quit_reason: Optional[str]
    cigarettes_per_day: Optional[int]
    years_smoking: Optional[int]
    cigarette_price: Optional[int]
    language: Optional[str]
    goals: Optional[List[Dict[str, Any]]]
    recent_cravings: Optional[List[Dict[str, Any]]]
    recent_diary_entries: Optional[List[Dict[str, Any]]]
    current_step: str
    tool_results: List[Dict[str, Any]]
    conversation_context: Dict[str, Any]

def create_custom_agent(
    model: BaseChatModel,
    tools: List[BaseTool],
    checkpointer: Optional[object],
) -> StateGraph:
    """
    Create a custom LangGraph agent with specialized nodes for smoking cessation.
    """
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("context_enricher", create_context_node())
    workflow.add_node("agent", create_agent_node(model, tools))
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("response_formatter", create_response_formatter())
    
    # Set entry point
    workflow.set_entry_point("context_enricher")
    
    # Add edges
    workflow.add_edge("context_enricher", "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "format_response": "response_formatter",
            "end": END,
        },
    )
    workflow.add_edge("tools", "agent")
    workflow.add_edge("response_formatter", END)
    
    app = workflow.compile(checkpointer=checkpointer)
    
    return app

def create_context_node():
    """Create a node that enriches the conversation with user context."""
    
    def context_node(state: AgentState) -> AgentState:
        # Initialize conversation context if not present
        if "conversation_context" not in state:
            state["conversation_context"] = {}
        
        # Add user context to conversation
        context = state["conversation_context"]
        
        # Debug log the incoming state
        logger.info(f"Context node received state keys: {list(state.keys())}")
        if state.get("user_id"):
            logger.info(f"Processing context for user {state['user_id']}")
        
        # CRITICAL: Always update context with fresh state data to maintain context across conversation
        # This ensures that even after multiple message exchanges, we retain the user's detailed context
        
        logger.info(f"Context enricher: state has keys: {list(state.keys())}")
        
        # FORCE UPDATE: Always refresh conversation context with current state data
        user_fields = ["user_id", "quit_date", "days_since_quit", "quit_reason", "cigarettes_per_day", 
                      "years_smoking", "cigarette_price", "language"]
        
        for field in user_fields:
            if state.get(field) is not None:
                context[field] = state[field]
                logger.info(f"Updated context[{field}] = {state[field]}")
        
        # FORCE UPDATE: Complex data structures - always preserve if available
        if state.get("goals"):
            context["goals"] = state["goals"]
            logger.info(f"Updated context[goals] with {len(state['goals'])} goals")
            
        if state.get("recent_cravings"):
            context["recent_cravings"] = state["recent_cravings"]
            logger.info(f"CRITICAL: Updated context[recent_cravings] with {len(state['recent_cravings'])} cravings")
            
        if state.get("recent_diary_entries"):
            context["recent_diary_entries"] = state["recent_diary_entries"]
            logger.info(f"Updated context[recent_diary_entries] with {len(state['recent_diary_entries'])} entries")
        
        # Log final context state
        logger.info(f"Final conversation_context keys: {list(context.keys())}")
        if context.get("recent_cravings"):
            logger.info(f"Final check: context has {len(context['recent_cravings'])} cravings")
        
        # Add motivational context based on quit duration
        days = state.get("days_since_quit", 0)
        if days > 0:
            if days == 1:
                context["milestone"] = "First day smoke-free! Your body is already healing."
            elif days == 7:
                context["milestone"] = "One week! The worst of withdrawal is behind you."
            elif days == 30:
                context["milestone"] = "One month! Your lung function is improving."
            elif days == 90:
                context["milestone"] = "Three months! Your risk of heart disease is decreasing."
            elif days == 365:
                context["milestone"] = "One year! Your risk of heart disease is half that of a smoker."
        
        return {
            **state,
            "current_step": "context_enriched",
            "conversation_context": context
        }
    
    return context_node

# Helper functions for context building
def _build_tool_descriptions(tools: List[BaseTool]) -> List[str]:
    """Build tool descriptions for the model."""
    return [f"{tool.name}: {tool.description}" for tool in tools]


def _build_quit_info_context(context: Dict[str, Any]) -> List[str]:
    """Build quit information context parts."""
    quit_info_mapping = {
        "quit_date": "Quit Date",
        "days_since_quit": "Days Since Quit", 
        "quit_reason": "Quit Reason",
        "milestone": "Milestone"
    }
    
    return [f"{label}: {context[key]}" for key, label in quit_info_mapping.items() if context.get(key)]


def _build_smoking_history_context(context: Dict[str, Any]) -> List[str]:
    """Build smoking history context parts."""
    smoking_history_mapping = {
        "cigarettes_per_day": lambda x: f"Previous Consumption: {x} cigarettes/day",
        "years_smoking": lambda x: f"Years of Smoking: {x} years",
        "cigarette_price": lambda x: f"Cigarette Cost: {x} per cigarette"
    }
    
    return [formatter(context[key]) for key, formatter in smoking_history_mapping.items() if context.get(key)]


def _build_preferences_context(context: Dict[str, Any]) -> List[str]:
    """Build user preferences context parts."""
    preferences_mapping = {
        "language": "Preferred Language"
    }
    
    return [f"{label}: {context[key]}" for key, label in preferences_mapping.items() if context.get(key)]


def _build_goals_context(context: Dict[str, Any]) -> List[str]:
    """Build goals context parts."""
    goals = context.get("goals", [])
    if not goals:
        return []
    
    completed_goals = [g['description'] for g in goals if g.get("is_completed")]
    pending_goals = [g['description'] for g in goals if not g.get("is_completed")]
    
    goal_parts = []
    goal_parts.extend([f"Completed Goals: {', '.join(completed_goals)}"] if completed_goals else [])
    goal_parts.extend([f"Current Goals: {', '.join(pending_goals)}"] if pending_goals else [])
    
    return goal_parts


def _format_craving_episode(craving: Dict[str, Any], episode_num: int) -> str:
    """Format a single craving episode into a readable string."""
    # Base episode info
    details = f"Episode {episode_num}: {craving.get('date', 'Unknown')}, Intensity {craving.get('desire_range', 0)}/10"
    
    # Optional context fields
    context_fields = [
        ("feeling", lambda x: f", felt {x}"),
        ("activity", lambda x: f", during {x}"),
        ("company", lambda x: f", with {x}"),
        ("comments", lambda x: f", notes: '{x[:40]}{'...' if len(x) > 40 else ''}'"),
    ]
    
    # Add context fields that exist
    for field, formatter in context_fields:
        value = craving.get(field)
        if value:
            details += formatter(value)
    
    # Add relapse indicator
    return details + (" [RELAPSED]" if craving.get("have_smoked") else "")


def _build_cravings_context(context: Dict[str, Any]) -> List[str]:
    """Build recent cravings context parts."""
    cravings = context.get("recent_cravings", [])
    if not cravings:
        return []
    
    logger.info(f"Agent node processing {len(cravings)} cravings: {cravings[:1]}")
    
    # Calculate summary statistics
    recent_count = len(cravings)
    relapse_count = sum(1 for c in cravings if c.get("have_smoked"))
    avg_desire = sum(c.get("desire_range", 0) for c in cravings) / len(cravings)
    
    # Build context parts
    context_parts = [f"Recent Cravings: {recent_count} episodes (avg intensity: {avg_desire:.1f}/10)"]
    context_parts.extend([f"Recent Relapses: {relapse_count} smoking episodes"] if relapse_count > 0 else [])
    
    # Add detailed breakdown of recent cravings
    craving_details = [_format_craving_episode(craving, i) for i, craving in enumerate(cravings[:3], 1)]
    context_parts.extend([f"Craving Details: {' | '.join(craving_details)}"] if craving_details else [])
    
    return context_parts


def _format_diary_entry(entry: Dict[str, Any], day_num: int) -> str:
    """Format a single diary entry into a readable string."""
    # Base entry info
    details = f"Day {day_num}: {entry.get('date', 'Unknown')}, Daily craving level {entry.get('craving_range', 0)}/10"
    
    # Add craving episodes count
    craving_count = entry.get("number_of_cravings", 0)
    details += f", {craving_count} craving episodes" if craving_count > 0 else ""
    
    # Add smoking status
    if entry.get("have_smoked"):
        cigarettes = entry.get('number_of_cigarets_smoked', 0)
        details += f", RELAPSED: smoked {cigarettes} cigarettes"
    else:
        details += ", stayed smoke-free"
    
    # Add notes
    notes = entry.get("notes", "")
    if notes:
        truncated_notes = notes[:40] + "..." if len(notes) > 40 else notes
        details += f", notes: '{truncated_notes}'"
    
    return details


def _build_diary_context(context: Dict[str, Any]) -> List[str]:
    """Build recent diary entries context parts."""
    entries = context.get("recent_diary_entries", [])
    if not entries:
        return []
    
    # Calculate summary statistics  
    recent_count = len(entries)
    avg_craving = sum(e.get("craving_range", 0) for e in entries) / len(entries)
    total_cravings = sum(e.get("number_of_cravings", 0) for e in entries)
    
    # Build context parts
    context_parts = [f"Recent Diary Entries: {recent_count} days tracked (avg craving level: {avg_craving:.1f}/10)"]
    context_parts.extend([f"Total Cravings Tracked: {total_cravings} cravings"] if total_cravings > 0 else [])
    
    # Add detailed breakdown of recent diary entries
    diary_details = [_format_diary_entry(entry, i) for i, entry in enumerate(entries[:3], 1)]
    context_parts.extend([f"Daily Diary Summary: {' | '.join(diary_details)}"] if diary_details else [])
    
    return context_parts


def _build_user_context_section(context: Dict[str, Any]) -> str:
    """Build the complete user context section for the system message."""
    # Debug log to track context availability
    logger.info(f"Building user context section. Context keys available: {list(context.keys()) if context else 'None'}")
    if context and context.get("recent_cravings"):
        logger.info(f"Context has {len(context['recent_cravings'])} recent cravings")
    
    if not context:
        return "\nUser Context: No preferences configured yet. The user should set up their quit date, smoking history, and goals for personalized advice."
    
    all_context_parts = []
    
    # Build different context sections
    all_context_parts.extend(_build_quit_info_context(context))
    all_context_parts.extend(_build_smoking_history_context(context))
    all_context_parts.extend(_build_preferences_context(context))
    all_context_parts.extend(_build_goals_context(context))
    all_context_parts.extend(_build_cravings_context(context))
    all_context_parts.extend(_build_diary_context(context))
    
    if all_context_parts:
        context_text = f"\nUser Context:\n" + "\n".join(f"- {part}" for part in all_context_parts)
        # Add reminder about context persistence
        context_text += "\n\nIMPORTANT: This context remains available throughout the entire conversation. Always refer to these details when discussing cravings, diary entries, goals, or progress, even if the topic changed and came back."
        logger.info(f"Built complete user context with {len(all_context_parts)} sections")
        return context_text
    else:
        logger.warning("No context parts available despite having context data")
        return "\nUser Context: No preferences configured yet. The user should set up their quit date, smoking history, and goals for personalized advice."


def _build_system_message(context: Dict[str, Any], tool_descriptions: List[str]) -> str:
    """Build the complete system message with context and tools."""
    system_parts = [SYSTEM_POLICY]
    
    # Add user context section
    system_parts.append(_build_user_context_section(context))
    
    # Add tool information
    system_parts.append(f"\nAvailable Tools:\n" + "\n".join(f"- {desc}" for desc in tool_descriptions))
    
    return "\n".join(system_parts)


def _prepare_model_messages(messages: List[BaseMessage], system_message: str) -> List[BaseMessage]:
    """Prepare messages for the model, handling tool sequences and system message placement."""
    if not messages:
        return [SystemMessage(content=system_message)]
    
    first_turn = len(messages) == 1 and getattr(messages[0], "type", getattr(messages[0], "role", "human")) in ("human", "user")
    leading_role = getattr(messages[0], "type", getattr(messages[0], "role", None))
    
    # Handle tool sequence to avoid invalid message ordering
    if leading_role == "tool":
        tool_content = getattr(messages[0], "content", "")
        synthesized = ([SystemMessage(content=system_message)] if first_turn else [])
        synthesized.extend([
            SystemMessage(content="You just received a tool result. Use it to continue the response."),
            HumanMessage(content=f"Tool result:\n{tool_content}")
        ])
        return synthesized
    
    # Handle normal conversation flow
    return [SystemMessage(content=system_message)] + messages if first_turn else messages


def create_agent_node(model: BaseChatModel, tools: List[BaseTool]):
    """Create the main agent node with tool calling capabilities."""
    # Bind tools to the model so it can emit tool_calls
    model_with_tools = model.bind_tools(tools)
    
    def agent_node(state: AgentState) -> AgentState:
        """Main agent node that processes messages and generates responses."""
        messages = state["messages"]
        context = state.get("conversation_context", {})
        
        # Debug log to track conversation context availability
        logger.info(f"Agent node: conversation_context keys: {list(context.keys()) if context else 'None'}")
        if context and context.get("recent_cravings"):
            logger.info(f"Agent node: Found {len(context['recent_cravings'])} cravings in conversation_context")
        else:
            logger.warning("Agent node: No recent_cravings found in conversation_context")
        
        # Build system message with context and tools
        tool_descriptions = _build_tool_descriptions(tools)
        system_message = _build_system_message(context, tool_descriptions)
        
        # Prepare messages for the model
        model_messages = _prepare_model_messages(messages, system_message)
        
        # Get response from model (with tools bound)
        response = model_with_tools.invoke(model_messages)
        
        # Update state with new message
        new_messages = messages + [response]
        
        return {
            **state,
            "messages": new_messages,
            "current_step": "agent_response"
        }
    
    return agent_node

def create_response_formatter():
    """Create a node that formats the final response with user context."""
    
    def response_formatter(state: AgentState) -> AgentState:
        # This node can be used to add final formatting, validation, or logging
        return {
            **state,
            "current_step": "response_formatted"
        }
    
    return response_formatter

def should_continue(state: AgentState) -> str:
    """Determine if the agent should continue to tools, format response, or end."""
    messages = state["messages"]
    last_message = messages[-1]
    
    # Check if the last message has tool calls
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    # Check if we should format the response (e.g., add user context)
    if state.get("conversation_context"):
        return "format_response"
    
    return "end"

def create_user_context_message(user_data: Dict[str, Any]) -> str:
    """Create a context message from user data."""
    if not user_data:
        return ""
    
    context_parts = []
    
    if user_data.get("quit_date"):
        quit_date = user_data["quit_date"]
        days_since_quit = (date.today() - quit_date).days
        context_parts.append(f"Quit date: {quit_date} ({days_since_quit} days ago)")
    
    if user_data.get("quit_reason"):
        context_parts.append(f"Quit reason: {user_data['quit_reason']}")
    
    if user_data.get("cigarettes_per_day"):
        context_parts.append(f"Previous consumption: {user_data['cigarettes_per_day']} cigarettes/day")
    
    if context_parts:
        return f"\n\nUser Context: {' | '.join(context_parts)}"
    
    return ""

def calculate_money_saved(quit_date: date, cigarettes_per_day: int, price_per_cigarette: float = 0.5) -> float:
    """Calculate money saved since quitting."""
    days_since_quit = (date.today() - quit_date).days
    if days_since_quit <= 0:
        return 0.0
    return days_since_quit * cigarettes_per_day * price_per_cigarette

def get_milestone_message(days_since_quit: int) -> Optional[str]:
    """Get a milestone message based on days since quitting."""
    milestones = {
        1: "🎉 First day smoke-free! Your body is already healing.",
        7: "🌟 One week! The worst of withdrawal is behind you.",
        30: "🏆 One month! Your lung function is improving.",
        90: "💪 Three months! Your risk of heart disease is decreasing.",
        365: "🎊 One year! Your risk of heart disease is half that of a smoker.",
    }
    return milestones.get(days_since_quit)
