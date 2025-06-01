#!/usr/bin/env python3
"""
Simple MCP Tools Integration using subprocess for local development.
This provides a fallback mechanism when full MCP client libraries are not available.
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional
from langchain_core.tools import Tool

logger = logging.getLogger(__name__)

class SimpleMCPTool:
    """Simple tool that calls MCP servers via subprocess."""
    
    def __init__(self, name: str, description: str, server_path: str, tool_name: str):
        self.name = name
        self.description = description
        self.server_path = server_path
        self.tool_name = tool_name
    
    def __call__(self, **kwargs) -> str:
        """Call the MCP server tool via subprocess."""
        try:
            # Create a simple test request
            input_data = {
                "tool": self.tool_name,
                "args": kwargs
            }
            
            # For now, fall back to direct import calls
            # This is a temporary solution until proper MCP client is working
            return self._fallback_call(**kwargs)
            
        except Exception as e:
            logger.error(f"Error calling MCP tool {self.name}: {e}")
            return f"Error: {str(e)}"
    
    def _fallback_call(self, **kwargs) -> str:
        """Fallback to direct tool calls."""
        try:
            if self.tool_name == "python_repl":
                from tools.secure_executor import secure_python_exec
                return secure_python_exec(kwargs.get("code", ""))
            
            elif self.tool_name == "stirling_approximation_for_factorial":
                from tools.math_tools import stirling_approximation_factorial
                return stirling_approximation_factorial(kwargs.get("n", "0"))
            
            elif self.tool_name == "tavily_search_results":
                from tools.search_tools import create_tavily_search_tool
                import os
                tavily_api_key = os.getenv("TAVILY_API_KEY")
                if tavily_api_key:
                    tool = create_tavily_search_tool(tavily_api_key)
                    return str(tool.invoke(kwargs.get("query", "")))
                return "Tavily API key not configured"
            
            elif self.tool_name == "wikipedia_query_run":
                from tools.wiki_tools import create_wikipedia_tool
                tool = create_wikipedia_tool()
                return tool.invoke(kwargs.get("query", ""))
            
            elif self.tool_name == "get_current_datetime":
                from tools.datetime_tools import get_current_datetime
                return get_current_datetime.invoke("")
            
            elif self.tool_name == "get_current_date_simple":
                from tools.datetime_tools import get_current_date_simple
                return get_current_date_simple.invoke("")
            
            elif self.tool_name == "store_text_memory":
                from tools.unified_multimodal_tools import store_text_memory
                return store_text_memory.invoke({
                    "content": kwargs.get("content", ""),
                    "category": kwargs.get("category", "general"),
                    "metadata": kwargs.get("metadata", "{}")
                })
            
            elif self.tool_name == "store_image_memory":
                from tools.unified_multimodal_tools import store_image_memory
                return store_image_memory.invoke({
                    "image_base64": kwargs.get("image_base64", ""),
                    "description": kwargs.get("description", ""),
                    "metadata": kwargs.get("metadata", "{}")
                })
            
            elif self.tool_name == "search_memories":
                from tools.unified_multimodal_tools import search_memories
                return search_memories.invoke({
                    "query": kwargs.get("query", ""),
                    "query_type": kwargs.get("query_type", "text"),
                    "limit": kwargs.get("limit", 5),
                    "category_filter": kwargs.get("category_filter", "")
                })
            
            elif self.tool_name == "get_vector_db_info":
                from tools.unified_multimodal_tools import get_vector_db_info
                return get_vector_db_info.invoke("")
            
            elif self.tool_name == "analyze_image_and_store":
                from tools.unified_multimodal_tools import analyze_image_and_store
                return analyze_image_and_store.invoke({
                    "image_base64": kwargs.get("image_base64", ""),
                    "analysis_request": kwargs.get("analysis_request", "Analyze this image and describe what you see"),
                    "store_in_memory": kwargs.get("store_in_memory", True),
                    "category": kwargs.get("category", "visual_analysis")
                })
            
            else:
                return f"Unknown tool: {self.tool_name}"
                
        except Exception as e:
            logger.error(f"Error in fallback call for {self.tool_name}: {e}")
            return f"Error: {str(e)}"

def create_simple_mcp_tools() -> List[Tool]:
    """
    Create LangChain Tools using simple MCP approach.
    
    Returns:
        List of LangChain Tool objects
    """
    tools = []
    
    # Tool definitions
    tool_definitions = [
        # Code tools
        {
            "name": "python_repl",
            "description": """A Python shell. Use this to execute python commands. Input should be a valid python command. 
            If you want to see the output of a value, you should print it out with `print(...)`.""",
            "server_path": "mcp_servers/code_server.py",
            "tool_name": "python_repl"
        },
        {
            "name": "stirling_approximation_for_factorial",
            "description": "Calculates Stirling's approximation for n! (factorial of n). Use this for large n (e.g., n > 70) or if direct calculation fails due to resource limits. Input should be a string representing the integer n.",
            "server_path": "mcp_servers/code_server.py",
            "tool_name": "stirling_approximation_for_factorial"
        },
        
        # Search tools
        {
            "name": "tavily_search_results",
            "description": "Search the web for current information. Useful for questions about current events or trending topics.",
            "server_path": "mcp_servers/search_server.py",
            "tool_name": "tavily_search_results"
        },
        
        # Wikipedia tools
        {
            "name": "wikipedia_query_run",
            "description": "Searches Wikipedia for information about a given topic. Use for historical, scientific, or general knowledge queries.",
            "server_path": "mcp_servers/wiki_server.py",
            "tool_name": "wikipedia_query_run"
        },
        
        # DateTime tools
        {
            "name": "get_current_datetime",
            "description": """Get the current date and time in a user-friendly format.
            
            Use this tool when:
            - User asks about current date, time, or "today"
            - User mentions "this week", "next week", "this month", etc.
            - User asks about weather forecasts or current events
            - Any time-sensitive queries that need current context""",
            "server_path": "mcp_servers/datetime_server.py",
            "tool_name": "get_current_datetime"
        },
        {
            "name": "get_current_date_simple",
            "description": """Get just the current date in simple format for search context.
            
            Use this tool to get date context before making search queries about:
            - Current events, news, weather
            - "This week", "next week", "recent" events  
            - Any time-sensitive information""",
            "server_path": "mcp_servers/datetime_server.py",
            "tool_name": "get_current_date_simple"
        },
        
        # Multimodal tools
        {
            "name": "store_text_memory",
            "description": """Store text content in the vector database for long-term memory.
            
            Use this tool to:
            - Store important facts or information for future reference
            - Save user preferences and learned behaviors
            - Archive significant conversation insights
            - Build long-term memory for better context""",
            "server_path": "mcp_servers/multimodal_server.py",
            "tool_name": "store_text_memory"
        },
        {
            "name": "store_image_memory",
            "description": """Store an image with description in the vector database for multimodal memory.
            
            Use this tool to:
            - Store important visual information
            - Save screenshots, diagrams, or charts for future reference
            - Build visual memory alongside textual memory
            - Enable image-based retrieval and search""",
            "server_path": "mcp_servers/multimodal_server.py",
            "tool_name": "store_image_memory"
        },
        {
            "name": "search_memories",
            "description": """Search the vector database for relevant content using semantic similarity.
            
            Use this tool to:
            - Find relevant past conversations or facts
            - Retrieve visual content by text description
            - Access stored knowledge for better responses
            - Provide context from long-term memory""",
            "server_path": "mcp_servers/multimodal_server.py",
            "tool_name": "search_memories"
        },
        {
            "name": "get_vector_db_info",
            "description": """Get information about the current vector database configuration and available options.
            
            Use this tool to:
            - Check which vector database is currently active
            - See available database options
            - Monitor system health
            - Debug configuration issues""",
            "server_path": "mcp_servers/multimodal_server.py",
            "tool_name": "get_vector_db_info"
        },
        {
            "name": "analyze_image_and_store",
            "description": """Analyze an image using Claude's vision capabilities and optionally store in vector database.
            
            Use this tool to:
            - Understand visual content in conversations
            - Extract information from images, charts, diagrams
            - Build visual memory for future reference
            - Combine image analysis with searchable storage""",
            "server_path": "mcp_servers/multimodal_server.py",
            "tool_name": "analyze_image_and_store"
        }
    ]
    
    # Create LangChain Tools
    for tool_def in tool_definitions:
        try:
            mcp_tool = SimpleMCPTool(
                name=tool_def["name"],
                description=tool_def["description"],
                server_path=tool_def["server_path"],
                tool_name=tool_def["tool_name"]
            )
            
            # Create parameter-specific wrapper functions
            def create_tool_func(mcp_tool_instance):
                if mcp_tool_instance.tool_name == "python_repl":
                    def tool_func(code: str) -> str:
                        return mcp_tool_instance(code=code)
                elif mcp_tool_instance.tool_name == "stirling_approximation_for_factorial":
                    def tool_func(n: str) -> str:
                        return mcp_tool_instance(n=n)
                elif mcp_tool_instance.tool_name in ["tavily_search_results", "wikipedia_query_run"]:
                    def tool_func(query: str) -> str:
                        return mcp_tool_instance(query=query)
                elif mcp_tool_instance.tool_name in ["get_current_datetime", "get_current_date_simple", "get_vector_db_info"]:
                    def tool_func(input: str = "") -> str:
                        # These tools don't need input, ignore it
                        return mcp_tool_instance()
                elif mcp_tool_instance.tool_name == "store_text_memory":
                    def tool_func(content: str, category: str = "general", metadata: str = "{}") -> str:
                        return mcp_tool_instance(content=content, category=category, metadata=metadata)
                elif mcp_tool_instance.tool_name == "store_image_memory":
                    def tool_func(image_base64: str, description: str, metadata: str = "{}") -> str:
                        return mcp_tool_instance(image_base64=image_base64, description=description, metadata=metadata)
                elif mcp_tool_instance.tool_name == "search_memories":
                    def tool_func(query: str, query_type: str = "text", limit: int = 5, category_filter: str = "") -> str:
                        return mcp_tool_instance(query=query, query_type=query_type, limit=limit, category_filter=category_filter)
                elif mcp_tool_instance.tool_name == "analyze_image_and_store":
                    def tool_func(image_base64: str, analysis_request: str = "Analyze this image and describe what you see", 
                                store_in_memory: bool = True, category: str = "visual_analysis") -> str:
                        return mcp_tool_instance(
                            image_base64=image_base64, 
                            analysis_request=analysis_request,
                            store_in_memory=store_in_memory,
                            category=category
                        )
                else:
                    def tool_func(**kwargs) -> str:
                        return mcp_tool_instance(**kwargs)
                return tool_func
            
            tool_func = create_tool_func(mcp_tool)
            
            langchain_tool = Tool(
                name=tool_def["name"],
                description=tool_def["description"],
                func=tool_func
            )
            
            tools.append(langchain_tool)
            logger.info(f"Created simple MCP tool: {tool_def['name']}")
            
        except Exception as e:
            logger.error(f"Failed to create tool {tool_def['name']}: {e}")
    
    return tools

def get_simple_mcp_tools() -> List[Tool]:
    """
    Get simple MCP tools for LangChain integration.
    
    Returns:
        List of LangChain Tool objects
    """
    logger.info("Initializing simple MCP tools...")
    tools = create_simple_mcp_tools()
    logger.info(f"Successfully initialized {len(tools)} simple MCP tools")
    return tools