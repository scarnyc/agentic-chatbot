#!/usr/bin/env python3
"""
Test script for extended thinking functionality.
Tests that the thinking configuration is properly set up.
"""

import os
import sys
sys.path.append('.')

from core.app import llm, model_with_tools
from langchain_core.messages import HumanMessage

def test_thinking_configuration():
    """Test that the model is configured for extended thinking."""
    print("Testing Extended Thinking Configuration...")
    
    # Check if model has thinking configuration
    if hasattr(llm, 'thinking'):
        print(f"✅ Thinking enabled: {llm.thinking}")
        print(f"   Budget tokens: {llm.thinking.get('budget_tokens', 'Unknown')}")
    else:
        print("❌ Thinking configuration not found")
        return False
    
    # Check for beta header
    if hasattr(llm, 'beta'):
        print(f"✅ Beta header: {llm.beta}")
    else:
        print("⚠️  Beta header not found - interleaved thinking may not work")
    
    return True

def test_thinking_response():
    """Test a simple thinking response."""
    print("\n🧠 Testing Thinking Response...")
    
    try:
        # Simple math problem that should trigger thinking
        test_message = HumanMessage(content="What's 17 * 23? Please show your thinking process.")
        
        print("Sending test message...")
        response = model_with_tools.invoke([test_message])
        
        print(f"Response type: {type(response)}")
        print(f"Response content length: {len(response.content) if response.content else 0}")
        
        # Check for thinking in additional_kwargs
        if hasattr(response, 'additional_kwargs') and 'thinking' in response.additional_kwargs:
            thinking = response.additional_kwargs['thinking']
            print(f"✅ Thinking content found: {len(thinking)} characters")
            print(f"   Thinking preview: {thinking[:100]}...")
            return True
        else:
            print("⚠️  No thinking content found in response")
            print(f"   Additional kwargs: {response.additional_kwargs if hasattr(response, 'additional_kwargs') else 'None'}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing thinking response: {e}")
        return False

def test_tool_thinking():
    """Test thinking with tool use."""
    print("\n🔧 Testing Thinking with Tool Use...")
    
    try:
        # Question that should trigger both thinking and tool use
        test_message = HumanMessage(content="Search for information about quantum computing and explain the key concepts.")
        
        print("Sending tool use test message...")
        response = model_with_tools.invoke([test_message])
        
        # Check if tool calls were made
        has_tool_calls = hasattr(response, 'tool_calls') and response.tool_calls
        print(f"Tool calls made: {has_tool_calls}")
        
        # Check for thinking
        has_thinking = (hasattr(response, 'additional_kwargs') and 
                       'thinking' in response.additional_kwargs)
        print(f"Thinking content: {has_thinking}")
        
        if has_thinking and has_tool_calls:
            print("✅ Interleaved thinking with tool use working")
            return True
        elif has_thinking:
            print("⚠️  Thinking works but no tool calls made")
            return True
        else:
            print("❌ Neither thinking nor tool calls detected")
            return False
            
    except Exception as e:
        print(f"❌ Error testing tool thinking: {e}")
        return False

if __name__ == "__main__":
    print("Extended Thinking Test Suite")
    print("=" * 40)
    
    # Test configuration
    config_ok = test_thinking_configuration()
    
    if not config_ok:
        print("\n❌ Configuration test failed - check ANTHROPIC_API_KEY and model setup")
        sys.exit(1)
    
    # Test basic thinking
    thinking_ok = test_thinking_response()
    
    # Test interleaved thinking with tools
    tool_thinking_ok = test_tool_thinking()
    
    print(f"\n📊 Test Results:")
    print(f"   Configuration: {'✅' if config_ok else '❌'}")
    print(f"   Basic Thinking: {'✅' if thinking_ok else '❌'}")
    print(f"   Tool Thinking: {'✅' if tool_thinking_ok else '❌'}")
    
    if config_ok and (thinking_ok or tool_thinking_ok):
        print("\n🎉 Extended thinking is working!")
        print("   Start the server and enable 'Show Thinking' to see thinking content in the UI")
    else:
        print("\n⚠️  Extended thinking may not be fully functional")
        print("   Check ANTHROPIC_API_KEY and model configuration")