# tools/wiki_tools.py

from langchain_core.tools import Tool
from langchain_community.utilities import WikipediaAPIWrapper

def create_wikipedia_tool():
    """
    Create a Wikipedia search tool.

    Returns:
        Configured Wikipedia tool or None if failed
    """
    try:
        api_wrapper = WikipediaAPIWrapper(top_k_results=3, doc_content_chars_max=3000)

        # Wrap the Wikipedia run to provide error handling and token management
        def wiki_query_with_handling(query):
            try:
                result = api_wrapper.run(query)

                # Limit result size to avoid token issues
                if len(result) > 4000:
                    result = result[:4000] + "... [content truncated for brevity]"

                # Add Wikipedia source URL
                wiki_url = f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}"
                result += f"\n\nSources:\n{wiki_url}"

                return result
            except Exception as e:
                print(f"Error in Wikipedia search: {e}")
                return "Wikipedia search encountered an error. Please try a different query or check your connection."

        # Create the tool with our wrapped function
        wiki_tool = Tool(
            name="wikipedia_query_run",
            func=wiki_query_with_handling,
            description="Searches Wikipedia for information about a given topic. Use for historical, scientific, or general knowledge queries."
        )

        print("Successfully initialized Wikipedia tool")
        return wiki_tool

    except Exception as e:
        print(f"Failed to initialize Wikipedia tool: {e}")
        return None