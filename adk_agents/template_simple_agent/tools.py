"""Tools for template_simple_agent.

Provides utility functions that the agent can call to retrieve
real-time information such as current time.
"""
from datetime import datetime, timezone, timedelta


def get_current_time() -> dict:
    """Get the current time in Eastern timezone.

    Returns:
        dict: Current time information including time, timezone, and formatted string
    """
    # Eastern Time is UTC-5 (EST) or UTC-4 (EDT)
    eastern = timezone(timedelta(hours=-5))
    now = datetime.now(eastern)

    return {
        "current_time": now.strftime("%I:%M %p"),
        "date": now.strftime("%B %d, %Y"),
        "timezone": "EST (Eastern Standard Time)",
        "formatted": now.strftime("%A, %B %d, %Y at %I:%M %p EST")
    }
