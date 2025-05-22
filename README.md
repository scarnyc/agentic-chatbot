# AI by Design Copilot

A powerful agentic workflow system built with FastAPI, LangGraph, and Anthropic Claude that provides an intelligent AI assistant capable of web search, Wikipedia queries, and secure code execution.

## Features

🤖 **Advanced AI Chat Interface**
- Real-time streaming responses via WebSocket
- Intelligent text formatting with proper sentence spacing
- Responsive design with REM-based CSS

🔧 **Multi-Tool Integration**
- **Web Search**: Tavily API integration for current information
- **Wikipedia Access**: Comprehensive knowledge base queries
- **Code Execution**: Secure Python environment with mathematical libraries
- **Large Number Handling**: Stirling's approximation for factorial calculations

🛡️ **Smart Content Filtering**
- Prevents raw tool output from displaying to users
- Filters out "[object Object]" and JSON-like responses
- Conservative validation to maintain response quality

💻 **Modern Architecture**
- FastAPI backend with WebSocket support
- LangGraph for workflow orchestration
- Anthropic Claude 3.7 Sonnet with thinking capabilities
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

3. **Set up environment variables**
   Create a `.env` file in the project root:
   ```env
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   TAVILY_API_KEY=your_tavily_api_key_here
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

5. **Open your browser**
   Navigate to `http://localhost:8000`

## Architecture

### Core Components

```
agentic-workflow/
├── main.py                 # FastAPI server with WebSocket endpoints
├── core/
│   └── app.py             # LangGraph workflow configuration
├── tools/                 # Modular tool implementations
│   ├── code_tools.py      # Python execution with security
│   ├── search_tools.py    # Tavily web search integration
│   ├── wiki_tools.py      # Wikipedia API wrapper
│   ├── math_tools.py      # Mathematical calculations
│   └── prompt.py          # System prompts and guidelines
├── static/                # Frontend assets
│   ├── css/styles.css     # Responsive styling
│   └── js/app.js          # WebSocket client logic
└── templates/
    └── index.html         # Main chat interface
```

### Data Flow

1. **User Input** → WebSocket connection established
2. **Message Processing** → LangGraph workflow orchestration
3. **Tool Execution** → Wikipedia, web search, or code execution
4. **Response Streaming** → Real-time chunks via WebSocket
5. **Content Filtering** → Intelligent formatting and validation
6. **UI Display** → Responsive message bubbles with proper spacing

## API Endpoints

### REST Endpoints

- `GET /` - Main chat interface
- `POST /api/conversations` - Create new conversation

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

**Example:** *"Tell me about the Roman Empire"*

### 🐍 Code Execution
- Mathematical calculations
- Data analysis
- Algorithm implementation
- Scientific computing with mpmath

**Example:** *"Calculate the factorial of 100"*

### 🔢 Advanced Mathematics
- Stirling's approximation for large factorials
- Scientific notation formatting
- High-precision calculations
- Memory-efficient algorithms

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | Yes |
| `TAVILY_API_KEY` | Tavily search API key | Yes |

### Model Configuration

The system uses **Claude 3.7 Sonnet** with:
- **Max tokens**: 1,500
- **Thinking enabled**: 1,024 token budget
- **Tool binding**: All available tools
- **Memory**: Persistent conversation history

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

## Troubleshooting

### Common Issues

**Server won't start:**
```bash
# Check port availability
lsof -i :8000

# Kill existing processes
lsof -ti:8000 | xargs kill -9
```

**API key errors:**
- Verify `.env` file exists and contains valid keys
- Check API key permissions and quotas
- Ensure no extra spaces in environment variables

**WebSocket connection issues:**
- Check browser console for errors
- Verify conversation ID exists
- Clear browser cache and cookies

**Tool execution failures:**
- Check Python environment and dependencies
- Verify network connectivity for external APIs
- Review server logs for detailed error messages

### Debugging

Enable debug logging:
```python
# In main.py
logging.basicConfig(level=logging.DEBUG)
```

Monitor server logs:
```bash
tail -f server.log
```

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

---

**Built with ❤️ for intelligent automation**

For support or questions, please open an issue on GitHub.