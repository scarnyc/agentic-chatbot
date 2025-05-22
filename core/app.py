# core/app.py

import os
import time
import logging
from typing import Annotated
from dotenv import load_dotenv
from typing_extensions import TypedDict
from langchain_anthropic import ChatAnthropic
from langgraph.graph import MessagesState, START, END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from anthropic import APIError, RateLimitError, InternalServerError

from tools.prompt import get_prompt
from tools.wiki_tools import create_wikipedia_tool
from tools.search_tools import create_tavily_search_tool
from tools.code_tools import get_code_tools

load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

class AnthropicAPIErrorHandler:
    """Handles Anthropic API errors with appropriate retry logic and user-friendly messages."""
    
    @staticmethod
    def get_error_message(error: Exception) -> str:
        """Convert API errors to user-friendly messages."""
        if hasattr(error, 'status_code'):
            status_code = error.status_code
            if status_code == 400:
                return "Invalid request format. Please try rephrasing your message."
            elif status_code == 401:
                return "Authentication error. Please check your API key configuration."
            elif status_code == 403:
                return "Permission denied. Your API key may not have sufficient permissions."
            elif status_code == 404:
                return "Resource not found. Please try again."
            elif status_code == 413:
                return "Your message is too long. Please try a shorter message."
            elif status_code == 429:
                return "Rate limit exceeded. Please wait a moment and try again."
            elif status_code == 500:
                return "Internal server error. Please try again in a moment."
            elif status_code == 529:
                return "Service temporarily overloaded. Please try again in a moment."
        
        return f"An unexpected error occurred: {str(error)}"
    
    @staticmethod
    def should_retry(error: Exception) -> bool:
        """Determine if error should trigger a retry."""
        if hasattr(error, 'status_code'):
            status_code = error.status_code
            # Retry on rate limits, overload, and server errors
            return status_code in [429, 500, 529]
        return False
    
    @staticmethod
    def get_retry_delay(attempt: int, error: Exception) -> float:
        """Calculate delay before retry based on error type and attempt number."""
        if hasattr(error, 'status_code'):
            status_code = error.status_code
            if status_code == 429:  # Rate limit
                return min(2 ** attempt, 60)  # Exponential backoff, max 60s
            elif status_code == 529:  # Overloaded
                return min(5 * attempt, 30)  # Linear backoff, max 30s
            elif status_code == 500:  # Server error
                return min(1 * attempt, 10)  # Short backoff, max 10s
        return 1  # Default 1 second

def create_anthropic_model_with_error_handling():
    """Create Anthropic model with comprehensive error handling."""
    if not anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    try:
        llm = ChatAnthropic(
            model_name="claude-sonnet-4-20250514",
            anthropic_api_key=anthropic_api_key,
            max_tokens=1500,
            thinking={
                "type": "enabled",
                "budget_tokens": 1024
            },
            # Enable keep-alive as recommended by Anthropic
            timeout=300.0,  # 5 minute timeout
        )
        logger.info("Successfully initialized Claude model with error handling")
        return llm
    except Exception as e:
        error_msg = AnthropicAPIErrorHandler.get_error_message(e)
        logger.error(f"Failed to initialize Claude model: {error_msg}")
        raise RuntimeError(f"Failed to initialize Claude model: {error_msg}")

anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
if not anthropic_api_key:
    print("ANTHROPIC_API_KEY environment variable not set.")
    print(
        "Please set the ANTHROPIC_API_KEY environment variable in your .env file"
    )

tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    print("TAVILY_API_KEY environment variable not set.")
    print(
        "Please set the TAVILY_API_KEY environment variable in your .env file"
    )

llm = create_anthropic_model_with_error_handling()

if tavily_api_key:
    tavily_search_tool = create_tavily_search_tool(tavily_api_key)

wikipedia_tool = create_wikipedia_tool()
code_tools = get_code_tools()

tools = [wikipedia_tool, tavily_search_tool] + code_tools
tool_node = ToolNode(tools)
model_with_tools = llm.bind_tools(tools)
prompt_template = ChatPromptTemplate.from_messages([
    ("system", get_prompt()),
    MessagesPlaceholder(variable_name="messages"),
    ])
model_chain = prompt_template | model_with_tools


def should_continue(state: MessagesState) -> str:
    """
    Determines whether the agent should continue processing or end.
    Args:
        state: The current state of the graph, containing messages.
    Returns:
        "tools" if the last message contains tool calls, END otherwise.
    """
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        if any(tc.get('name') in [t.name for t in tools] for tc in last_message.tool_calls):
             return "tools"

    if isinstance(last_message, AIMessage) and last_message.additional_kwargs.get("tool_calls"):
         pass

    return END


def call_model(state: MessagesState) -> dict:
    """
    The main agent node function. Invokes the LLM with error handling and retry logic.
    Args:
        state: The current state of the graph.
    Returns:
        A dictionary containing the updated messages list.
    """
    messages = state["messages"]
    max_retries = 3
    
    for attempt in range(max_retries + 1):
        try:
            response = model_chain.invoke({"messages": messages})
            
            # Log request ID if available for support tracking
            if hasattr(response, 'response_metadata') and 'request-id' in response.response_metadata:
                request_id = response.response_metadata['request-id']
                logger.info(f"Anthropic request ID: {request_id}")
            
            return {"messages": [response]}
            
        except Exception as e:
            error_handler = AnthropicAPIErrorHandler()
            
            # Log the error with details
            error_msg = error_handler.get_error_message(e)
            logger.error(f"Anthropic API error (attempt {attempt + 1}/{max_retries + 1}): {error_msg}")
            
            # Log request ID if available for support
            if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                request_id = e.response.headers.get('request-id')
                if request_id:
                    logger.error(f"Failed request ID: {request_id}")
            
            # Check if we should retry
            if attempt < max_retries and error_handler.should_retry(e):
                delay = error_handler.get_retry_delay(attempt + 1, e)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                continue
            else:
                # Return error message as AI response instead of raising
                from langchain_core.messages import AIMessage
                error_response = AIMessage(content=error_msg)
                return {"messages": [error_response]}


workflow = StateGraph(MessagesState)
workflow.add_node("chatbot", call_model)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("chatbot")
workflow.add_conditional_edges(
    "chatbot",
    should_continue,
    {
        "tools": "tools", 
        END: END
    }
)
workflow.add_edge("tools", "chatbot")
memory = MemorySaver()
store = InMemoryStore()
langgraph_app = workflow.compile(checkpointer=memory, store=store)
