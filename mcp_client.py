#!/usr/bin/env python3
"""
MCP Client implementation for connecting to local MCP servers.
This provides a unified interface to all MCP tool servers.
"""

import asyncio
import json
import logging
import subprocess
import sys
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

import mcp
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

class MCPClient:
    """Client for managing connections to MCP servers."""
    
    def __init__(self):
        self.servers: Dict[str, Dict[str, Any]] = {
            "code": {
                "command": [sys.executable, "mcp_servers/code_server.py"],
                "description": "Python code execution and math tools",
                "session": None,
                "tools": []
            },
            "search": {
                "command": [sys.executable, "mcp_servers/search_server.py"],
                "description": "Web search using Tavily",
                "session": None,
                "tools": []
            },
            "wiki": {
                "command": [sys.executable, "mcp_servers/wiki_server.py"],
                "description": "Wikipedia search",
                "session": None,
                "tools": []
            },
            "datetime": {
                "command": [sys.executable, "mcp_servers/datetime_server.py"],
                "description": "Current date and time tools",
                "session": None,
                "tools": []
            },
            "multimodal": {
                "command": [sys.executable, "mcp_servers/multimodal_server.py"],
                "description": "Vector database and multimodal tools",
                "session": None,
                "tools": []
            }
        }
        self.connected_servers: Dict[str, ClientSession] = {}
    
    async def connect_to_server(self, server_name: str) -> bool:
        """Connect to a specific MCP server."""
        if server_name not in self.servers:
            logger.error(f"Unknown server: {server_name}")
            return False
        
        if server_name in self.connected_servers:
            logger.info(f"Already connected to {server_name}")
            return True
        
        try:
            server_config = self.servers[server_name]
            
            # Start the server process
            logger.info(f"Starting MCP server: {server_name}")
            
            # Use stdio_client to connect
            async with stdio_client(server_config["command"]) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the session
                    await session.initialize()
                    
                    # List available tools
                    result = await session.list_tools()
                    tools = result.tools if hasattr(result, 'tools') else []
                    
                    logger.info(f"Connected to {server_name} with {len(tools)} tools")
                    
                    # Store session and tools info
                    server_config["tools"] = [tool.name for tool in tools]
                    self.connected_servers[server_name] = session
                    
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to connect to {server_name}: {e}")
            return False
    
    async def connect_all_servers(self) -> Dict[str, bool]:
        """Connect to all available MCP servers."""
        results = {}
        
        for server_name in self.servers.keys():
            try:
                success = await self.connect_to_server(server_name)
                results[server_name] = success
            except Exception as e:
                logger.error(f"Error connecting to {server_name}: {e}")
                results[server_name] = False
        
        return results
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on a specific server."""
        if server_name not in self.connected_servers:
            logger.error(f"Not connected to server: {server_name}")
            return {"error": f"Not connected to server: {server_name}"}
        
        try:
            session = self.connected_servers[server_name]
            
            # Call the tool
            result = await session.call_tool(tool_name, arguments)
            
            # Extract content from result
            if hasattr(result, 'content') and result.content:
                if len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        return content.text
                    else:
                        return str(content)
            
            return str(result)
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on {server_name}: {e}")
            return {"error": f"Error calling tool {tool_name}: {str(e)}"}
    
    def get_available_tools(self) -> Dict[str, List[str]]:
        """Get list of available tools from all connected servers."""
        available_tools = {}
        
        for server_name, server_config in self.servers.items():
            if server_name in self.connected_servers:
                available_tools[server_name] = server_config["tools"]
            else:
                available_tools[server_name] = []
        
        return available_tools
    
    async def disconnect_all(self):
        """Disconnect from all servers."""
        for server_name, session in self.connected_servers.items():
            try:
                # Sessions will be closed automatically by context managers
                logger.info(f"Disconnected from {server_name}")
            except Exception as e:
                logger.error(f"Error disconnecting from {server_name}: {e}")
        
        self.connected_servers.clear()

# Global MCP client instance
mcp_client = MCPClient()

async def initialize_mcp_client():
    """Initialize the global MCP client."""
    logger.info("Initializing MCP client...")
    
    results = await mcp_client.connect_all_servers()
    
    connected_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    logger.info(f"MCP client initialized: {connected_count}/{total_count} servers connected")
    
    if connected_count > 0:
        available_tools = mcp_client.get_available_tools()
        for server_name, tools in available_tools.items():
            if tools:
                logger.info(f"  {server_name}: {tools}")
    
    return mcp_client

# Convenience functions for LangChain integration
async def call_mcp_tool(server_name: str, tool_name: str, **kwargs) -> str:
    """
    Convenience function to call MCP tools.
    
    Args:
        server_name: Name of the MCP server
        tool_name: Name of the tool to call
        **kwargs: Tool arguments
    
    Returns:
        Tool result as string
    """
    try:
        result = await mcp_client.call_tool(server_name, tool_name, kwargs)
        return str(result)
    except Exception as e:
        logger.error(f"Error calling MCP tool {server_name}.{tool_name}: {e}")
        return f"Error: {str(e)}"

if __name__ == "__main__":
    # Test the MCP client
    async def test_client():
        client = await initialize_mcp_client()
        
        # Test a simple tool call
        if "datetime" in client.connected_servers:
            result = await client.call_tool("datetime", "get_current_datetime", {})
            print(f"Current time: {result}")
        
        await client.disconnect_all()
    
    asyncio.run(test_client())