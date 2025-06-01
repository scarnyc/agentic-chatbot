#!/usr/bin/env python3
"""
MCP Server for web search tools.
Provides Tavily search capabilities with caching and result processing.
"""

import logging
import os
import sys

# Add parent directory to path first
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from mcp.server.fastmcp import FastMCP

from langchain_community.tools.tavily_search.tool import TavilySearchResults
from tools.search_tools import process_search_results
from core.cache import cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("search-server")

# Create FastMCP server
mcp = FastMCP("Search Server")

@mcp.tool()
def tavily_search_results(query: str) -> str:
    """
    Search the web for current information using Tavily.
    
    Args:
        query: The search query
        
    Returns:
        Processed search results with URLs and content
    """
    try:
        # Check for API key
        tavily_api_key = os.getenv('TAVILY_API_KEY')
        if not tavily_api_key:
            return "Error: TAVILY_API_KEY environment variable not set"
        
        # Check cache first
        cache_key_params = {
            'k': 3,
            'include_raw_content': True,
            'include_images': False,
            'include_answer': True,
            'max_results': 3,
            'search_depth': 'basic'
        }
        
        cached_result = cache.get('tavily', query, **cache_key_params)
        if cached_result is not None:
            logger.info(f"Cache hit for Tavily search: {query[:50]}...")
            # Format cached results for display
            formatted_results = ""
            for i, result in enumerate(cached_result, 1):
                formatted_results += f"\n{i}. {result.get('title', 'No title')}\n"
                formatted_results += f"URL: {result.get('url', 'No URL')}\n"
                formatted_results += f"Content: {result.get('content', 'No content')}\n"
            return formatted_results.strip()
        
        # Make API call
        logger.info(f"Making Tavily API call for: {query[:50]}...")
        search_tool = TavilySearchResults(
            api_key=tavily_api_key,
            k=3,
            include_raw_content=True,
            include_images=False,
            include_answer=True,
            max_results=3,
            search_depth="basic"
        )
        
        results = search_tool(query)
        processed_results = process_search_results(
            results, 
            max_tokens=1000,
            max_results=3,
            max_chars_per_result=2000
        )
        
        # Cache the results (30 minutes TTL)
        cache.set('tavily', query, processed_results, ttl=1800, **cache_key_params)
        
        # Format results for display
        formatted_results = ""
        for i, result in enumerate(processed_results, 1):
            formatted_results += f"\n{i}. {result.get('title', 'No title')}\n"
            formatted_results += f"URL: {result.get('url', 'No URL')}\n"
            formatted_results += f"Content: {result.get('content', 'No content')}\n"
        
        return formatted_results.strip()
        
    except Exception as e:
        error_msg = f"Error in Tavily search: {str(e)}"
        logger.error(error_msg)
        return error_msg

if __name__ == "__main__":
    mcp.run()