# core/memory_agent.py

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import MessagesState
from langgraph.store.base import BaseStore

from core.long_term_memory import LongTermMemoryStore

logger = logging.getLogger(__name__)

class MemoryEnhancedAgent:
    """
    An agent wrapper that adds long-term memory capabilities to the conversation flow.
    Extracts and stores semantic, episodic, and procedural memories from conversations.
    """
    
    def __init__(self, memory_store: LongTermMemoryStore):
        self.memory_store = memory_store
        self.conversation_summaries = {}  # Track conversation summaries for episodic memory
        
    def extract_semantic_memories(self, messages: List[BaseMessage]) -> List[Dict]:
        """Extract potential semantic memories from conversation messages."""
        semantic_memories = []
        
        for message in messages:
            if isinstance(message, HumanMessage):
                content = message.content.lower()
                
                # Detect preferences
                if any(phrase in content for phrase in ["i like", "i prefer", "i enjoy", "i love", "i hate", "i dislike"]):
                    semantic_memories.append({
                        'content': message.content,
                        'category': 'preference',
                        'confidence': 0.8,
                        'source': 'user_stated'
                    })
                
                # Detect facts about user
                elif any(phrase in content for phrase in ["i am", "i work", "i live", "i have", "my name is"]):
                    semantic_memories.append({
                        'content': message.content,
                        'category': 'fact',
                        'confidence': 0.9,
                        'source': 'user_stated'
                    })
                
                # Detect skills or experience
                elif any(phrase in content for phrase in ["i know", "i can", "i've worked with", "i'm experienced in"]):
                    semantic_memories.append({
                        'content': message.content,
                        'category': 'skill',
                        'confidence': 0.8,
                        'source': 'user_stated'
                    })
            
            elif isinstance(message, AIMessage):
                # Extract learned domain knowledge from AI responses
                if any(keyword in message.content.lower() for keyword in 
                       ["according to", "research shows", "studies indicate", "it's important to note"]):
                    semantic_memories.append({
                        'content': message.content,
                        'category': 'domain_knowledge',
                        'confidence': 0.7,
                        'source': 'external_tool'
                    })
        
        return semantic_memories
    
    def extract_procedural_memories(self, messages: List[BaseMessage]) -> List[Dict]:
        """Extract procedural patterns from successful interactions."""
        procedural_memories = []
        
        # Look for patterns where user asks for something and AI successfully provides it
        for i in range(len(messages) - 1):
            if isinstance(messages[i], HumanMessage) and isinstance(messages[i + 1], AIMessage):
                user_request = messages[i].content.lower()
                ai_response = messages[i + 1].content
                
                # Detect successful tool usage patterns
                if "search" in user_request and "search" in ai_response.lower():
                    procedural_memories.append({
                        'pattern_name': 'search_request_pattern',
                        'trigger_conditions': [f"User requests search: {user_request[:100]}"],
                        'action_sequence': ['use_search_tool', 'provide_results', 'summarize_findings'],
                        'context': 'web_search',
                        'learned_from': 'conversation'
                    })
                
                elif any(code_word in user_request for code_word in ["code", "program", "script", "function"]):
                    if "```" in ai_response:  # AI provided code
                        procedural_memories.append({
                            'pattern_name': 'code_generation_pattern',
                            'trigger_conditions': [f"User requests code: {user_request[:100]}"],
                            'action_sequence': ['analyze_requirements', 'generate_code', 'provide_explanation'],
                            'context': 'programming',
                            'learned_from': 'conversation'
                        })
                
                elif "explain" in user_request or "what is" in user_request:
                    procedural_memories.append({
                        'pattern_name': 'explanation_pattern',
                        'trigger_conditions': [f"User asks for explanation: {user_request[:100]}"],
                        'action_sequence': ['search_knowledge', 'structure_explanation', 'provide_examples'],
                        'context': 'educational',
                        'learned_from': 'conversation'
                    })
        
        return procedural_memories
    
    def create_conversation_summary(self, messages: List[BaseMessage], conversation_id: str) -> Optional[Dict]:
        """Create a summary of the conversation for episodic memory."""
        if len(messages) < 2:
            return None
        
        # Extract key information
        key_events = []
        tools_used = []
        outcomes = []
        emotions = []
        
        user_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
        ai_messages = [msg for msg in messages if isinstance(msg, AIMessage)]
        
        # Analyze user intent and outcomes
        if user_messages:
            first_user_msg = user_messages[0].content.lower()
            
            # Detect emotional context
            if any(word in first_user_msg for word in ["help", "please", "confused", "stuck"]):
                emotions.append("seeking_help")
            if any(word in first_user_msg for word in ["urgent", "quickly", "asap"]):
                emotions.append("urgency")
            if any(word in first_user_msg for word in ["thanks", "thank you", "appreciate"]):
                emotions.append("gratitude")
        
        # Detect tools used
        for msg in ai_messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get('name', 'unknown_tool')
                    if tool_name not in tools_used:
                        tools_used.append(tool_name)
        
        # Extract key events
        for msg in messages:
            content = msg.content.lower()
            if "error" in content:
                key_events.append("error_encountered")
            elif "success" in content or "completed" in content:
                key_events.append("task_completed")
            elif "search" in content:
                key_events.append("information_search")
            elif "code" in content or "```" in msg.content:
                key_events.append("code_interaction")
        
        # Determine outcomes
        if any("thank" in msg.content.lower() for msg in user_messages[-2:]):
            outcomes.append("user_satisfied")
        if any("error" in msg.content.lower() for msg in ai_messages[-2:]):
            outcomes.append("partial_failure")
        else:
            outcomes.append("task_completed")
        
        # Create summary
        summary_parts = []
        if user_messages:
            summary_parts.append(f"User requested: {user_messages[0].content[:100]}")
        if tools_used:
            summary_parts.append(f"Tools used: {', '.join(tools_used)}")
        if outcomes:
            summary_parts.append(f"Outcome: {', '.join(outcomes)}")
        
        summary = ". ".join(summary_parts)
        
        # Calculate importance score
        importance_score = 0.5  # Base importance
        if "error" in key_events:
            importance_score += 0.2  # Errors are important to remember
        if len(tools_used) > 1:
            importance_score += 0.1  # Multi-tool interactions are complex
        if "user_satisfied" in outcomes:
            importance_score += 0.2  # Successful interactions are valuable
        
        return {
            'conversation_id': conversation_id,
            'summary': summary,
            'key_events': key_events,
            'tools_used': tools_used,
            'emotions': emotions,
            'outcomes': outcomes,
            'importance_score': min(importance_score, 1.0)
        }
    
    def process_conversation(self, messages: List[BaseMessage], conversation_id: str):
        """Process a conversation to extract and store memories."""
        if not self.memory_store.embeddings:
            logger.warning("Embeddings not available - skipping memory processing")
            return
        
        try:
            # Extract and store semantic memories
            semantic_memories = self.extract_semantic_memories(messages)
            for memory_data in semantic_memories:
                self.memory_store.add_semantic_memory(**memory_data)
            
            # Extract and store procedural memories
            procedural_memories = self.extract_procedural_memories(messages)
            for memory_data in procedural_memories:
                self.memory_store.add_procedural_memory(**memory_data)
            
            # Create and store episodic memory
            conversation_summary = self.create_conversation_summary(messages, conversation_id)
            if conversation_summary:
                self.memory_store.add_episodic_memory(**conversation_summary)
            
            logger.info(f"Processed conversation {conversation_id}: "
                       f"{len(semantic_memories)} semantic, "
                       f"{len(procedural_memories)} procedural, "
                       f"{'1' if conversation_summary else '0'} episodic memories")
        
        except Exception as e:
            logger.error(f"Error processing conversation memories: {e}")
    
    def get_memory_context_for_message(self, message: str) -> str:
        """Get relevant memory context to enhance the current message."""
        if not self.memory_store.embeddings:
            return ""
        
        try:
            context = self.memory_store.get_relevant_context(message)
            
            context_parts = []
            
            # Add semantic memories
            if context['semantic']:
                semantic_context = "## Relevant Knowledge:\n"
                for memory in context['semantic']:
                    semantic_context += f"- {memory['content']} (confidence: {memory['confidence']:.1f})\n"
                context_parts.append(semantic_context)
            
            # Add episodic memories
            if context['episodic']:
                episodic_context = "## Previous Conversations:\n"
                for memory in context['episodic']:
                    episodic_context += f"- {memory['summary']}\n"
                context_parts.append(episodic_context)
            
            # Add procedural memories
            if context['procedural']:
                procedural_context = "## Learned Patterns:\n"
                for memory in context['procedural']:
                    pattern = f"{memory['pattern_name']}: {' -> '.join(memory['action_sequence'])}"
                    procedural_context += f"- {pattern}\n"
                context_parts.append(procedural_context)
            
            if context_parts:
                return "\n\n".join(context_parts) + "\n\n"
            else:
                return ""
        
        except Exception as e:
            logger.error(f"Error retrieving memory context: {e}")
            return ""
    
    def update_procedural_success(self, pattern_name: str, success: bool):
        """Update the success rate of a procedural memory pattern."""
        for memory in self.memory_store.procedural_memories.values():
            if memory.pattern_name == pattern_name:
                total_uses = memory.usage_count + 1
                if success:
                    memory.success_rate = ((memory.success_rate * memory.usage_count) + 1) / total_uses
                else:
                    memory.success_rate = (memory.success_rate * memory.usage_count) / total_uses
                memory.usage_count = total_uses
                memory.updated_at = datetime.now().isoformat()
                break
        
        # Save updated memories
        self.memory_store._save_memories()

def create_memory_enhanced_system_message(memory_context: str, original_prompt: str) -> str:
    """Create an enhanced system message that includes memory context."""
    if not memory_context.strip():
        return original_prompt
    
    enhanced_prompt = f"""{original_prompt}

## Memory Context
You have access to long-term memory about this user and previous conversations:

{memory_context}

Use this context to provide more personalized and contextually aware responses. Reference previous conversations or learned preferences when relevant, but don't explicitly mention "I remember from our previous conversation" unless the context directly relates to the current query.
"""
    
    return enhanced_prompt