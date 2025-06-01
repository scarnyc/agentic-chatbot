#!/usr/bin/env python3
"""
Enhanced MCP Tools Integration with multiple server support.
Provides session management, tool mapping, and proper resource cleanup.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from contextlib import ExitStack
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from langchain_core.tools import Tool

logger = logging.getLogger(__name__)

@dataclass
class ServerConfig:
    """Configuration for an MCP server."""
    name: str
    command: List[str]
    description: str
    tools: List[str]

@dataclass
class ToolDefinition:
    """Definition of a tool exposed by an MCP server."""
    name: str
    description: str
    server_name: str
    input_schema: Dict[str, Any]

class EnhancedMCPSession:
    """Manages a connection to a single MCP server."""
    
    def __init__(self, server_config: ServerConfig):
        self.server_config = server_config
        self.process: Optional[subprocess.Popen] = None
        self.is_connected = False
    
    async def connect(self) -> bool:
        """Connect to the MCP server."""
        try:
            # For now, we'll use the fallback approach
            # In a full implementation, this would start the server process
            self.is_connected = True
            logger.info(f"Connected to {self.server_config.name} server")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {self.server_config.name}: {e}")
            return False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on this server."""
        if not self.is_connected:
            return {"error": "Server not connected"}
        
        # Use fallback implementation
        return self._fallback_call_tool(tool_name, arguments)
    
    def _fallback_call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Fallback tool implementation using direct imports."""
        try:
            if tool_name == "python_repl":
                from tools.secure_executor import secure_python_exec
                return secure_python_exec(arguments.get("code", ""))
            
            elif tool_name == "stirling_approximation_for_factorial":
                from tools.math_tools import stirling_approximation_factorial
                return stirling_approximation_factorial(arguments.get("n", "0"))
            
            elif tool_name == "tavily_search_results":
                from tools.search_tools import create_tavily_search_tool
                tavily_api_key = os.getenv("TAVILY_API_KEY")
                if tavily_api_key:
                    tool = create_tavily_search_tool(tavily_api_key)
                    return str(tool.invoke(arguments.get("query", "")))
                return "Tavily API key not configured"
            
            elif tool_name == "wikipedia_query_run":
                from tools.wiki_tools import create_wikipedia_tool
                tool = create_wikipedia_tool()
                return tool.invoke(arguments.get("query", ""))
            
            elif tool_name == "get_current_datetime":
                from tools.datetime_tools import get_current_datetime
                return get_current_datetime.invoke("")
            
            elif tool_name == "get_current_date_simple":
                from tools.datetime_tools import get_current_date_simple
                return get_current_date_simple.invoke("")
            
            elif tool_name == "store_text_memory":
                from tools.unified_multimodal_tools import store_text_memory
                return store_text_memory.invoke({
                    "content": arguments.get("content", ""),
                    "category": arguments.get("category", "general"),
                    "metadata": arguments.get("metadata", "{}")
                })
            
            elif tool_name == "store_image_memory":
                from tools.unified_multimodal_tools import store_image_memory
                return store_image_memory.invoke({
                    "image_base64": arguments.get("image_base64", ""),
                    "description": arguments.get("description", ""),
                    "metadata": arguments.get("metadata", "{}")
                })
            
            elif tool_name == "search_memories":
                from tools.unified_multimodal_tools import search_memories
                return search_memories.invoke({
                    "query": arguments.get("query", ""),
                    "query_type": arguments.get("query_type", "text"),
                    "limit": arguments.get("limit", 5),
                    "category_filter": arguments.get("category_filter", "")
                })
            
            elif tool_name == "get_vector_db_info":
                from tools.unified_multimodal_tools import get_vector_db_info
                return get_vector_db_info.invoke("")
            
            elif tool_name == "analyze_image_and_store":
                from tools.unified_multimodal_tools import analyze_image_and_store
                return analyze_image_and_store.invoke({
                    "image_base64": arguments.get("image_base64", ""),
                    "analysis_request": arguments.get("analysis_request", "Analyze this image and describe what you see"),
                    "store_in_memory": arguments.get("store_in_memory", True),
                    "category": arguments.get("category", "visual_analysis")
                })
            
            else:
                return f"Unknown tool: {tool_name}"
                
        except Exception as e:
            logger.error(f"Error in fallback call for {tool_name}: {e}")
            return f"Error: {str(e)}"
    
    async def disconnect(self):
        """Disconnect from the server."""
        if self.process:
            self.process.terminate()
            self.process = None
        self.is_connected = False

class EnhancedMCPClient:
    """Enhanced MCP client that can connect to multiple servers."""
    
    def __init__(self, config_file: str = "mcp_config.json"):
        """
        Initialize the enhanced MCP client.
        
        Args:
            config_file: Path to the server configuration file
        """
        self.config_file = config_file
        self.client_sessions: Dict[str, EnhancedMCPSession] = {}
        self.available_tools: Dict[str, ToolDefinition] = {}
        self.tool_to_session: Dict[str, str] = {}
        self.exit_stack: Optional[ExitStack] = None
        self.server_configs: Dict[str, ServerConfig] = {}
        
    async def connect_to_servers(self) -> bool:
        """
        Connect to all configured MCP servers.
        
        Returns:
            True if all connections successful, False otherwise
        """
        try:
            # Load server configuration
            if not os.path.exists(self.config_file):
                logger.error(f"Configuration file not found: {self.config_file}")
                return False
            
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            # Initialize exit stack for resource management
            self.exit_stack = ExitStack()
            
            # Connect to each server
            success_count = 0
            total_servers = len(config['servers'])
            
            for server_name, server_config in config['servers'].items():
                try:
                    server_cfg = ServerConfig(
                        name=server_name,
                        command=server_config['command'],
                        description=server_config['description'],
                        tools=server_config.get('tools', [])
                    )
                    self.server_configs[server_name] = server_cfg
                    
                    success = await self.connect_to_server(server_cfg)
                    if success:
                        success_count += 1
                        logger.info(f"✅ Connected to {server_name}")
                    else:
                        logger.error(f"❌ Failed to connect to {server_name}")
                        
                except Exception as e:
                    logger.error(f"Error connecting to {server_name}: {e}")
            
            logger.info(f"Connected to {success_count}/{total_servers} MCP servers")
            logger.info(f"Available tools: {list(self.available_tools.keys())}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to connect to servers: {e}")
            return False
    
    async def connect_to_server(self, server_config: ServerConfig) -> bool:
        """
        Connect to a single MCP server.
        
        Args:
            server_config: Configuration for the server to connect to
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create session
            session = EnhancedMCPSession(server_config)
            
            # Connect to the server
            success = await session.connect()
            if not success:
                return False
            
            # Store session
            self.client_sessions[server_config.name] = session
            
            # Add tools to available tools based on config
            tool_descriptions = self._get_tool_descriptions()
            
            for tool_name in server_config.tools:
                if tool_name in tool_descriptions:
                    tool_def = ToolDefinition(
                        name=tool_name,
                        description=tool_descriptions[tool_name],
                        server_name=server_config.name,
                        input_schema=self._get_tool_input_schema(tool_name)
                    )
                    
                    self.available_tools[tool_name] = tool_def
                    self.tool_to_session[tool_name] = server_config.name
            
            logger.info(f"Server {server_config.name} provides {len(server_config.tools)} tools")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to server {server_config.name}: {e}")
            return False
    
    def _get_tool_descriptions(self) -> Dict[str, str]:
        """Get tool descriptions mapping."""
        return {
            "python_repl": """A Python shell. Use this to execute python commands. Input should be a valid python command. 
            If you want to see the output of a value, you should print it out with `print(...)`.""",
            "stirling_approximation_for_factorial": "Calculates Stirling's approximation for n! (factorial of n). Use this for large n (e.g., n > 70) or if direct calculation fails due to resource limits. Input should be a string representing the integer n.",
            "tavily_search_results": "Search the web for current information. Useful for questions about current events or trending topics.",
            "wikipedia_query_run": "Searches Wikipedia for information about a given topic. Use for historical, scientific, or general knowledge queries.",
            "get_current_datetime": """Get the current date and time in a user-friendly format.
            
            Use this tool when:
            - User asks about current date, time, or "today"
            - User mentions "this week", "next week", "this month", etc.
            - User asks about weather forecasts or current events
            - Any time-sensitive queries that need current context""",
            "get_current_date_simple": """Get just the current date in simple format for search context.
            
            Use this tool to get date context before making search queries about:
            - Current events, news, weather
            - "This week", "next week", "recent" events  
            - Any time-sensitive information""",
            "store_text_memory": """Store text content in the vector database for long-term memory.
            
            Use this tool to:
            - Store important facts or information for future reference
            - Save user preferences and learned behaviors
            - Archive significant conversation insights
            - Build long-term memory for better context""",
            "store_image_memory": """Store an image with description in the vector database for multimodal memory.
            
            Use this tool to:
            - Store important visual information
            - Save screenshots, diagrams, or charts for future reference
            - Build visual memory alongside textual memory
            - Enable image-based retrieval and search""",
            "search_memories": """Search the vector database for relevant content using semantic similarity.
            
            Use this tool to:
            - Find relevant past conversations or facts
            - Retrieve visual content by text description
            - Access stored knowledge for better responses
            - Provide context from long-term memory""",
            "get_vector_db_info": """Get information about the current vector database configuration and available options.
            
            Use this tool to:
            - Check which vector database is currently active
            - See available database options
            - Monitor system health
            - Debug configuration issues""",
            "analyze_image_and_store": """Analyze an image using Claude's vision capabilities and optionally store in vector database.
            
            Use this tool to:
            - Understand visual content in conversations
            - Extract information from images, charts, diagrams
            - Build visual memory for future reference
            - Combine image analysis with searchable storage"""
        }
    
    def _get_tool_input_schema(self, tool_name: str) -> Dict[str, Any]:
        """Get input schema for a tool."""
        schemas = {
            "python_repl": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"}
                },
                "required": ["code"]
            },
            "stirling_approximation_for_factorial": {
                "type": "object",
                "properties": {
                    "n": {"type": "string", "description": "Number to calculate factorial approximation for"}
                },
                "required": ["n"]
            },
            "tavily_search_results": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            },
            "wikipedia_query_run": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Wikipedia search query"}
                },
                "required": ["query"]
            },
            "get_current_datetime": {
                "type": "object",
                "properties": {},
                "required": []
            },
            "get_current_date_simple": {
                "type": "object",
                "properties": {},
                "required": []
            },
            "store_text_memory": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Text content to store"},
                    "category": {"type": "string", "description": "Category for the content", "default": "general"},
                    "metadata": {"type": "string", "description": "JSON metadata", "default": "{}"}
                },
                "required": ["content"]
            },
            "store_image_memory": {
                "type": "object",
                "properties": {
                    "image_base64": {"type": "string", "description": "Base64 encoded image"},
                    "description": {"type": "string", "description": "Description of the image"},
                    "metadata": {"type": "string", "description": "JSON metadata", "default": "{}"}
                },
                "required": ["image_base64", "description"]
            },
            "search_memories": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "query_type": {"type": "string", "description": "Type of search", "default": "text"},
                    "limit": {"type": "integer", "description": "Maximum results", "default": 5},
                    "category_filter": {"type": "string", "description": "Category filter", "default": ""}
                },
                "required": ["query"]
            },
            "get_vector_db_info": {
                "type": "object",
                "properties": {},
                "required": []
            },
            "analyze_image_and_store": {
                "type": "object",
                "properties": {
                    "image_base64": {"type": "string", "description": "Base64 encoded image"},
                    "analysis_request": {"type": "string", "description": "Analysis request", "default": "Analyze this image and describe what you see"},
                    "store_in_memory": {"type": "boolean", "description": "Whether to store in memory", "default": True},
                    "category": {"type": "string", "description": "Storage category", "default": "visual_analysis"}
                },
                "required": ["image_base64"]
            }
        }
        return schemas.get(tool_name, {})
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the appropriate MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool execution result
        """
        try:
            # Check if tool exists
            if tool_name not in self.tool_to_session:
                return {"error": f"Tool '{tool_name}' not found"}
            
            # Get the session for this tool
            server_name = self.tool_to_session[tool_name]
            session = self.client_sessions.get(server_name)
            
            if not session:
                return {"error": f"No session found for server '{server_name}'"}
            
            # Call the tool
            logger.debug(f"Calling tool '{tool_name}' on server '{server_name}' with args: {arguments}")
            result = await session.call_tool(tool_name, arguments)
            
            return result
            
        except Exception as e:
            logger.error(f"Error calling tool '{tool_name}': {e}")
            return {"error": f"Error calling tool '{tool_name}': {str(e)}"}
    
    def get_available_tools(self) -> Dict[str, ToolDefinition]:
        """
        Get all available tools from all connected servers.
        
        Returns:
            Dictionary mapping tool names to their definitions
        """
        return self.available_tools.copy()
    
    def get_tool_to_session_mapping(self) -> Dict[str, str]:
        """
        Get the mapping of tool names to server names.
        
        Returns:
            Dictionary mapping tool names to server names
        """
        return self.tool_to_session.copy()
    
    def get_server_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all connected servers.
        
        Returns:
            Dictionary with server information
        """
        server_info = {}
        
        for server_name, config in self.server_configs.items():
            is_connected = server_name in self.client_sessions
            tools_count = len([t for t in self.available_tools.values() if t.server_name == server_name])
            
            server_info[server_name] = {
                "description": config.description,
                "command": config.command,
                "connected": is_connected,
                "tools_count": tools_count,
                "tools": [t for t in self.available_tools.keys() if self.tool_to_session.get(t) == server_name]
            }
        
        return server_info
    
    async def cleanup(self):
        """
        Clean up all connections and resources.
        """
        try:
            # Disconnect all sessions
            for session in self.client_sessions.values():
                await session.disconnect()
            
            if self.exit_stack:
                self.exit_stack.close()
                logger.info("All MCP connections cleaned up")
            
            # Clear internal state
            self.client_sessions.clear()
            self.available_tools.clear()
            self.tool_to_session.clear()
            self.exit_stack = None
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect_to_servers()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()

def create_enhanced_mcp_tools() -> List[Tool]:
    """
    Create LangChain Tools from enhanced MCP client.
    
    Returns:
        List of LangChain Tool objects
    """
    # This will be populated by the enhanced client
    # For now, return empty list and let the async initialization handle it
    return []

class EnhancedMCPToolWrapper:
    """Wrapper to make enhanced MCP tools work with LangChain synchronously."""
    
    def __init__(self, client: EnhancedMCPClient, tool_def: ToolDefinition):
        self.client = client
        self.tool_def = tool_def
    
    def __call__(self, **kwargs) -> str:
        """Synchronous wrapper for async MCP tool calls."""
        try:
            # Run the async function
            result = asyncio.run(self.client.call_tool(self.tool_def.name, kwargs))
            return str(result)
        except Exception as e:
            logger.error(f"Error calling enhanced MCP tool {self.tool_def.name}: {e}")
            return f"Error calling tool: {str(e)}"

def create_langchain_tools_from_mcp_client(client: EnhancedMCPClient) -> List[Tool]:
    """
    Create LangChain Tools from an initialized enhanced MCP client.
    
    Args:
        client: Initialized EnhancedMCPClient
        
    Returns:
        List of LangChain Tool objects
    """
    tools = []
    
    for tool_name, tool_def in client.get_available_tools().items():
        try:
            wrapper = EnhancedMCPToolWrapper(client, tool_def)
            
            # Create parameter-specific wrapper functions
            def create_tool_func(wrapper_instance):
                if wrapper_instance.tool_def.name == "python_repl":
                    def tool_func(code: str) -> str:
                        return wrapper_instance(code=code)
                elif wrapper_instance.tool_def.name == "stirling_approximation_for_factorial":
                    def tool_func(n: str) -> str:
                        return wrapper_instance(n=n)
                elif wrapper_instance.tool_def.name in ["tavily_search_results", "wikipedia_query_run"]:
                    def tool_func(query: str) -> str:
                        return wrapper_instance(query=query)
                elif wrapper_instance.tool_def.name in ["get_current_datetime", "get_current_date_simple", "get_vector_db_info"]:
                    def tool_func(input: str = "") -> str:
                        return wrapper_instance()
                elif wrapper_instance.tool_def.name == "store_text_memory":
                    def tool_func(content: str, category: str = "general", metadata: str = "{}") -> str:
                        return wrapper_instance(content=content, category=category, metadata=metadata)
                elif wrapper_instance.tool_def.name == "store_image_memory":
                    def tool_func(image_base64: str, description: str, metadata: str = "{}") -> str:
                        return wrapper_instance(image_base64=image_base64, description=description, metadata=metadata)
                elif wrapper_instance.tool_def.name == "search_memories":
                    def tool_func(query: str, query_type: str = "text", limit: int = 5, category_filter: str = "") -> str:
                        return wrapper_instance(query=query, query_type=query_type, limit=limit, category_filter=category_filter)
                elif wrapper_instance.tool_def.name == "analyze_image_and_store":
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
                name=tool_def.name,
                description=tool_def.description,
                func=tool_func
            )
            
            tools.append(langchain_tool)
            logger.info(f"Created enhanced MCP tool: {tool_def.name} from {tool_def.server_name} server")
            
        except Exception as e:
            logger.error(f"Failed to create tool {tool_def.name}: {e}")
    
    return tools

# Global instance for the enhanced MCP client
enhanced_mcp_client: Optional[EnhancedMCPClient] = None

async def initialize_enhanced_mcp_client(config_file: str = "mcp_config.json") -> EnhancedMCPClient:
    """
    Initialize the global enhanced MCP client.
    
    Args:
        config_file: Path to the server configuration file
        
    Returns:
        Initialized EnhancedMCPClient instance
    """
    global enhanced_mcp_client
    
    logger.info("Initializing enhanced MCP client...")
    
    enhanced_mcp_client = EnhancedMCPClient(config_file)
    success = await enhanced_mcp_client.connect_to_servers()
    
    if success:
        logger.info("Enhanced MCP client initialized successfully")
        
        # Log server information
        server_info = enhanced_mcp_client.get_server_info()
        for server_name, info in server_info.items():
            status = "✅ Connected" if info["connected"] else "❌ Disconnected"
            logger.info(f"  {server_name}: {status} - {info['tools_count']} tools")
    else:
        logger.error("Failed to initialize enhanced MCP client")
    
    return enhanced_mcp_client

def get_enhanced_mcp_tools() -> List[Tool]:
    """
    Get enhanced MCP tools for LangChain integration.
    
    Returns:
        List of LangChain Tool objects
    """
    global enhanced_mcp_client
    
    if not enhanced_mcp_client:
        # Initialize synchronously if not already done
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            enhanced_mcp_client = loop.run_until_complete(initialize_enhanced_mcp_client())
        finally:
            loop.close()
    
    if enhanced_mcp_client:
        tools = create_langchain_tools_from_mcp_client(enhanced_mcp_client)
        logger.info(f"Successfully created {len(tools)} enhanced MCP tools")
        return tools
    else:
        logger.error("Failed to initialize enhanced MCP client")
        return []

if __name__ == "__main__":
    # Test the enhanced MCP client
    async def test_enhanced_client():
        async with EnhancedMCPClient() as client:
            print(f"Connected to {len(client.client_sessions)} servers")
            print(f"Available tools: {list(client.available_tools.keys())}")
            
            # Test a tool call
            if "get_current_datetime" in client.available_tools:
                result = await client.call_tool("get_current_datetime", {})
                print(f"DateTime result: {result}")
    
    asyncio.run(test_enhanced_client())