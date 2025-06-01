#!/usr/bin/env python3
"""
MCP Server for Wikipedia search tools.
Provides Wikipedia search capabilities with caching and result processing.
"""

import logging
import os
import sys
from urllib.parse import quote

# Add parent directory to path first
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from mcp.server.fastmcp import FastMCP

from langchain_community.utilities import WikipediaAPIWrapper
from core.cache import cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wiki-server")

# Create FastMCP server
mcp = FastMCP("Wikipedia Server")

@mcp.tool()
def wikipedia_query_run(query: str) -> str:
    """
    Search Wikipedia for information about a given topic.
    
    Args:
        query: The search query for Wikipedia
        
    Returns:
        Wikipedia article content with source URL
    """
    try:
        # Input validation
        if not query or not isinstance(query, str):
            return "Invalid query: Please provide a valid search term."
        
        # Sanitize query
        query = query.strip()
        if len(query) > 300:
            query = query[:300]
        
        # Check cache first
        cache_key_params = {
            'top_k_results': 3,
            'doc_content_chars_max': 3000
        }
        
        cached_result = cache.get('wikipedia', query, **cache_key_params)
        if cached_result is not None:
            logger.info(f"Cache hit for Wikipedia search: {query[:50]}...")
            return cached_result
        
        # Make API call
        logger.info(f"Making Wikipedia API call for: {query[:50]}...")
        api_wrapper = WikipediaAPIWrapper(top_k_results=3, doc_content_chars_max=3000)
        result = api_wrapper.run(query)
        
        # Limit result size to avoid token issues
        if len(result) > 4000:
            result = result[:4000] + "... [content truncated for brevity]"
        
        # Add Wikipedia source URL with proper encoding
        wiki_title = quote(query.replace(' ', '_'), safe='')
        wiki_url = f"https://en.wikipedia.org/wiki/{wiki_title}"
        result += f"\n\nSources:\n{wiki_url}"
        
        # Cache the results (24 hours TTL for Wikipedia)
        cache.set('wikipedia', query, result, ttl=86400, **cache_key_params)
        
        return result
        
    except Exception as e:
        error_msg = f"Wikipedia search encountered an error: {str(e)}"
        logger.error(error_msg)
        
        # Cache error results for shorter time (5 minutes)
        cache.set('wikipedia', query, error_msg, ttl=300, **cache_key_params)
        
        return error_msg

if __name__ == "__main__":
    mcp.run()