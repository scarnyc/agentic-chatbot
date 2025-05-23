# AI by Design Agent

A powerful agentic workflow system built with FastAPI, LangGraph, and Anthropic Claude that provides an intelligent AI assistant capable of web search, Wikipedia queries, and secure code execution.

<img width="974" alt="Screenshot 2025-05-22 at 5 11 00 PM" src="https://github.com/user-attachments/assets/c9b766dc-5708-4473-88cc-19a6063fad74" />

## Features

🤖 **Advanced AI Chat Interface**
- Real-time streaming responses via WebSocket
- **Enhanced Thinking**: Claude's internal reasoning for improved response quality
- **Interleaved Thinking**: Better tool orchestration and multi-step workflows
- Intelligent text formatting with proper sentence spacing
- **Markdown support**: Automatic parsing of headers, **bold**, *italic*, and clickable hyperlinks
- Responsive design with REM-based CSS

🔧 **Multi-Tool Integration**
- **Web Search**: Tavily API integration for current information
- **Wikipedia Access**: Comprehensive knowledge base queries
- **Code Execution**: Secure Python environment with mathematical libraries
- **DateTime Tools**: Automatic current date retrieval for time-sensitive queries
- **Large Number Handling**: Stirling's approximation for factorial calculations
- **File Upload**: Support for images and PDFs with vision analysis
- **Vector Database**: PostgreSQL + pgvector for enhanced multimodal memory

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
- Persistent conversation memory

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
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

6. **Optional: PostgreSQL Vector Database Setup**
   For enhanced multimodal memory with vector embeddings:
   ```bash
   # Install PostgreSQL 16 with pgvector (macOS)
   brew install postgresql@16
   brew services start postgresql@16
   
   # Install pgvector extension
   git clone https://github.com/pgvector/pgvector.git
   cd pgvector
   make
   make install
   
   # Create database and user
   createdb agentic_vectors
   psql agentic_vectors -c "CREATE EXTENSION vector;"
   ```

7. **Open your browser**
   Navigate to `http://localhost:8000`

## File Cleanup

The `install_deps.py` file can be safely deleted - it was a temporary installation helper that is no longer needed.

## Architecture

### System Overview

This is an **agentic workflow system** built with FastAPI, LangGraph, and Anthropic Claude that provides intelligent tool orchestration with advanced error recovery and caching.

### Core Components

```
agentic-workflow/
├── main.py                       # FastAPI server with WebSocket endpoints
├── core/                         # Core system components
│   ├── app.py                   # LangGraph workflow configuration
│   ├── cache.py                 # In-memory cache with TTL support
│   ├── error_recovery.py        # Circuit breaker pattern & error handling
│   ├── logging_config.py        # Comprehensive logging system
│   ├── cache_monitor.py         # Real-time cache monitoring utility
│   ├── error_recovery_monitor.py # Error recovery monitoring & trends
│   ├── long_term_memory.py      # OpenAI embeddings-based memory store
│   └── memory_agent.py          # Memory-enhanced agent with extraction
├── tools/                        # Modular tool implementations
│   ├── code_tools.py            # Python execution with security
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

### Data Flow

1. **User Input** → WebSocket connection established
2. **Memory Retrieval** → Semantic search for relevant context
3. **Message Processing** → LangGraph workflow orchestration with memory context
4. **Tool Execution** → Wikipedia, web search, or code execution
5. **Response Streaming** → Real-time chunks via WebSocket
6. **Content Filtering** → Intelligent formatting and validation
7. **Memory Extraction** → Automatic memory processing on conversation end
8. **UI Display** → Responsive message bubbles with proper spacing

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

## Tool Capabilities

### 🌐 Web Search (Tavily)
- Current events and news
- Real-time information
- Market data and trends
- Product information

**Example:** *"What are the latest developments in AI?"*

### 📚 Wikipedia Integration
- Historical information
- Biographical data
- Scientific concepts
- General knowledge
- **Security**: URL encoding, input validation, query sanitization

**Example:** *"Tell me about the Roman Empire"*

### 🐍 Code Execution
- Mathematical calculations
- Data analysis
- Algorithm implementation
- Scientific computing with mpmath

**Example:** *"Calculate the factorial of 100"*

### ⏰ DateTime Context Tools
- Automatic current date retrieval for time-sensitive queries
- Resolves relative time references ("this week", "next week", "recently")
- Eliminates confusion from model knowledge cutoff
- Contextualizes search queries with accurate timeframes

**Example:** *"What's the weather next week in Miami?"* automatically gets current date, calculates "next week", then searches with proper date context.

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
3. Add to `tools/code_tools.py` or create new category
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
- Log-in screen with Google oAuth for sign-in
- MCP Servers
- Vision, PDF support
- Canvas
  
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

---

**Built with ❤️ for intelligent automation**

For support or questions, please open an issue on GitHub.
