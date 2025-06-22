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

### Multimodal Dependencies (Optional)
For enhanced image embeddings with CLIP, install:
```bash
pip install torch torchvision transformers
```
Note: System works with text-only embeddings if these are not installed.

### Enhanced MCP Implementation
The system now uses an enhanced Model Context Protocol (MCP) implementation:
```bash
# View MCP server configuration
cat mcp/mcp_config.json

# Test enhanced MCP client
python -c "from mcp import get_enhanced_mcp_tools; tools = get_enhanced_mcp_tools(); print(f'Loaded {len(tools)} tools')"

# View implementation details
cat mcp/MCP_IMPLEMENTATION.md
```

Key MCP features:
- **Multiple server sessions**: Each tool category runs in its own MCP server
- **Tool-to-session mapping**: Efficient routing of tool calls to appropriate servers
- **Resource management**: Proper cleanup with ExitStack context manager
- **Modular architecture**: Easy to extend with new servers and tools

MCP Servers (located in `mcp/mcp_servers/`):
- `code-server`: Python execution and mathematical tools
- `search-server`: Web search capabilities
- `wiki-server`: Wikipedia search functionality  
- `datetime-server`: Time-sensitive date/time tools
- `multimodal-server`: Vector database and multimodal operations

### File Cleanup
The `install_deps.py` file can be safely deleted - it was a temporary installation helper that is no longer needed.

### Code Quality
Run code formatting with:
```bash
black .
```

Run tests with:
```bash
pytest
```

### Testing
Run automated API error tests:
```bash
python test_api_errors.py
```

Test memory system:
```bash
python test_memory.py
```

Test extended thinking:
```bash
python test_thinking.py
```

View comprehensive testing guide:
```bash
cat TESTING_GUIDE.md
```

### Caching System
Monitor cache performance:
```bash
python core/cache_monitor.py --monitor
```

Clear cache:
```bash
python core/cache_monitor.py --clear
```

Check cache stats:
```bash
curl http://localhost:8000/api/cache/stats
```

### Error Recovery System
Monitor error recovery:
```bash
python core/error_recovery_monitor.py --monitor
```

Check error recovery stats:
```bash
curl http://localhost:8000/api/error-recovery/stats
```

Analyze error trends:
```bash
python core/error_recovery_monitor.py --trends
```

### Long-term Memory System
Check memory stats:
```bash
curl http://localhost:8000/api/memory/stats
```

Manually process a conversation for memory:
```bash
curl -X POST http://localhost:8000/api/memory/process/{conversation_id}
```

### Enhanced Thinking System
Check if thinking is enabled:
```bash
grep -A 5 "thinking.*enabled" core/app.py
```

The system uses Claude's enhanced thinking capabilities:
- **Internal reasoning**: Claude thinks through problems before responding
- **Better tool selection**: Enhanced reasoning about which tools to use
- **Improved quality**: All responses benefit from internal reasoning processes
- **Interleaved thinking**: Better tool orchestration and multi-step workflows

Note: Thinking content is processed internally for quality but not displayed due to LangChain limitations.

### DateTime Tools System
Check datetime tool usage:
```bash
grep "datetime" logs/api_calls.log
```

Monitor time-sensitive query handling:
```bash
tail -f logs/api_calls.log | grep "current date"
```

The system automatically handles time-sensitive queries:
- **Current date retrieval**: Automatically gets current date before time-sensitive searches
- **Context awareness**: Resolves relative time references ("next week", "recently")
- **Search accuracy**: Eliminates confusion from model knowledge cutoff
- **Automatic activation**: No user intervention needed for date-contextual queries

### Vector Database & Multimodal System
Check vector database status:
```bash
curl http://localhost:8000/api/vector-db/stats
```

Monitor vector database operations:
```bash
grep "vector DB" logs/api_calls.log
```

Test multimodal capabilities:
```bash
# Check if Pinecone is connected
python -c "from core.vector_db import vector_db; print(vector_db.get_stats())"
```

The system provides advanced vector database capabilities:
- **PostgreSQL Integration**: Cost-effective local vector database with pgvector
- **Pinecone Integration**: Cloud-based vector database for scalable similarity search
- **Multimodal Embeddings**: Unified text and image embeddings using OpenAI + CLIP
- **Long-term Memory**: Persistent storage of facts, preferences, and conversations
- **Visual Memory**: Store and search images with semantic descriptions
- **Auto-detection**: Automatically chooses best available database (PostgreSQL → Pinecone → Mock)

### Database Setup
Set up PostgreSQL vector database (optional but recommended):
```bash
# View setup instructions
cat database/README.md

# Run PostgreSQL setup
psql -U postgres -f database/setup_postgres.sql

# Set environment variable
export DATABASE_URL="postgresql://agentic_user:your_password@localhost:5432/agentic_vectors"
```

Alternative cloud setup with Pinecone:
```bash
export PINECONE_API_KEY="your-pinecone-api-key"
```

Without either, the system uses a mock database for development.

### Directory Structure
The codebase is organized into logical directories:
```bash
# Core application logic
ls core/

# Enhanced MCP implementation  
ls mcp/

# Database setup scripts
ls database/

# Tool implementations (used by MCP servers)
ls tools/

# Test infrastructure
ls test/
```

### MCP Development
Working with the Enhanced MCP architecture:
```bash
# Test MCP functionality
python -c "from mcp import get_enhanced_mcp_tools; print('MCP tools loaded successfully')"

# View server configuration
cat mcp/mcp_config.json

# Check individual MCP servers
ls mcp/mcp_servers/

# View MCP implementation details
cat mcp/MCP_IMPLEMENTATION.md
```

### Security Analysis
View Wikipedia tool security analysis:
```bash
cat WIKIPEDIA_SECURITY_ANALYSIS.md
```

Check tool security implementations:
```bash
grep -r "quote\|sanitize\|validate" tools/
```

### Logging System
View application logs:
```bash
tail -f logs/app.log
```

View error logs:
```bash
tail -f logs/error.log
```

View API call logs:
```bash
tail -f logs/api_calls.log
```

View WebSocket logs:
```bash
tail -f logs/websocket.log
```

## Architecture Overview

This is an agentic workflow system built with **FastAPI, LangGraph, and Anthropic Claude** that provides a chat interface with tool-enabled AI agents.

### Core Components

**main.py**: FastAPI application with WebSocket endpoints for real-time chat
- Manages conversation state and WebSocket connections
- Handles streaming responses from LangGraph
- Includes content filtering for problematic tool outputs (JSON-like responses)
- Serves static files and HTML templates
- Configured uvicorn to use centralized logging (disables default server.log creation)

**core/app.py**: LangGraph workflow configuration  
- Defines the agent state graph with `chatbot` and `tools` nodes
- Integrates Claude 3.7 Sonnet with tool binding and enhanced thinking
- Memory management with MemorySaver and InMemoryStore
- Tool routing logic in `should_continue()` function
- Configured with thinking enabled (budget: 1024 tokens, max: 2000 tokens)
- Interleaved thinking for improved tool use and reasoning

**tools/** directory: Modular tool implementations
- `secure_executor.py`: Secure Python execution with sandboxing
- `search_tools.py`: Tavily web search integration with caching
- `wiki_tools.py`: Wikipedia search functionality with caching
- `datetime_tools.py`: Current date/time retrieval for time-sensitive queries
- `multimodal_tools.py`: Vector database and multimodal memory operations
- `mcp_interface.py`: Model Context Protocol interface for future migration
- `secure_executor.py`: Sandboxed Python execution environment
- `prompt.py`: System prompt with detailed tool usage guidelines

**test/** directory: Comprehensive testing infrastructure
- `test_api_errors.py`: Automated tests for API error handling and stop reasons
- `TESTING_GUIDE.md`: Complete testing guide for manual and automated testing

**core/** directory: Core system components
- `app.py`: LangGraph workflow with error handling and retry logic
- `cache.py`: In-memory cache with TTL support for API results
- `error_recovery.py`: Advanced error recovery with circuit breaker pattern
- `logging_config.py`: Comprehensive logging with file rotation and categorization
- `cache_monitor.py`: Real-time cache monitoring and management utility
- `error_recovery_monitor.py`: Error recovery monitoring and trend analysis utility
- `long_term_memory.py`: OpenAI embeddings-based long-term memory store (legacy)
- `memory_agent.py`: Memory-enhanced agent with automatic memory extraction
- `vector_db.py`: Unified Pinecone vector database with multimodal capabilities

### Data Flow
1. User sends message via WebSocket to `/ws/{conversation_id}`
2. Message added to conversation history and passed to LangGraph
3. LangGraph routes through `chatbot` → `tools` (if needed) → `chatbot` cycle
4. Responses streamed back as chunks via WebSocket
5. Content filtered to prevent raw tool output display

### Environment Requirements
- `ANTHROPIC_API_KEY`: Required for Claude model access
- `TAVILY_API_KEY`: Required for web search functionality
- `OPENAI_API_KEY`: Required for long-term memory embeddings (optional)

### Key Design Patterns
- **Stateful conversations**: Each conversation has unique ID with persistent memory
- **Tool orchestration**: Agent can chain Wikipedia, web search, code execution, and datetime retrieval
- **Long-term memory**: Three types of memory using OpenAI embeddings for semantic search:
  - **Semantic memory**: Facts, preferences, skills, and domain knowledge
  - **Episodic memory**: Conversation summaries with context and outcomes
  - **Procedural memory**: Learned patterns and successful interaction sequences
- **Memory-enhanced responses**: Context from previous conversations informs current responses
- **Streaming responses**: Real-time message delivery via WebSocket chunks with intelligent sentence spacing
- **Intelligent caching**: API results cached with appropriate TTL (Wikipedia: 24h, Search: 30min)
- **Advanced error recovery**: Circuit breaker pattern with exponential backoff and jitter
- **Comprehensive error handling**: Anthropic API error classification with smart retry logic
- **Stop reason handling**: Proper handling of max_tokens, tool_use, and pause_turn scenarios
- **Markdown support**: Automatic parsing of headers, **bold**, *italic*, and clickable hyperlinks
- **Content sanitization**: Filters problematic tool outputs before user display
- **Error resilience**: Graceful handling of tool failures and WebSocket disconnections
- **Responsive UI**: REM-based CSS with proper text wrapping and containment
- **Smart formatting**: Scientific notation for large numbers, proper text spacing
- **Centralized logging**: All logs go to logs/ directory with automatic rotation and categorization
- **Tool-specific animations**: WebSocket events for tool start/end with named tool detection
- **Comprehensive testing**: Automated API error testing and manual testing guides
- **Security hardening**: URL encoding, input validation, and vulnerability assessments for all tools
- **Enhanced thinking**: Claude's internal reasoning enabled for improved response quality

### Performance Optimization
- **Cache hit rates**: Monitor with `/api/cache/stats` endpoint
- **API call reduction**: Cached results reduce external API calls by 60-80%
- **TTL strategy**: Different cache durations based on content stability
- **Memory management**: LRU eviction with configurable max size limits