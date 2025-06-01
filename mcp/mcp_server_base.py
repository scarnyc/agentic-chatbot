#!/usr/bin/env python3
"""
Simple MCP server base for compatibility.
Since mcp.server.fastmcp doesn't exist in our installation, 
this provides a minimal compatible interface.
"""

import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class SimpleMCPServer:
    """Simple MCP server base class."""
    
    def __init__(self, name: str):
        self.name = name
        self.tools: Dict[str, Callable] = {}
        logger.info(f"Initialized {name}")
    
    def tool(self, name: str = None):
        """Decorator to register tools."""
        def decorator(func: Callable):
            tool_name = name or func.__name__
            self.tools[tool_name] = func
            logger.info(f"Registered tool: {tool_name}")
            return func
        return decorator
    
    def run(self):
        """Run the server (stub implementation)."""
        logger.info(f"Running {self.name} with {len(self.tools)} tools")
        # In a real implementation, this would start the server
        # For our fallback system, we just log the availability

# Compatibility alias
FastMCP = SimpleMCPServer