# core/app.py

import os
import time
import logging
import asyncio
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
from core.error_recovery import ErrorRecoveryManager, RetryConfig, get_error_recovery_stats

from tools.prompt import get_prompt
from tools.wiki_tools import create_wikipedia_tool
from tools.search_tools import create_tavily_search_tool
from tools.code_tools import get_code_tools

load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Initialize error recovery manager with custom config
error_recovery_config = RetryConfig(
    max_attempts=4,  # Reduced from 5 for faster failure detection
    base_delay=0.5,  # Start with shorter delay
    max_delay=30.0,  # Reduced max delay
    exponential_base=2.0,
    jitter_factor=0.15  # Slightly more jitter
)
error_recovery_manager = ErrorRecoveryManager(error_recovery_config)

class AnthropicStopReasonHandler:
    """Handles Anthropic API stop reasons and provides appropriate responses."""
    
    @staticmethod
    def handle_stop_reason(response, messages_context=None) -> dict:
        """
        Handle different stop reasons from Anthropic API responses.
        Args:
            response: The API response object
            messages_context: Optional context for continuation requests
        Returns:
            Dict with handling information and any modifications needed
        """
        stop_reason = None
        stop_info = {
            'should_warn_user': False,
            'warning_message': None,
            'should_continue': False,
            'modified_content': None
        }
        
        # Extract stop reason from response metadata
        if hasattr(response, 'response_metadata'):
            stop_reason = response.response_metadata.get('stop_reason')
        elif hasattr(response, 'additional_kwargs'):
            stop_reason = response.additional_kwargs.get('stop_reason')
        
        if stop_reason:
            logger.info(f"Anthropic stop reason: {stop_reason}")
            
            if stop_reason == 'max_tokens':
                stop_info['should_warn_user'] = True
                stop_info['warning_message'] = "\n\n*Note: Response was truncated due to length limits. The answer may be incomplete.*"
                stop_info['modified_content'] = response.content + stop_info['warning_message']
                logger.warning("Response truncated due to max_tokens limit")
                
            elif stop_reason == 'stop_sequence':
                logger.info("Response stopped due to custom stop sequence")
                # Could add logic here to handle specific stop sequences
                
            elif stop_reason == 'tool_use':
                logger.info("Response stopped for tool use - this should be handled by LangGraph")
                # LangGraph handles tool use automatically, so this is informational
                
            elif stop_reason == 'pause_turn':
                logger.info("Response paused - implementing retry logic")
                stop_info['should_continue'] = True
                
            elif stop_reason == 'end_turn':
                logger.debug("Response completed naturally")
                # This is the normal case, no special handling needed
        
        return stop_info

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
    logger.error("ANTHROPIC_API_KEY environment variable not set.")
    logger.error(
        "Please set the ANTHROPIC_API_KEY environment variable in your .env file"
    )

tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    logger.warning("TAVILY_API_KEY environment variable not set.")
    logger.warning(
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
    The main agent node function. Invokes the LLM with advanced error recovery and stop reason handling.
    Args:
        state: The current state of the graph.
    Returns:
        A dictionary containing the updated messages list.
    """
    messages = state["messages"]
    
    async def model_operation():
        """The actual model invocation wrapped for error recovery."""
        response = model_chain.invoke({"messages": messages})
        
        # Log request ID if available for support tracking
        if hasattr(response, 'response_metadata') and 'request-id' in response.response_metadata:
            request_id = response.response_metadata['request-id']
            logger.info(f"Anthropic request ID: {request_id}")
        
        # Handle stop reasons
        stop_handler = AnthropicStopReasonHandler()
        stop_info = stop_handler.handle_stop_reason(response, messages)
        
        # Handle pause_turn with retry logic
        if stop_info['should_continue']:
            max_pause_retries = 3
            for pause_attempt in range(max_pause_retries):
                logger.info(f"Retrying paused turn (attempt {pause_attempt + 1}/{max_pause_retries})")
                await asyncio.sleep(1 + pause_attempt)  # Progressive delay
                
                try:
                    response = model_chain.invoke({"messages": messages})
                    stop_info = stop_handler.handle_stop_reason(response, messages)
                    
                    if not stop_info['should_continue']:
                        break  # Success, exit retry loop
                except Exception as retry_e:
                    logger.warning(f"Pause retry failed: {retry_e}")
                    if pause_attempt == max_pause_retries - 1:
                        # Final attempt failed, continue with original response
                        break
        
        # Modify content if needed (e.g., add truncation warning)
        if stop_info['modified_content']:
            from langchain_core.messages import AIMessage
            modified_response = AIMessage(
                content=stop_info['modified_content'],
                additional_kwargs=response.additional_kwargs if hasattr(response, 'additional_kwargs') else {},
                response_metadata=response.response_metadata if hasattr(response, 'response_metadata') else {}
            )
            return {"messages": [modified_response]}
        
        return {"messages": [response]}
    
    # Use error recovery for the model call
    try:
        # Run the async operation
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            error_recovery_manager.execute_with_retry(
                model_operation,
                operation_name="ANTHROPIC_API_CALL"
            )
        )
        return result
        
    except Exception as e:
        # Fallback error handling if error recovery fails
        error_handler = AnthropicAPIErrorHandler()
        error_msg = error_handler.get_error_message(e)
        
        # Log request ID if available for support
        if hasattr(e, 'response') and hasattr(e.response, 'headers'):
            request_id = e.response.headers.get('request-id')
            if request_id:
                logger.error(f"Failed request ID: {request_id}")
        
        logger.error(f"Final error after all retries: {error_msg}")
        
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
