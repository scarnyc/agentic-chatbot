# AI by Design Agent

A powerful agentic workflow system built with FastAPI, LangGraph, and Anthropic Claude that provides an intelligent AI assistant capable of web search, Wikipedia queries, and secure code execution.

![0601](https://github.com/user-attachments/assets/08078e66-6672-46ca-99fa-d986cc3d5a26)

## Features

🤖 **Advanced AI Chat Interface**
- Real-time streaming responses via WebSocket
- **Enhanced Thinking**: Claude's internal reasoning for improved response quality
- **Interleaved Thinking**: Better tool orchestration and multi-step workflows
- Intelligent text formatting with proper sentence spacing
- **Markdown support**: Automatic parsing of headers, **bold**, *italic*, and clickable hyperlinks
- Responsive design with REM-based CSS

🔧 **Multi-Tool Integration via Enhanced MCP**
- **Web Search**: Tavily API integration for current information
- **Wikipedia Access**: Comprehensive knowledge base queries
- **Code Execution**: Secure Python environment with mathematical libraries
- **DateTime Tools**: Automatic current date retrieval for time-sensitive queries
- **Large Number Handling**: Stirling's approximation for factorial calculations
- **File Upload**: Support for images and PDFs with vision analysis
- **Vector Database**: PostgreSQL + pgvector for enhanced multimodal memory
- **MCP Architecture**: Model Context Protocol with multiple server sessions

🛡️ **Smart Content Filtering**
- Prevents raw tool output from displaying to users
- Filters out "[object Object]" and JSON-like responses
- Conservative validation to maintain response quality

🔄 **Advanced Error Recovery**
- Circuit breaker pattern with exponential backoff
- Intelligent retry logic for API failures
- Real-time error recovery monitoring
- Automatic failure trend analysis

📊 **Intelligent Caching System**
- In-memory cache with TTL support
- API call reduction (60-80% efficiency)
- Real-time cache performance monitoring
- Automatic LRU eviction

🧠 **Long-term Agentic Memory**
- **Semantic Memory**: Facts, preferences, skills, and domain knowledge
- **Episodic Memory**: Conversation summaries with context and outcomes
- **Procedural Memory**: Learned patterns and successful interaction sequences
- **OpenAI Embeddings**: Semantic search for memory retrieval
- **Persistent Storage**: Local JSON-based memory with automatic pruning

🔍 **Comprehensive Monitoring**
- Real-time system health dashboard
- Cache hit rate and performance metrics
- Error recovery statistics and trends
- Detailed logging with automatic rotation

💻 **Modern Architecture**
- FastAPI backend with WebSocket support
- LangGraph for workflow orchestration
- Anthropic Claude 4 Sonnet with enhanced thinking capabilities
- **Enhanced MCP**: Multiple server sessions with tool-to-session mapping
- Persistent conversation memory with vector embeddings

## Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key
- Tavily API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/scarnyc/agentic-workflow.git
   cd agentic-workflow
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install multimodal dependencies (optional)**
   For enhanced image embeddings with CLIP:
   ```bash
   pip install torch torchvision transformers
   ```
   *Note: System works with text-only embeddings if these are not installed.*

4. **Set up environment variables**
   Create a `.env` file in the project root:
   ```env
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   TAVILY_API_KEY=your_tavily_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here  # Optional: For long-term memory
   DATABASE_URL=postgresql://username:password@localhost:5432/agentic_vectors  # Optional: For PostgreSQL vector storage
   PINECONE_API_KEY=your_pinecone_api_key_here  # Alternative: For cloud vector storage
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

6. **Optional: Vector Database Setup**
   Choose one of the following for enhanced multimodal memory:
   
   **Option A: PostgreSQL (Recommended - Cost-effective)**
   ```bash
   # Follow detailed setup instructions
   cat database/README.md
   
   # Quick setup
   psql -U postgres -f database/setup_postgres.sql
   ```
   
   **Option B: Pinecone (Cloud)**
   ```bash
   # Just set your API key in .env
   PINECONE_API_KEY=your_pinecone_api_key_here
   ```
   
   **Option C: Mock Database (Default)**
   No setup required - automatically used if neither above is configured.

7. **Open your browser**
   Navigate to `http://localhost:8000`

## Architecture

### System Overview

This is an **agentic workflow system** built with FastAPI, LangGraph, and Anthropic Claude that provides intelligent tool orchestration via **Enhanced MCP (Model Context Protocol)** with advanced error recovery and caching.

### Core Components

```
agentic-workflow/
├── main.py                       # FastAPI server with WebSocket endpoints
├── core/                         # Core system components
│   ├── app.py                   # LangGraph workflow with MCP integration
│   ├── cache.py                 # In-memory cache with TTL support
│   ├── error_recovery.py        # Circuit breaker pattern & error handling
│   ├── logging_config.py        # Comprehensive logging system
│   ├── cache_monitor.py         # Real-time cache monitoring utility
│   ├── error_recovery_monitor.py # Error recovery monitoring & trends
│   ├── long_term_memory.py      # OpenAI embeddings-based memory store
│   ├── memory_agent.py          # Memory-enhanced agent with extraction
│   ├── postgres_vector_db.py    # PostgreSQL vector database implementation
│   ├── vector_db_factory.py     # Auto-detection of available databases
│   └── mock_vector_db.py        # Fallback mock database
├── mcp/                          # Enhanced MCP implementation
│   ├── enhanced_mcp_tools.py    # Multi-server MCP client with session management
│   ├── mcp_config.json          # Server configuration and tool mapping
│   ├── mcp_servers/             # Individual MCP server implementations
│   │   ├── code_server.py       # Python execution & mathematical tools
│   │   ├── search_server.py     # Tavily web search capabilities
│   │   ├── wiki_server.py       # Wikipedia search functionality
│   │   ├── datetime_server.py   # Time-sensitive date/time tools
│   │   └── multimodal_server.py # Vector database & multimodal operations
│   └── MCP_IMPLEMENTATION.md    # Detailed MCP architecture documentation
├── database/                     # Database setup and migrations
│   ├── setup_postgres.sql       # PostgreSQL + pgvector setup script
│   └── README.md                # Database setup instructions
├── tools/                        # Tool implementations (used by MCP servers)
│   ├── secure_executor.py       # Secure Python execution with sandboxing
│   ├── search_tools.py          # Tavily web search integration
│   ├── wiki_tools.py            # Wikipedia API wrapper
│   ├── datetime_tools.py        # Current date/time for context
│   ├── math_tools.py            # Mathematical calculations
│   ├── secure_executor.py       # Sandboxed execution environment
│   └── prompt.py                # System prompts and guidelines
├── test/                         # Testing infrastructure
│   ├── test_api_errors.py       # Automated API error testing
│   └── TESTING_GUIDE.md         # Comprehensive testing guide
├── static/                       # Frontend assets
│   ├── css/styles.css           # Responsive styling
│   └── js/app.js                # WebSocket client logic
├── templates/
│   └── index.html               # Main chat interface
├── logs/                         # Application logs (auto-created)
│   ├── app.log                  # General application logs
│   ├── error.log                # Error-level logs
│   ├── cache.log                # Cache operations
│   ├── error_recovery.log       # Error recovery events
│   ├── websocket.log            # WebSocket connections
│   └── api_calls.log            # API tool usage
└── memory/                       # Long-term memory storage (auto-created)
    ├── semantic_memories.json   # Facts, preferences, skills
    ├── episodic_memories.json   # Conversation summaries  
    └── procedural_memories.json # Learned patterns
```

### Enhanced MCP Architecture

The system uses **Model Context Protocol (MCP)** with multiple server sessions for robust tool orchestration:

#### **Key MCP Features:**
- **Multiple Client Sessions**: Each tool category runs in its own MCP server process
- **Tool-to-Session Mapping**: Efficient routing of tool calls to appropriate servers  
- **Resource Management**: Proper cleanup with ExitStack context manager
- **Modular Design**: Easy to extend with new servers and tools

#### **MCP Servers:**
- **code-server**: Python execution and mathematical computations
- **search-server**: Web search via Tavily API with caching
- **wiki-server**: Wikipedia search with intelligent content processing
- **datetime-server**: Current date/time for time-sensitive queries  
- **multimodal-server**: Vector database operations and multimodal memory

#### **Benefits:**
- **Scalability**: Each server runs independently, no single point of failure
- **Maintainability**: Clear separation of concerns between tool categories
- **Performance**: Direct tool-to-session mapping for fast routing
- **Future-Ready**: Prepared for remote MCP server deployment

### Data Flow

1. **User Input** → WebSocket connection established
2. **Memory Retrieval** → Semantic search for relevant context from vector database
3. **Message Processing** → LangGraph workflow orchestration with memory context
4. **MCP Tool Routing** → Tool calls routed to appropriate MCP server sessions
5. **Tool Execution** → Parallel execution across specialized MCP servers
6. **Response Streaming** → Real-time chunks via WebSocket
7. **Content Filtering** → Intelligent formatting and validation
8. **Memory Extraction** → Automatic memory processing and vector storage
9. **UI Display** → Responsive message bubbles with proper spacing

## API Endpoints

### REST Endpoints

- `GET /` - Main chat interface
- `POST /api/conversations` - Create new conversation
- `GET /api/health` - System health check with cache and error recovery stats
- `GET /api/cache/stats` - Cache performance statistics
- `POST /api/cache/clear` - Clear all cache entries
- `GET /api/error-recovery/stats` - Error recovery and circuit breaker status
- `GET /api/memory/stats` - Long-term memory statistics
- `POST /api/memory/process/{conversation_id}` - Process conversation for memory extraction

### WebSocket Endpoints

- `WS /ws/{conversation_id}` - Real-time chat communication

### Message Format

**Client to Server:**
```json
{
  "type": "message",
  "content": "What's the weather today?",
  "id": "message-123"
}
```

**Server to Client:**
```json
{
  "type": "message_chunk",
  "content": "The weather today is..."
}
```

## Tool Capabilities via Enhanced MCP

All tools are accessed through the **Enhanced MCP (Model Context Protocol)** architecture, providing robust session management and efficient routing.

### 🌐 Web Search (Tavily) - `search-server`
- Current events and news
- Real-time information
- Market data and trends
- Product information
- **Caching**: 30-minute TTL for search results
- **Processing**: Token-optimized result formatting

**Example:** *"What are the latest developments in AI?"*

### 📚 Wikipedia Integration - `wiki-server`
- Historical information
- Biographical data
- Scientific concepts
- General knowledge
- **Security**: URL encoding, input validation, query sanitization
- **Caching**: 24-hour TTL for stable content

**Example:** *"Tell me about the Roman Empire"*

### 🐍 Code Execution - `code-server`
- Mathematical calculations
- Data analysis
- Algorithm implementation
- Scientific computing with mpmath
- **Security**: Sandboxed execution environment
- **Features**: Stirling approximation for large factorials

**Example:** *"Calculate the factorial of 100"*

### ⏰ DateTime Context Tools - `datetime-server`
- Automatic current date retrieval for time-sensitive queries
- Resolves relative time references ("this week", "next week", "recently")
- Eliminates confusion from model knowledge cutoff
- Contextualizes search queries with accurate timeframes
- **Tools**: Current datetime, simple date format for search context

**Example:** *"What's the weather next week in Miami?"* automatically gets current date, calculates "next week", then searches with proper date context.

### 🎯 Multimodal Operations - `multimodal-server`
- Vector database operations (PostgreSQL/Pinecone/Mock)
- Text and image memory storage
- Semantic similarity search
- Database auto-detection and health monitoring
- **Features**: Store/search text, store/analyze images, database info

**Example:** Store important facts, search previous conversations, analyze uploaded images

### 🧠 Long-term Memory System

The agent employs a sophisticated three-tier memory system using OpenAI embeddings for semantic search and retrieval:

#### Memory Types

**📝 Semantic Memory**
- Stores factual knowledge, user preferences, and skills
- Automatically extracts information from user statements
- Categories: facts, preferences, skills, domain knowledge
- Example: "I prefer Python programming" → stored as preference

**📚 Episodic Memory** 
- Records conversation summaries with context
- Tracks tools used, outcomes, and emotional context
- Importance scoring for memory retention
- Example: "User asked about data science, used search tool, successful outcome"

**⚙️ Procedural Memory**
- Learns successful interaction patterns
- Stores trigger conditions → action sequences
- Success rate tracking and pattern optimization
- Example: "Code request → analyze requirements → generate code → explain"

#### Memory Storage

```
📁 memory/
├── semantic_memories.json    # Facts, preferences, skills
├── episodic_memories.json    # Conversation summaries  
└── procedural_memories.json  # Learned patterns
```

Each memory includes:
- **Content**: The actual memory information
- **Embedding**: 1536-dimensional OpenAI vector for semantic search
- **Metadata**: Confidence scores, timestamps, usage counts
- **Context**: Category, source, importance scores

#### Memory Integration

1. **Context Retrieval**: Every user message triggers semantic search
2. **Enhanced Prompts**: Relevant memories automatically added to system prompts
3. **Automatic Extraction**: Conversations processed for memory on disconnect
4. **Smart Pruning**: LRU-based memory management with configurable limits

### 🔢 Advanced Mathematics
- Stirling's approximation for large factorials
- Scientific notation formatting
- High-precision calculations
- Memory-efficient algorithms

### 📝 Rich Text Formatting
- **Headers**: `# Title`, `## Subtitle`, `### Section` (supports H1-H6)
- **Bold text**: `**text**` renders as **bold**
- **Italic text**: `*text*` renders as *italic*
- **Clickable links**: Automatic URL detection and formatting
- **Smart parsing**: Real-time markdown processing during streaming
- **Custom styling**: Light blue links and purple headers optimized for dark theme

### 🧠 Enhanced Thinking System
- **Internal Reasoning**: Claude processes complex problems with enhanced thinking
- **Better Tool Selection**: Improved reasoning about which tools to use  
- **Quality Improvements**: All responses benefit from internal reasoning processes
- **Interleaved Thinking**: Enhanced tool orchestration for multi-step workflows
- **Note**: Thinking content processed internally but not displayed due to LangChain limitations

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | Yes |
| `TAVILY_API_KEY` | Tavily search API key | Yes |
| `OPENAI_API_KEY` | OpenAI API key for embeddings | No* |

*Required for long-term memory functionality

### Model Configuration

The system uses **Claude 4 Sonnet** with:
- **Max tokens**: 2,000
- **Enhanced thinking**: 1,024 token budget for internal reasoning
- **Interleaved thinking**: Beta feature for better tool orchestration
- **Tool binding**: All available tools
- **Memory**: Persistent conversation history

## Monitoring & Operations

### System Health Monitoring

```bash
# Real-time cache monitoring
python core/cache_monitor.py --monitor

# Error recovery monitoring
python core/error_recovery_monitor.py --monitor

# System health check
python core/cache_monitor.py --health
python core/error_recovery_monitor.py --health

# Analyze error trends
python core/error_recovery_monitor.py --trends
```

### Cache Management

```bash
# View cache statistics
python core/cache_monitor.py
curl http://localhost:8000/api/cache/stats

# Clear cache
python core/cache_monitor.py --clear
curl -X POST http://localhost:8000/api/cache/clear

# Run cache benchmark
python core/cache_monitor.py --benchmark
```

### Long-term Memory Management

```bash
# View memory statistics
curl http://localhost:8000/api/memory/stats

# Process conversation for memory extraction
curl -X POST http://localhost:8000/api/memory/process/{conversation_id}

# Test memory system
python test_memory.py

# Memory storage location
ls -la memory/
```

### Testing

```bash
# Run automated API error tests
python test_api_errors.py

# Test memory system
python test_memory.py

# Test extended thinking functionality
python test_thinking.py

# View comprehensive testing guide
cat TESTING_GUIDE.md
```

### DateTime Tools Monitoring

```bash
# Monitor datetime tool usage
grep "datetime" logs/api_calls.log

# Watch time-sensitive query handling in real-time
tail -f logs/api_calls.log | grep "current date"

# Check for time-context searches
grep "Retrieved.*date" logs/api_calls.log
```

### Security Analysis

```bash
# View Wikipedia tool security analysis
cat WIKIPEDIA_SECURITY_ANALYSIS.md

# Check tool security implementations
grep -r "quote\|sanitize\|validate" tools/
```

## Development

### Enhanced MCP Development

#### **Working with MCP Servers:**

```bash
# Test MCP client functionality
python -c "from mcp import get_enhanced_mcp_tools; tools = get_enhanced_mcp_tools(); print(f'Loaded {len(tools)} tools')"

# View MCP configuration
cat mcp/mcp_config.json

# View detailed MCP documentation
cat mcp/MCP_IMPLEMENTATION.md

# Test individual MCP server
python mcp/mcp_servers/datetime_server.py
```

#### **Adding New MCP Servers:**

1. **Create server file** in `mcp/mcp_servers/new_server.py`
2. **Update configuration** in `mcp/mcp_config.json`
3. **Add tool definitions** in `mcp/enhanced_mcp_tools.py`
4. **Test integration** with the main app

#### **MCP Server Structure:**
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Your Server Name")

@mcp.tool()
def your_tool(param: str) -> str:
    """Tool description"""
    return f"Result: {param}"

if __name__ == "__main__":
    mcp.run()
```

#### **Vector Database Development:**

```bash
# Test PostgreSQL setup
python -c "from core.vector_db_factory import VectorDBFactory; db = VectorDBFactory.create_vector_db(); print(db.get_stats())"

# View database setup instructions
cat database/README.md

# Check which database is being used
python -c "from core.vector_db_factory import VectorDBFactory; print(VectorDBFactory.get_available_databases())"
```

### Code Quality

```bash
# Format code
black .

# Run tests
pytest

# Type checking (if configured)
mypy .
```

### Adding New Tools

1. Create a new tool file in `tools/`
2. Implement the tool function
3. Add to `tools/secure_executor.py` or create new category
4. Update `core/app.py` to include the tool
5. Add usage guidelines to `tools/prompt.py`

### Frontend Customization

The UI uses CSS custom properties for easy theming:

```css
:root {
    --bg-dark: #18191a;
    --bg-message: #292a2d;
    --accent: #7c4dff;
    --text-light: #e4e6eb;
}
```

## Security Features

### Code Execution Safety
- Sandboxed Python environment
- Temporary file cleanup
- Resource limitations
- Error handling and logging

### Content Validation
- Input sanitization
- Output filtering
- Raw data detection
- Malicious content prevention

### Network Security
- CORS configuration
- WebSocket authentication
- API key protection
- Rate limiting (Anthropic-enforced)

### Tool Security
- **Wikipedia Tool**: URL encoding, input validation, query length limiting
- **Search Tool**: API key protection, result filtering
- **Code Tool**: Sandboxed execution, no file system access
- **Security Auditing**: Regular vulnerability assessments of LangChain community tools

## Performance Optimizations

### Streaming Response
- **Chunked delivery**: Real-time message streaming
- **Intelligent spacing**: Sentence boundary detection
- **Content filtering**: Prevents UI blocking on raw data
- **Auto-scrolling**: Smooth user experience

### Memory Management
- **Conversation persistence**: In-memory storage with cleanup
- **Tool result caching**: Reduced API calls
- **Connection pooling**: Efficient WebSocket handling

### Mathematical Performance
- **Stirling's approximation**: For large factorial calculations
- **Scientific notation**: Prevents UI overflow
- **Precision control**: Balanced accuracy and performance

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add docstrings to all functions
- Include type hints where appropriate
- Write tests for new functionality
- Update documentation for API changes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Anthropic** for Claude API and advanced reasoning capabilities
- **LangChain** for framework and tool integration
- **Tavily** for web search functionality
- **FastAPI** for modern web framework
- **Community** for inspiration and feedback

## Architecture Diagram

```
User Query
    │
    ▼
┌───────────────┐
│ Agent         │
│ (Claude 4)    │
└───────────────┘
    │
    ├─────────────────┬─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│Tavily Search│  │Python REPL  │  │Wikipedia API│
└─────────────┘  └─────────────┘  └─────────────┘

```
## Roadmap

### v0 ✅ 
- Comprehensive error handling
- Handling stop reasons
- Caching Results: Add a simple cache for commonly requested information to reduce API calls
- Progressive Enhancement: In the frontend, show typing indicators during tool transitions for a more natural feel
- Error Recovery: Implement automatic retries for temporary API failures
  
### v1 ✅
- Long-term Agentic Memory (Semantic, Episodic, Procedural)
- OpenAI Embeddings for semantic search
- Automatic memory extraction and retrieval

### v1.1
- Vision, PDF support ✅
- Canvas
- Log-in screen with Google oAuth for sign-in
- MCP Servers
  
### v2
- File System
- Human in the loop (stop and ask for input)
- Evals (https://docs.anthropic.com/en/docs/test-and-evaluate/strengthen-guardrails/reduce-hallucinations)
- RL fine-tuning with GRPO w/ thumbs up and thumbs down user feedback
- Support for GPT 4.1 for writing (Tool Call)
- Persist user Chat history (UI)


### v3
- Planning: research, generation, reflection
- RAG, Deep Research w/ Perplexity
- Upgraded web search with Google SerpAPI
- Enable Claude's Built-in Web Search w/ Prompt Caching 
- Claude's Code Exec / Prompt Gen / Computer Use (Beta)
- Experiment with thinking budget

### V4
- Slack, LinkedIn, gmail, Nasa toolkit, Substack
- User-input OpenAI / Anthropic API Key
- Security with Cloudflare
- App optimized for security, speed & efficiency
- Generative UI
- User Feedback Loop: Add a thumbs up/down mechanism to collect feedback on answers
- chatterbox.ai voice integration

---

**Built with ❤️ for intelligent automation**

For support or questions, please open an issue on GitHub.
