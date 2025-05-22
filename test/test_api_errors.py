#!/usr/bin/env python3
"""
Test script for Anthropic API error handling and stop reasons.
This script simulates various error conditions to test the error handling implementation.
"""

import os
import sys
import time
import asyncio
import json
from unittest.mock import Mock, patch
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.app import AnthropicAPIErrorHandler, AnthropicStopReasonHandler, call_model
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

class MockAnthropicError:
    """Mock Anthropic API error for testing."""
    def __init__(self, status_code, message="Mock error"):
        self.status_code = status_code
        self.message = message
        self.response = Mock()
        self.response.headers = {'request-id': f'mock-request-{status_code}'}
    
    def __str__(self):
        return self.message

class MockResponse:
    """Mock Anthropic API response for testing stop reasons."""
    def __init__(self, content, stop_reason="end_turn", request_id="mock-request-123"):
        self.content = content
        self.response_metadata = {
            'stop_reason': stop_reason,
            'request-id': request_id
        }
        self.additional_kwargs = {}

def test_error_handling():
    """Test error handling for various HTTP status codes."""
    print("=== Testing API Error Handling ===\n")
    
    error_handler = AnthropicAPIErrorHandler()
    
    # Test different error codes
    test_cases = [
        (400, "Bad Request"),
        (401, "Unauthorized"),
        (403, "Forbidden"),
        (404, "Not Found"),
        (413, "Request Too Large"),
        (429, "Rate Limited"),
        (500, "Internal Server Error"),
        (529, "Overloaded"),
    ]
    
    for status_code, description in test_cases:
        print(f"Testing {status_code} ({description}):")
        
        # Create mock error
        mock_error = MockAnthropicError(status_code)
        
        # Test error message generation
        error_msg = error_handler.get_error_message(mock_error)
        print(f"  Error Message: {error_msg}")
        
        # Test retry logic
        should_retry = error_handler.should_retry(mock_error)
        print(f"  Should Retry: {should_retry}")
        
        if should_retry:
            delay = error_handler.get_retry_delay(1, mock_error)
            print(f"  Retry Delay: {delay}s")
        
        print()

def test_stop_reasons():
    """Test stop reason handling."""
    print("=== Testing Stop Reason Handling ===\n")
    
    stop_handler = AnthropicStopReasonHandler()
    
    # Test different stop reasons
    test_cases = [
        ("end_turn", "This is a complete response."),
        ("max_tokens", "This response was truncated because it exceeded"),
        ("stop_sequence", "This response stopped at a custom sequence."),
        ("tool_use", "I need to use a tool for this."),
        ("pause_turn", "This is a paused response."),
    ]
    
    for stop_reason, content in test_cases:
        print(f"Testing stop_reason: {stop_reason}")
        
        # Create mock response
        mock_response = MockResponse(content, stop_reason)
        
        # Test stop reason handling
        stop_info = stop_handler.handle_stop_reason(mock_response)
        
        print(f"  Content: {content}")
        print(f"  Should Warn User: {stop_info['should_warn_user']}")
        if stop_info['warning_message']:
            print(f"  Warning: {stop_info['warning_message']}")
        print(f"  Should Continue: {stop_info['should_continue']}")
        if stop_info['modified_content']:
            print(f"  Modified Content: {stop_info['modified_content']}")
        print()

def test_max_tokens_simulation():
    """Simulate a max_tokens response to test truncation warning."""
    print("=== Testing Max Tokens Simulation ===\n")
    
    # Create a response that simulates max_tokens
    long_content = "This is a very long response that would normally continue but gets cut off due to token limits"
    
    mock_response = MockResponse(long_content, "max_tokens")
    stop_handler = AnthropicStopReasonHandler()
    stop_info = stop_handler.handle_stop_reason(mock_response)
    
    print("Original content:")
    print(f"  {long_content}")
    print("\nModified content with warning:")
    print(f"  {stop_info['modified_content']}")

async def test_integration_with_mock():
    """Test integration with mocked API calls."""
    print("=== Testing Integration with Mock API ===\n")
    
    # Mock the model chain to simulate different scenarios
    test_scenarios = [
        ("Normal response", "end_turn", "This is a normal response."),
        ("Truncated response", "max_tokens", "This response was truncated"),
        ("API Error", "error", None),  # Will raise an exception
    ]
    
    for scenario_name, stop_reason, content in test_scenarios:
        print(f"Testing: {scenario_name}")
        
        try:
            if stop_reason == "error":
                # Simulate API error
                with patch('core.app.model_chain') as mock_chain:
                    mock_chain.invoke.side_effect = MockAnthropicError(429, "Rate limit exceeded")
                    
                    # Create mock state
                    mock_state = {
                        "messages": [HumanMessage(content="Test message")]
                    }
                    
                    result = call_model(mock_state)
                    print(f"  Result: {result['messages'][0].content}")
            else:
                # Simulate normal response with stop reason
                with patch('core.app.model_chain') as mock_chain:
                    mock_response = MockResponse(content, stop_reason)
                    mock_chain.invoke.return_value = mock_response
                    
                    # Create mock state
                    mock_state = {
                        "messages": [HumanMessage(content="Test message")]
                    }
                    
                    result = call_model(mock_state)
                    print(f"  Result: {result['messages'][0].content}")
                    
        except Exception as e:
            print(f"  Error: {e}")
        
        print()

def main():
    """Run all tests."""
    print("🧪 Anthropic API Error Handling & Stop Reason Tests\n")
    print("=" * 60)
    
    # Run synchronous tests
    test_error_handling()
    test_stop_reasons()
    test_max_tokens_simulation()
    
    # Run async integration test
    print("Running integration tests...")
    asyncio.run(test_integration_with_mock())
    
    print("=" * 60)
    print("✅ All tests completed!")
    print("\nTo test with real API:")
    print("1. Use very long prompts to trigger max_tokens")
    print("2. Set low max_tokens value in core/app.py")
    print("3. Use invalid API key to test 401 errors")
    print("4. Make rapid requests to test rate limiting")

if __name__ == "__main__":
    main()