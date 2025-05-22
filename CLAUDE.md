# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Running the Application
```bash
python main.py
```
This starts the FastAPI server with WebSocket support on http://0.0.0.0:8000

### Development Dependencies
Install dependencies with:
```bash
pip install -r requirements.txt
```

### Code Quality
Run code formatting with:
```bash
black .
```

Run tests with:
```bash
pytest
```

## Architecture Overview

This is an agentic workflow system built with **FastAPI, LangGraph, and Anthropic Claude** that provides a chat interface with tool-enabled AI agents.

### Core Components

**main.py**: FastAPI application with WebSocket endpoints for real-time chat
- Manages conversation state and WebSocket connections
- Handles streaming responses from LangGraph
- Includes content filtering for problematic tool outputs (JSON-like responses)
- Serves static files and HTML templates

**core/app.py**: LangGraph workflow configuration  
- Defines the agent state graph with `chatbot` and `tools` nodes
- Integrates Claude 3.7 Sonnet with tool binding
- Memory management with MemorySaver and InMemoryStore
- Tool routing logic in `should_continue()` function

**tools/** directory: Modular tool implementations
- `code_tools.py`: Python code execution with security measures
- `search_tools.py`: Tavily web search integration  
- `wiki_tools.py`: Wikipedia search functionality
- `secure_executor.py`: Sandboxed Python execution environment
- `prompt.py`: System prompt with detailed tool usage guidelines

### Data Flow
1. User sends message via WebSocket to `/ws/{conversation_id}`
2. Message added to conversation history and passed to LangGraph
3. LangGraph routes through `chatbot` → `tools` (if needed) → `chatbot` cycle
4. Responses streamed back as chunks via WebSocket
5. Content filtered to prevent raw tool output display

### Environment Requirements
- `ANTHROPIC_API_KEY`: Required for Claude model access
- `TAVILY_API_KEY`: Required for web search functionality

### Key Design Patterns
- **Stateful conversations**: Each conversation has unique ID with persistent memory
- **Tool orchestration**: Agent can chain Wikipedia, web search, and code execution
- **Streaming responses**: Real-time message delivery via WebSocket chunks with intelligent sentence spacing
- **Content sanitization**: Filters problematic tool outputs before user display
- **Error resilience**: Graceful handling of tool failures and WebSocket disconnections
- **Responsive UI**: REM-based CSS with proper text wrapping and containment
- **Smart formatting**: Scientific notation for large numbers, proper text spacing