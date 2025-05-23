# tools/wiki_tools.py

import logging
from urllib.parse import quote
from langchain_core.tools import Tool
from langchain_community.utilities import WikipediaAPIWrapper
from core.cache import cache

logger = logging.getLogger('api_calls')

def create_wikipedia_tool():
    """
    Create a Wikipedia search tool.

    Returns:
        Configured Wikipedia tool or None if failed
    """
    try:
        api_wrapper = WikipediaAPIWrapper(top_k_results=3, doc_content_chars_max=3000)

        # Wrap the Wikipedia run to provide error handling, token management, and caching
        def wiki_query_with_handling(query):
            # Input validation
            if not query or not isinstance(query, str):
                return "Invalid query: Please provide a valid search term."
            
            # Sanitize query - remove potentially problematic characters
            query = query.strip()
            if len(query) > 300:  # Align with WIKIPEDIA_MAX_QUERY_LENGTH
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
            
            try:
                logger.info(f"Making Wikipedia API call for: {query[:50]}...")
                result = api_wrapper.run(query)

                # Limit result size to avoid token issues
                if len(result) > 4000:
                    result = result[:4000] + "... [content truncated for brevity]"

                # Add Wikipedia source URL with proper encoding
                wiki_title = quote(query.replace(' ', '_'), safe='')
                wiki_url = f"https://en.wikipedia.org/wiki/{wiki_title}"
                result += f"\n\nSources:\n{wiki_url}"

                # Cache the results (24 hours TTL for Wikipedia - more stable content)
                cache.set('wikipedia', query, result, ttl=86400, **cache_key_params)
                
                return result
                
            except Exception as e:
                error_result = "Wikipedia search encountered an error. Please try a different query or check your connection."
                
                logger.error(f"Error in Wikipedia search: {e}")
                
                # Cache error results for shorter time (5 minutes)
                cache.set('wikipedia', query, error_result, ttl=300, **cache_key_params)
                
                return error_result

        # Create the tool with our wrapped function
        wiki_tool = Tool(
            name="wikipedia_query_run",
            func=wiki_query_with_handling,
            description="Searches Wikipedia for information about a given topic. Use for historical, scientific, or general knowledge queries."
        )

        logger.info("Successfully initialized Wikipedia tool")
        return wiki_tool

    except Exception as e:
        logger.error(f"Failed to initialize Wikipedia tool: {e}")
        return None