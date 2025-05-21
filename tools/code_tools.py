# tools/code_tools.py

from langchain_core.tools import Tool
from .secure_executor import secure_python_exec
from .math_tools import stirling_tool


def create_code_execution_tool():
    """
    Create a Python code execution tool with security measures.
    Returns:
        Configured code execution tool
    """
    try:
        repl_tool = Tool(
            name="python_repl",
            description="""
            A Python shell. Use this to execute python commands. Input should be a valid python command. 
            If you want to see the output of a value, you should print it out with `print(...)`.
            """,
            func=secure_python_exec,
        )

        print("Successfully initialized Python REPL tool")
        return repl_tool

    except Exception as e:
        print(f"Failed to initialize Python REPL tool: {e}")
        return None


def parse_code_execution_error(error_content):
    """
    Parse code execution errors and provide more helpful responses.
    Args:
        error_content: The error text from the code execution
    Returns:
        User-friendly error message
    """
    try:
        if "memory" in error_content.lower():
            return "I encountered a memory limitation while executing this code. The calculation you requested requires more memory than is available in the execution environment."
        elif "timeout" in error_content.lower():
            return "The code execution timed out. This calculation is too complex to complete within the allowed time limit."
        else:
            # Extract the actual error message from the full trace
            error_lines = error_content.split('\n')
            for line in error_lines:
                if "Error:" in line or "Exception:" in line:
                    return f"Code execution error: {line}"
            return "There was a problem executing the code. Please try a different approach."
    except Exception:
        return "An error occurred during code execution. Please try again with a simpler request."


def get_code_tools():
    """
    Get all tools needed for the code agent.
    Returns:
        List of code agent tools
    """
    tools = []

    repl_tool = create_code_execution_tool()
    if repl_tool:
        tools.append(repl_tool)

    tools.append(stirling_tool)

    return tools