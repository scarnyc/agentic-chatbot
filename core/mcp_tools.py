#!/usr/bin/env python3
"""
MCP Tools Integration for LangGraph.
Provides MCP-based tools as LangChain Tool objects for seamless integration.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from langchain_core.tools import Tool
from mcp_client import mcp_client, initialize_mcp_client

logger = logging.getLogger(__name__)

class MCPToolWrapper:
    """Wrapper to make MCP tools work with LangChain synchronously."""
    
    def __init__(self, server_name: str, tool_name: str, description: str):
        self.server_name = server_name
        self.tool_name = tool_name
        self.description = description
    
    def __call__(self, **kwargs) -> str:
        """Synchronous wrapper for async MCP tool calls."""
        try:
            # Run the async function in the current event loop or create new one
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, we need to use a different approach
                    # For now, we'll create a task and run it
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            lambda: asyncio.run(mcp_client.call_tool(self.server_name, self.tool_name, kwargs))
                        )
                        result = future.result(timeout=30)  # 30 second timeout
                else:
                    result = loop.run_until_complete(
                        mcp_client.call_tool(self.server_name, self.tool_name, kwargs)
                    )
            except RuntimeError:
                # No event loop, create one
                result = asyncio.run(
                    mcp_client.call_tool(self.server_name, self.tool_name, kwargs)
                )
            
            return str(result)
            
        except Exception as e:
            logger.error(f"Error calling MCP tool {self.server_name}.{self.tool_name}: {e}")
            return f"Error calling tool: {str(e)}"

def create_mcp_tools() -> List[Tool]:
    """
    Create LangChain Tools from MCP servers.
    
    Returns:
        List of LangChain Tool objects
    """
    tools = []
    
    # Tool definitions matching the original tools
    tool_definitions = [
        # Code tools
        {
            "server": "code",
            "name": "python_repl",
            "description": """A Python shell. Use this to execute python commands. Input should be a valid python command. 
            If you want to see the output of a value, you should print it out with `print(...)`."""
        },
        {
            "server": "code",
            "name": "stirling_approximation_for_factorial",
            "description": "Calculates Stirling's approximation for n! (factorial of n). Use this for large n (e.g., n > 70) or if direct calculation fails due to resource limits. Input should be a string representing the integer n."
        },
        
        # Search tools
        {
            "server": "search",
            "name": "tavily_search_results",
            "description": "Search the web for current information. Useful for questions about current events or trending topics."
        },
        
        # Wikipedia tools
        {
            "server": "wiki",
            "name": "wikipedia_query_run",
            "description": "Searches Wikipedia for information about a given topic. Use for historical, scientific, or general knowledge queries."
        },
        
        # DateTime tools
        {
            "server": "datetime",
            "name": "get_current_datetime",
            "description": """Get the current date and time in a user-friendly format.
            
            Use this tool when:
            - User asks about current date, time, or "today"
            - User mentions "this week", "next week", "this month", etc.
            - User asks about weather forecasts or current events
            - Any time-sensitive queries that need current context"""
        },
        {
            "server": "datetime",
            "name": "get_current_date_simple",
            "description": """Get just the current date in simple format for search context.
            
            Use this tool to get date context before making search queries about:
            - Current events, news, weather
            - "This week", "next week", "recent" events  
            - Any time-sensitive information"""
        },
        
        # Multimodal tools
        {
            "server": "multimodal",
            "name": "store_text_memory",
            "description": """Store text content in the vector database for long-term memory.
            
            Use this tool to:
            - Store important facts or information for future reference
            - Save user preferences and learned behaviors
            - Archive significant conversation insights
            - Build long-term memory for better context"""
        },
        {
            "server": "multimodal",
            "name": "store_image_memory",
            "description": """Store an image with description in the vector database for multimodal memory.
            
            Use this tool to:
            - Store important visual information
            - Save screenshots, diagrams, or charts for future reference
            - Build visual memory alongside textual memory
            - Enable image-based retrieval and search"""
        },
        {
            "server": "multimodal",
            "name": "search_memories",
            "description": """Search the vector database for relevant content using semantic similarity.
            
            Use this tool to:
            - Find relevant past conversations or facts
            - Retrieve visual content by text description
            - Access stored knowledge for better responses
            - Provide context from long-term memory"""
        },
        {
            "server": "multimodal",
            "name": "get_vector_db_info",
            "description": """Get information about the current vector database configuration and available options.
            
            Use this tool to:
            - Check which vector database is currently active
            - See available database options
            - Monitor system health
            - Debug configuration issues"""
        },
        {
            "server": "multimodal",
            "name": "analyze_image_and_store",
            "description": """Analyze an image using Claude's vision capabilities and optionally store in vector database.
            
            Use this tool to:
            - Understand visual content in conversations
            - Extract information from images, charts, diagrams
            - Build visual memory for future reference
            - Combine image analysis with searchable storage"""
        }
    ]
    
    # Create LangChain Tools from MCP tool definitions
    for tool_def in tool_definitions:
        try:
            wrapper = MCPToolWrapper(
                server_name=tool_def["server"],
                tool_name=tool_def["name"],
                description=tool_def["description"]
            )
            
            # Handle special parameter parsing for some tools
            def create_tool_func(wrapper_instance):
                if wrapper_instance.tool_name == "python_repl":
                    def tool_func(code: str) -> str:
                        return wrapper_instance(code=code)
                elif wrapper_instance.tool_name == "stirling_approximation_for_factorial":
                    def tool_func(n: str) -> str:
                        return wrapper_instance(n=n)
                elif wrapper_instance.tool_name == "tavily_search_results":
                    def tool_func(query: str) -> str:
                        return wrapper_instance(query=query)
                elif wrapper_instance.tool_name == "wikipedia_query_run":
                    def tool_func(query: str) -> str:
                        return wrapper_instance(query=query)
                elif wrapper_instance.tool_name in ["get_current_datetime", "get_current_date_simple"]:
                    def tool_func() -> str:
                        return wrapper_instance()
                elif wrapper_instance.tool_name == "store_text_memory":
                    def tool_func(content: str, category: str = "general", metadata: str = "{}") -> str:
                        return wrapper_instance(content=content, category=category, metadata=metadata)
                elif wrapper_instance.tool_name == "store_image_memory":
                    def tool_func(image_base64: str, description: str, metadata: str = "{}") -> str:
                        return wrapper_instance(image_base64=image_base64, description=description, metadata=metadata)
                elif wrapper_instance.tool_name == "search_memories":
                    def tool_func(query: str, query_type: str = "text", limit: int = 5, category_filter: str = "") -> str:
                        return wrapper_instance(query=query, query_type=query_type, limit=limit, category_filter=category_filter)
                elif wrapper_instance.tool_name == "get_vector_db_info":
                    def tool_func() -> str:
                        return wrapper_instance()
                elif wrapper_instance.tool_name == "analyze_image_and_store":
                    def tool_func(image_base64: str, analysis_request: str = "Analyze this image and describe what you see", 
                                store_in_memory: bool = True, category: str = "visual_analysis") -> str:
                        return wrapper_instance(
                            image_base64=image_base64, 
                            analysis_request=analysis_request,
                            store_in_memory=store_in_memory,
                            category=category
                        )
                else:
                    def tool_func(**kwargs) -> str:
                        return wrapper_instance(**kwargs)
                return tool_func
            
            tool_func = create_tool_func(wrapper)
            
            langchain_tool = Tool(
                name=tool_def["name"],
                description=tool_def["description"],
                func=tool_func
            )
            
            tools.append(langchain_tool)
            logger.info(f"Created MCP tool: {tool_def['name']} from {tool_def['server']} server")
            
        except Exception as e:
            logger.error(f"Failed to create tool {tool_def['name']}: {e}")
    
    return tools

async def initialize_mcp_tools() -> List[Tool]:
    """
    Initialize MCP client and create LangChain tools.
    
    Returns:
        List of LangChain Tool objects ready for use
    """
    try:
        # Initialize MCP client
        await initialize_mcp_client()
        
        # Create tools
        tools = create_mcp_tools()
        
        logger.info(f"Successfully initialized {len(tools)} MCP tools")
        return tools
        
    except Exception as e:
        logger.error(f"Failed to initialize MCP tools: {e}")
        return []

def get_mcp_tools_sync() -> List[Tool]:
    """
    Synchronous wrapper to get MCP tools.
    
    Returns:
        List of LangChain Tool objects
    """
    try:
        # Run the async initialization
        tools = asyncio.run(initialize_mcp_tools())
        return tools
    except Exception as e:
        logger.error(f"Failed to get MCP tools synchronously: {e}")
        return []