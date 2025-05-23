# tools/datetime_tools.py

import logging
from datetime import datetime, timezone
from langchain.tools import tool

logger = logging.getLogger(__name__)

@tool
def get_current_datetime() -> str:
    """
    Get the current date and time in a user-friendly format.
    
    Returns:
        str: Current date and time in format "Friday, May 23, 2025 at 12:45 PM EST"
    
    Use this tool when:
    - User asks about current date, time, or "today"
    - User mentions "this week", "next week", "this month", etc.
    - User asks about weather forecasts or current events
    - Any time-sensitive queries that need current context
    """
    try:
        # Get current datetime in UTC
        now_utc = datetime.now(timezone.utc)
        
        # Format for user display
        formatted_date = now_utc.strftime("%A, %B %d, %Y at %I:%M %p UTC")
        
        # Log to API calls log for monitoring
        api_logger = logging.getLogger('api_calls')
        api_logger.info(f"Retrieved current datetime: {formatted_date}")
        
        return f"Current date and time: {formatted_date}"
        
    except Exception as e:
        error_msg = f"Error getting current datetime: {str(e)}"
        logger.error(error_msg)
        return error_msg

@tool  
def get_current_date_simple() -> str:
    """
    Get just the current date in simple format for search context.
    
    Returns:
        str: Current date in format "May 23, 2025"
        
    Use this tool to get date context before making search queries about:
    - Current events, news, weather
    - "This week", "next week", "recent" events  
    - Any time-sensitive information
    """
    try:
        now_utc = datetime.now(timezone.utc)
        simple_date = now_utc.strftime("%B %d, %Y")
        
        # Log to API calls log for monitoring
        api_logger = logging.getLogger('api_calls')
        api_logger.info(f"Retrieved simple current date for search context: {simple_date}")
        
        return simple_date
        
    except Exception as e:
        error_msg = f"Error getting current date: {str(e)}"
        logger.error(error_msg)
        return error_msg