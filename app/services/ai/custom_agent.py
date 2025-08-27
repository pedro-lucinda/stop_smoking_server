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
        
        if state.get("quit_date"):
            context["quit_date"] = state["quit_date"]
            context["days_since_quit"] = state.get("days_since_quit", 0)
        
        if state.get("quit_reason"):
            context["quit_reason"] = state["quit_reason"]
            
        if state.get("cigarettes_per_day"):
            context["cigarettes_per_day"] = state["cigarettes_per_day"]
        
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

def create_agent_node(model: BaseChatModel, tools: List[BaseTool]):
    """Create the main agent node with tool calling capabilities."""

    # Bind tools to the model so it can emit tool_calls
    model_with_tools = model.bind_tools(tools)
    
    def agent_node(state: AgentState) -> AgentState:
        # Get the last message
        messages = state["messages"]
        context = state.get("conversation_context", {})
        
        # Create tool descriptions for the model
        tool_descriptions = []
        for tool in tools:
            tool_descriptions.append(f"{tool.name}: {tool.description}")
        
        # Build personalized system message
        system_parts = [SYSTEM_POLICY]
        
        # Add user context
        if context:
            context_parts = []
            if context.get("quit_date"):
                context_parts.append(f"Quit Date: {context['quit_date']}")
            if context.get("days_since_quit"):
                context_parts.append(f"Days Since Quit: {context['days_since_quit']}")
            if context.get("quit_reason"):
                context_parts.append(f"Quit Reason: {context['quit_reason']}")
            if context.get("cigarettes_per_day"):
                context_parts.append(f"Previous Consumption: {context['cigarettes_per_day']} cigarettes/day")
            if context.get("milestone"):
                context_parts.append(f"Milestone: {context['milestone']}")
            
            if context_parts:
                system_parts.append(f"\nUser Context:\n" + "\n".join(f"- {part}" for part in context_parts))
        
        # Add tool information (helps the model choose correctly)
        system_parts.append(f"\nAvailable Tools:\n" + "\n".join(f"- {desc}" for desc in tool_descriptions))
        
        system_message = "\n".join(system_parts)
        
        # Only prepend system on the first turn to preserve valid tool-call sequencing
        first_turn = len(messages) == 1 and getattr(messages[0], "type", getattr(messages[0], "role", "human")) in ("human", "user")
        leading_role = None
        if messages:
            leading_role = getattr(messages[0], "type", getattr(messages[0], "role", None))

        if leading_role == "tool":
            # Avoid invalid sequence: convert leading tool message into a user summary
            tool_content = getattr(messages[0], "content", "")
            synthesized = [SystemMessage(content=system_message)] if first_turn else []
            synthesized.append(SystemMessage(content="You just received a tool result. Use it to continue the response."))
            synthesized.append(HumanMessage(content=f"Tool result:\n{tool_content}"))
            model_messages = synthesized
        else:
            if first_turn:
                model_messages = [SystemMessage(content=system_message)] + messages
            else:
                model_messages = messages
        
        # Get response from model (with tools bound)
        response = model_with_tools.invoke(model_messages)
        
        # Update state
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
        # For now, we'll just pass through the state
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
