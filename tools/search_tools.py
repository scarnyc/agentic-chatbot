# tools/search_tools.py

import re
import json
from typing import Dict, Any, List
from langchain_core.tools import Tool
from langchain_community.tools.tavily_search.tool import TavilySearchResults
from core.cache import cache


class TavilyResultTracker:
    """Class to track Tavily search results."""

    def __init__(self):
        self.last_results = {}

    def store_result(self, session_id, results):
        try:
            self.last_results[session_id] = results
        except Exception as e:
            print(f"Error storing Tavily results: {e}")
            self.last_results[session_id] = []

    def get_result(self, session_id):
        return self.last_results.get(session_id, [])


# Create a global instance of the tracker
tavily_tracker = TavilyResultTracker()


def process_search_results(results, max_tokens=1000, max_results=3, max_chars_per_result=2000):
    """
    Process and truncate search results to stay within token budget.
    Args:
        results: Raw search results from Tavily
        max_tokens: Maximum total tokens to return (reduced from 2000)
        max_results: Maximum number of results to return
        max_chars_per_result: Maximum characters per result content
    Returns:
        Processed and truncated search results
    """
    processed_results = []
    estimated_tokens = 0

    # Handle different result formats
    if isinstance(results, dict) and 'results' in results:
        results_list = results['results']
    elif isinstance(results, list):
        results_list = results
    else:
        print(f"Unexpected results format: {type(results)}")
        return [{
            "url": "https://en.wikipedia.org/wiki/Search_error",
            "content": "Search returned an unexpected format. Please try a different query.",
            "title": "Search Format Error"
        }]

    if all('score' in r for r in results_list):
        results_list = sorted(results_list,
                              key=lambda x: x.get('score', 0),
                              reverse=True)

    results_list = results_list[:max_results]

    for result in results_list:
        content = result.get('content', '')
        if len(content) > max_chars_per_result:
            content = content[:max_chars_per_result] + "..."
            result['content'] = content

        result_tokens = len(content) // 4

        if estimated_tokens + result_tokens > max_tokens:
            remaining_tokens = max_tokens - estimated_tokens
            if remaining_tokens > 50:
                truncated_length = max(0, remaining_tokens * 3)
                result['content'] = content[:truncated_length] + "..." if truncated_length > 0 else ""
                estimated_tokens = max_tokens
                processed_results.append(result)
            break

        estimated_tokens += result_tokens
        processed_results.append(result)

        if estimated_tokens >= max_tokens:
            break

    print(
        f"Processed search results: {len(processed_results)} items, ~{estimated_tokens} tokens"
    )
    return processed_results


def extract_key_facts(search_results, max_facts=5):
    """
    Extract key facts from search results for better citation.
    Args:
        search_results: Processed search results
        max_facts: Maximum number of key facts to extract
    Returns:
        List of key facts with their sources
    """
    facts = []

    for i, result in enumerate(search_results):
        source_url = result.get('url', '')
        content = result.get('content', '')

        sentences = [
            s.strip() for s in content.split('.') if len(s.strip()) > 20
        ]

        for j, sentence in enumerate(sentences[:2]):
            if len(facts) >= max_facts:
                break

            facts.append({
                'content': sentence,
                'source_index': f"{i}-{j}",
                'url': source_url
            })

    return facts


def extract_urls_from_tavily_result(content: str) -> List[str]:
    """
    Extract URLs from Tavily search results content.
    Args:
        content: The content string from the agent
    Returns:
        List of extracted URLs or empty list if none found
    """
    if not content:
        return []

    try:
        tavily_pattern = r"Action: tavily_search_results\s+Action Input: .*?\s+Observation: (.*?)(?:\n\nThought:|$)"
        tavily_matches = re.findall(tavily_pattern, content, re.DOTALL)

        urls = []
        for match in tavily_matches:
            try:
                data = json.loads(match.strip())
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'url' in item:
                            urls.append(item['url'])
                elif isinstance(data, dict) and 'results' in data:
                    for item in data['results']:
                        if isinstance(item, dict) and 'url' in item:
                            urls.append(item['url'])
            except json.JSONDecodeError:
                url_pattern = r'https?://[^\s"\')]+'
                found_urls = re.findall(url_pattern, match)
                urls.extend(found_urls)
            except Exception as e:
                print(f"Error extracting URLs from Tavily result: {e}")

        return urls[:5]
    except Exception as e:
        print(f"Error in extract_urls_from_tavily_result: {e}")
        return []


def format_citations(content: str) -> str:
    """
    Clean up content by removing citation markup and adding sources list.
    Args:
        content: The text content to process
    Returns:
        The content with citations removed and sources appended
    """
    if not content or not isinstance(content, str):
        return content

    try:
        # Remove any existing citation tags
        import re
        content = re.sub(r'<cite index="[^"]*">(.*?)</cite>', r'\1', content)
        
        urls = extract_urls_from_tavily_result(content)

        if urls and "Sources:" not in content:
            sources_text = "\n\nSources:\n"
            for url in urls:
                sources_text += f"{url}\n"
            content += sources_text

        return content
    except Exception as e:
        print(f"Error in format_citations: {e}")
        return content


def create_tavily_search_tool(tavily_api_key):
    """
    Create the Tavily search tool with token management.
    Args:
        tavily_api_key: API key for Tavily
    Returns:
        Configured search tool or None if failed
    """
    try:
        def tavily_search_with_processing(query, *args, **kwargs):
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
                print(f"Cache hit for Tavily search: {query[:50]}...")
                return cached_result
            
            try:
                print(f"Making Tavily API call for: {query[:50]}...")
                results = TavilySearchResults(api_key=tavily_api_key,
                                             k=3,
                                             include_raw_content=True,
                                             include_images=False,
                                             include_answer=True,
                                             max_results=3,
                                             search_depth="basic")(query, *args, **kwargs)

                processed_results = process_search_results(results, 
                                                         max_tokens=1000,
                                                         max_results=3,
                                                         max_chars_per_result=2000)
                
                # Cache the results (30 minutes TTL for search results)
                cache.set('tavily', query, processed_results, ttl=1800, **cache_key_params)
                
                return processed_results
                
            except Exception as e:
                error_result = [{
                    "url": "https://example.com/search_error",
                    "content": "Search encountered an error. The search service may be unavailable or experiencing high load. Please try a more specific query or try again later.",
                    "title": "Search Error"
                }]
                
                print(f"Error in Tavily search: {e}")
                
                # Cache error results for shorter time (5 minutes) to avoid repeated failures
                cache.set('tavily', query, error_result, ttl=300, **cache_key_params)
                
                return error_result

        search_tool = Tool(
            name="tavily_search_results",
            func=tavily_search_with_processing,
            description=
            "Search the web for current information. Useful for questions about current events or trending topics."
        )

        print(
            "Successfully initialized Tavily Search with token management")
        return search_tool

    except Exception as e:
        print(f"Failed to initialize Tavily Search: {e}")
        return None
