#!/usr/bin/env python3
"""
Enhanced MCP Client for connecting to multiple MCP servers.
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

# Install required MCP packages if not available
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("Installing required MCP packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp", "--quiet"])
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

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

class EnhancedMCPClient:
    """Enhanced MCP client that can connect to multiple servers."""
    
    def __init__(self, config_file: str = "mcp_config.json"):
        """
        Initialize the enhanced MCP client.
        
        Args:
            config_file: Path to the server configuration file
        """
        self.config_file = config_file
        self.client_sessions: Dict[str, ClientSession] = {}
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
            # Create server parameters
            server_params = StdioServerParameters(
                command=server_config.command[0],
                args=server_config.command[1:] if len(server_config.command) > 1 else []
            )
            
            # Create stdio client and add to exit stack
            stdio_client_ctx = stdio_client(server_params)
            read_stream, write_stream = await self.exit_stack.enter_async_context(stdio_client_ctx)
            
            # Create client session and add to exit stack  
            session_ctx = ClientSession(read_stream, write_stream)
            session = await self.exit_stack.enter_async_context(session_ctx)
            
            # Initialize the session
            await session.initialize()
            
            # Get available tools from the server
            tools_result = await session.list_tools()
            
            # Store session and tools
            self.client_sessions[server_config.name] = session
            
            # Process tools and add to available tools
            if hasattr(tools_result, 'tools'):
                for tool in tools_result.tools:
                    tool_def = ToolDefinition(
                        name=tool.name,
                        description=tool.description,
                        server_name=server_config.name,
                        input_schema=tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                    )
                    
                    self.available_tools[tool.name] = tool_def
                    self.tool_to_session[tool.name] = server_config.name
                    
                logger.info(f"Server {server_config.name} provides {len(tools_result.tools)} tools")
            else:
                logger.warning(f"Server {server_config.name} returned no tools")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to server {server_config.name}: {e}")
            return False
    
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
            if self.exit_stack:
                await self.exit_stack.aclose()
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

async def call_enhanced_mcp_tool(tool_name: str, **kwargs) -> str:
    """
    Convenience function to call tools through the enhanced MCP client.
    
    Args:
        tool_name: Name of the tool to call
        **kwargs: Tool arguments
        
    Returns:
        Tool result as string
    """
    global enhanced_mcp_client
    
    if not enhanced_mcp_client:
        return "Error: Enhanced MCP client not initialized"
    
    try:
        result = await enhanced_mcp_client.call_tool(tool_name, kwargs)
        return str(result)
    except Exception as e:
        logger.error(f"Error calling enhanced MCP tool {tool_name}: {e}")
        return f"Error: {str(e)}"

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