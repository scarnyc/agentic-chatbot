# Testing Guide: API Error Handling & Stop Reasons

This guide explains how to test the Anthropic API error handling and stop reason functionality.

## Quick Start

Run the automated test script:
```bash
python test_api_errors.py
```

## Testing Error Handling

### 1. Automated Testing
The test script simulates all error conditions without making real API calls:

```bash
python test_api_errors.py
```

This tests:
- ✅ Error message generation for all HTTP status codes
- ✅ Retry logic for different error types
- ✅ Stop reason handling for all scenarios
- ✅ Integration with mocked API responses

### 2. Real API Error Testing

#### Test 401 (Authentication Error)
```bash
# Temporarily set invalid API key
export ANTHROPIC_API_KEY="invalid_key"
python main.py
# Try sending a message - should show authentication error
```

#### Test 413 (Request Too Large)
Send an extremely long message (>100,000 characters) through the web interface.

#### Test 429 (Rate Limiting)
Create a script to make rapid API calls:
```python
import asyncio
import aiohttp

async def spam_requests():
    for i in range(50):
        # Send rapid requests to trigger rate limiting
        # Use your app's WebSocket endpoint
        pass
```

#### Test 529 (Overloaded)
This is harder to trigger but may occur during high API usage periods.

## Testing Stop Reasons

### 1. Test max_tokens (Truncation)

#### Method 1: Lower the token limit
In `core/app.py`, temporarily change:
```python
llm = ChatAnthropic(
    model_name="claude-sonnet-4-20250514",
    max_tokens=50,  # Very low limit
    # ...
)
```

Then ask: "Write a detailed 1000-word essay about artificial intelligence"

#### Method 2: Very long prompt
Send a message with a very long context that approaches the model's limits.

### 2. Test tool_use
Ask the AI to search for something:
```
"Search Wikipedia for information about quantum computing"
```

The stop reason should be `tool_use` when Claude wants to call the Wikipedia tool.

### 3. Test end_turn (Normal)
Ask any regular question:
```
"What is 2+2?"
```

This should result in `end_turn` stop reason.

### 4. Test stop_sequence (Custom)
Currently not implemented in the UI, but you can modify `core/app.py` to add stop sequences:
```python
llm = ChatAnthropic(
    # ...
    stop_sequences=["STOP", "END"]
)
```

## Manual Testing Checklist

### Error Handling ✅
- [ ] Invalid API key shows user-friendly message
- [ ] Long requests show "request too large" error
- [ ] Rate limiting shows appropriate retry message
- [ ] Server errors are handled gracefully
- [ ] Network timeouts are handled

### Stop Reasons ✅
- [ ] Normal responses complete without warnings
- [ ] Long responses show truncation warning
- [ ] Tool calls work seamlessly
- [ ] All stop reasons are logged correctly

### User Experience ✅
- [ ] No raw error codes shown to users
- [ ] Clear, actionable error messages
- [ ] Automatic retries work transparently
- [ ] Truncation warnings are helpful

## Debugging & Monitoring

### Log Analysis
Check server logs for:
```bash
# Error handling
grep "Anthropic API error" logs/app.log

# Stop reasons
grep "Anthropic stop reason" logs/app.log

# Request IDs for support
grep "request ID" logs/app.log
```

### Browser DevTools
1. Open browser DevTools (F12)
2. Go to Network tab
3. Send messages and monitor WebSocket traffic
4. Look for error responses in the messages

### Server Logs
Monitor the FastAPI server output for:
- Error handling messages
- Stop reason logging
- Retry attempts
- Request ID tracking

## Expected Behaviors

### ✅ Success Cases
- Normal conversations work seamlessly
- Tool calls execute properly
- Retries happen automatically for transient errors
- Users see helpful messages for permanent errors

### ⚠️ Error Cases
- Authentication errors: Clear message about API key
- Rate limits: "Please wait and try again" message
- Truncation: Warning appended to response
- Server errors: Automatic retry, then error message

## Troubleshooting

### Common Issues
1. **Tests fail with import errors**: Ensure you're in the project directory
2. **Real API tests don't trigger errors**: Errors are rare; use mocked tests instead
3. **Logs don't show stop reasons**: Check log level is set to INFO or DEBUG

### Advanced Testing
For more comprehensive testing, consider:
- Load testing with multiple concurrent users
- Network interruption simulation
- Memory usage monitoring during retries
- Integration testing with all tools enabled

## Production Monitoring

In production, monitor:
- Error rate trends
- Retry success rates
- Stop reason distribution
- Request ID patterns for support correlation