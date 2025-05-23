#!/usr/bin/env python3
"""
Simple test script for the long-term memory system.
Tests semantic, episodic, and procedural memory functionality.
"""

import os
import sys
sys.path.append('.')

from core.long_term_memory import LongTermMemoryStore
from core.memory_agent import MemoryEnhancedAgent
from langchain_core.messages import HumanMessage, AIMessage

def test_memory_system():
    """Test the memory system functionality."""
    print("Testing Long-term Memory System...")
    
    # Initialize memory store
    memory_store = LongTermMemoryStore(memory_dir="test_memory")
    memory_agent = MemoryEnhancedAgent(memory_store)
    
    if not memory_store.embeddings:
        print("⚠️  OpenAI API key not found - testing without embeddings")
        print("   Set OPENAI_API_KEY environment variable for full functionality")
        return
    
    print("✓ Memory store initialized with embeddings")
    
    # Test semantic memory
    print("\n📚 Testing Semantic Memory...")
    semantic_id = memory_store.add_semantic_memory(
        content="I prefer Python programming over JavaScript",
        category="preference",
        confidence=0.9,
        source="user_stated"
    )
    print(f"   Added semantic memory: {semantic_id}")
    
    # Search semantic memories
    results = memory_store.search_semantic_memories("programming languages", top_k=3)
    print(f"   Search results: {len(results)} memories found")
    for result in results:
        print(f"   - {result['content'][:50]}... (similarity: {result['similarity']:.2f})")
    
    # Test episodic memory
    print("\n📖 Testing Episodic Memory...")
    episodic_id = memory_store.add_episodic_memory(
        conversation_id="test_conv_001",
        summary="User asked about Python programming best practices",
        key_events=["programming_question", "code_discussion"],
        tools_used=["wikipedia", "search"],
        outcomes=["user_satisfied"],
        importance_score=0.8
    )
    print(f"   Added episodic memory: {episodic_id}")
    
    # Search episodic memories
    results = memory_store.search_episodic_memories("Python programming", top_k=3)
    print(f"   Search results: {len(results)} memories found")
    for result in results:
        print(f"   - {result['summary'][:50]}... (similarity: {result['similarity']:.2f})")
    
    # Test procedural memory
    print("\n🔧 Testing Procedural Memory...")
    procedural_id = memory_store.add_procedural_memory(
        pattern_name="code_help_pattern",
        trigger_conditions=["user asks for code help", "programming question"],
        action_sequence=["search documentation", "provide example", "explain concepts"],
        context="programming assistance",
        learned_from="test_conversation"
    )
    print(f"   Added procedural memory: {procedural_id}")
    
    # Search procedural memories
    results = memory_store.search_procedural_memories("code help", top_k=3)
    print(f"   Search results: {len(results)} memories found")
    for result in results:
        print(f"   - {result['pattern_name']}: {' -> '.join(result['action_sequence'])}")
    
    # Test memory agent integration
    print("\n🧠 Testing Memory Agent Integration...")
    test_messages = [
        HumanMessage(content="I like machine learning and I work as a data scientist"),
        AIMessage(content="That's great! Machine learning is a fascinating field. As a data scientist, you must work with various algorithms and datasets."),
        HumanMessage(content="Can you help me write a Python function for data preprocessing?"),
        AIMessage(content="Certainly! Here's a Python function for basic data preprocessing:\n\n```python\ndef preprocess_data(df):\n    # Remove duplicates\n    df = df.drop_duplicates()\n    # Handle missing values\n    df = df.fillna(0)\n    return df\n```")
    ]
    
    # Process conversation for memory extraction
    memory_agent.process_conversation(test_messages, "test_conv_002")
    print("   Processed conversation for memory extraction")
    
    # Test memory context retrieval
    context = memory_agent.get_memory_context_for_message("I need help with Python coding")
    print(f"   Retrieved memory context ({len(context)} characters)")
    if context:
        print(f"   Context preview: {context[:200]}...")
    
    # Get final stats
    print("\n📊 Memory Statistics:")
    stats = memory_store.get_memory_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n✅ Memory system test completed successfully!")
    
    # Cleanup test files
    import shutil
    if os.path.exists("test_memory"):
        shutil.rmtree("test_memory")
        print("   Cleaned up test files")

if __name__ == "__main__":
    test_memory_system()