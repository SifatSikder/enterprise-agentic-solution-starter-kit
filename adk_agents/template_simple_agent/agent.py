"""Agent definition for template_simple_agent.

This module defines a basic ADK agent with a time utility tool,
serving as a template for building more complex agents.
"""
from google.adk.agents import Agent

from config.settings import settings
from .tools import get_current_time

# Create the agent (must be named root_agent for ADK web)
root_agent = Agent(
    name="template_simple_agent",
    model=settings.default_model,
    description="A simple template agent with basic utility tools",
    instruction="""You are a helpful assistant that can provide useful information.

TOOLS AVAILABLE:
1. get_current_time() - Gets current time in Eastern timezone

Your role:
- Greet users warmly and help them with their questions
- When they ask about time, call get_current_time()
- Provide clear and helpful responses

IMPORTANT: Always use tools instead of making up information!

Example Interactions:

User: "What time is it?"
You: [call get_current_time()] It's currently [time from result].
""",
    tools=[get_current_time]
)
