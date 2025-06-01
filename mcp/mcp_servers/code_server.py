#!/usr/bin/env python3
"""
MCP Server for Python code execution tools.
Provides secure Python REPL and mathematical computation capabilities.
"""

import logging
import sys
import os

# Add parent directory to path first
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from mcp.mcp_server_base import FastMCP
from tools.secure_executor import secure_python_exec
from tools.math_tools import stirling_approximation_factorial

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("code-server")

# Create FastMCP server
mcp = FastMCP("Code Execution Server")

@mcp.tool()
def python_repl(code: str) -> str:
    """
    Execute Python code in a secure environment.
    
    Args:
        code: Python code to execute
        
    Returns:
        The output of the code execution
    """
    try:
        result = secure_python_exec(code)
        return result
    except Exception as e:
        return f"Error executing code: {str(e)}"

@mcp.tool()
def stirling_approximation_for_factorial(n: str) -> str:
    """
    Calculate Stirling's approximation for large factorials.
    
    Args:
        n: The number (as string) to calculate factorial approximation for
        
    Returns:
        Stirling's approximation result
    """
    try:
        result = stirling_approximation_factorial(n)
        return result
    except Exception as e:
        return f"Error calculating Stirling approximation: {str(e)}"

if __name__ == "__main__":
    mcp.run()