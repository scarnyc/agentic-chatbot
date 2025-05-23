# core/long_term_memory.py

import os
import json
import time
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
from langchain_openai import OpenAIEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class SemanticMemory:
    """Stores factual knowledge and learned information."""
    id: str
    content: str
    embedding: List[float]
    category: str  # "fact", "preference", "skill", "domain_knowledge"
    confidence: float
    source: str  # "user_stated", "inferred", "external_tool"
    created_at: str
    updated_at: str
    access_count: int = 0

@dataclass
class EpisodicMemory:
    """Stores specific conversation episodes and experiences."""
    id: str
    conversation_id: str
    summary: str
    embedding: List[float]
    participants: List[str]
    key_events: List[str]
    emotions: List[str]  # detected emotional context
    outcomes: List[str]  # what was accomplished
    tools_used: List[str]
    created_at: str
    duration_minutes: int
    importance_score: float

@dataclass
class ProceduralMemory:
    """Stores learned patterns and procedures."""
    id: str
    pattern_name: str
    trigger_conditions: List[str]
    action_sequence: List[str]
    embedding: List[float]
    success_rate: float
    usage_count: int
    context: str
    learned_from: str  # conversation_id or "system"
    created_at: str
    updated_at: str

class LongTermMemoryStore:
    """
    Advanced memory store using OpenAI embeddings for semantic search.
    Implements three types of memory: Semantic, Episodic, and Procedural.
    """
    
    def __init__(self, memory_dir: str = "memory", openai_api_key: Optional[str] = None):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        
        # Initialize embeddings
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("No OpenAI API key found. Long-term memory will be disabled.")
            self.embeddings = None
        else:
            try:
                self.embeddings = OpenAIEmbeddings(
                    api_key=self.openai_api_key,
                    model="text-embedding-3-small"  # Cost-effective embedding model
                )
                logger.info("OpenAI embeddings initialized for long-term memory")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI embeddings: {e}")
                self.embeddings = None
        
        # Memory stores
        self.semantic_memories: Dict[str, SemanticMemory] = {}
        self.episodic_memories: Dict[str, EpisodicMemory] = {}
        self.procedural_memories: Dict[str, ProceduralMemory] = {}
        
        # Load existing memories
        self._load_memories()
        
        # Memory limits to prevent unbounded growth
        self.max_semantic_memories = 1000
        self.max_episodic_memories = 500
        self.max_procedural_memories = 200
    
    def _generate_id(self, content: str) -> str:
        """Generate a unique ID based on content hash."""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text using OpenAI."""
        if not self.embeddings:
            return None
        
        try:
            embedding = self.embeddings.embed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            return None
    
    def _load_memories(self):
        """Load memories from disk."""
        try:
            semantic_file = self.memory_dir / "semantic_memories.json"
            if semantic_file.exists():
                with open(semantic_file, 'r') as f:
                    data = json.load(f)
                    self.semantic_memories = {
                        k: SemanticMemory(**v) for k, v in data.items()
                    }
            
            episodic_file = self.memory_dir / "episodic_memories.json"
            if episodic_file.exists():
                with open(episodic_file, 'r') as f:
                    data = json.load(f)
                    self.episodic_memories = {
                        k: EpisodicMemory(**v) for k, v in data.items()
                    }
            
            procedural_file = self.memory_dir / "procedural_memories.json"
            if procedural_file.exists():
                with open(procedural_file, 'r') as f:
                    data = json.load(f)
                    self.procedural_memories = {
                        k: ProceduralMemory(**v) for k, v in data.items()
                    }
            
            logger.info(f"Loaded {len(self.semantic_memories)} semantic, "
                       f"{len(self.episodic_memories)} episodic, "
                       f"{len(self.procedural_memories)} procedural memories")
        
        except Exception as e:
            logger.error(f"Failed to load memories: {e}")
    
    def _save_memories(self):
        """Save memories to disk."""
        try:
            # Save semantic memories
            semantic_file = self.memory_dir / "semantic_memories.json"
            with open(semantic_file, 'w') as f:
                data = {k: asdict(v) for k, v in self.semantic_memories.items()}
                json.dump(data, f, indent=2)
            
            # Save episodic memories
            episodic_file = self.memory_dir / "episodic_memories.json"
            with open(episodic_file, 'w') as f:
                data = {k: asdict(v) for k, v in self.episodic_memories.items()}
                json.dump(data, f, indent=2)
            
            # Save procedural memories
            procedural_file = self.memory_dir / "procedural_memories.json"
            with open(procedural_file, 'w') as f:
                data = {k: asdict(v) for k, v in self.procedural_memories.items()}
                json.dump(data, f, indent=2)
            
            logger.debug("Memories saved to disk")
        
        except Exception as e:
            logger.error(f"Failed to save memories: {e}")
    
    def add_semantic_memory(self, content: str, category: str, confidence: float = 0.8, 
                          source: str = "user_stated") -> Optional[str]:
        """Add a new semantic memory (fact, preference, skill, etc.)."""
        if not self.embeddings:
            return None
        
        embedding = self._get_embedding(content)
        if not embedding:
            return None
        
        memory_id = self._generate_id(content)
        now = datetime.now().isoformat()
        
        # Check if similar memory already exists
        similar_memories = self.search_semantic_memories(content, top_k=3, threshold=0.9)
        if similar_memories:
            # Update existing memory instead of creating duplicate
            existing_id = similar_memories[0]['id']
            self.semantic_memories[existing_id].updated_at = now
            self.semantic_memories[existing_id].confidence = max(
                self.semantic_memories[existing_id].confidence, confidence
            )
            self.semantic_memories[existing_id].access_count += 1
            self._save_memories()
            return existing_id
        
        memory = SemanticMemory(
            id=memory_id,
            content=content,
            embedding=embedding,
            category=category,
            confidence=confidence,
            source=source,
            created_at=now,
            updated_at=now
        )
        
        self.semantic_memories[memory_id] = memory
        
        # Manage memory limits
        if len(self.semantic_memories) > self.max_semantic_memories:
            self._prune_semantic_memories()
        
        self._save_memories()
        logger.info(f"Added semantic memory: {category} - {content[:100]}...")
        return memory_id
    
    def add_episodic_memory(self, conversation_id: str, summary: str, 
                          key_events: List[str], tools_used: List[str] = None,
                          emotions: List[str] = None, outcomes: List[str] = None,
                          importance_score: float = 0.5) -> Optional[str]:
        """Add a new episodic memory from a conversation."""
        if not self.embeddings:
            return None
        
        embedding = self._get_embedding(summary)
        if not embedding:
            return None
        
        memory_id = self._generate_id(f"{conversation_id}_{summary}")
        now = datetime.now().isoformat()
        
        memory = EpisodicMemory(
            id=memory_id,
            conversation_id=conversation_id,
            summary=summary,
            embedding=embedding,
            participants=["user", "assistant"],
            key_events=key_events or [],
            emotions=emotions or [],
            outcomes=outcomes or [],
            tools_used=tools_used or [],
            created_at=now,
            duration_minutes=0,  # Could be calculated if needed
            importance_score=importance_score
        )
        
        self.episodic_memories[memory_id] = memory
        
        # Manage memory limits
        if len(self.episodic_memories) > self.max_episodic_memories:
            self._prune_episodic_memories()
        
        self._save_memories()
        logger.info(f"Added episodic memory: {summary[:100]}...")
        return memory_id
    
    def add_procedural_memory(self, pattern_name: str, trigger_conditions: List[str],
                            action_sequence: List[str], context: str,
                            learned_from: str = "system") -> Optional[str]:
        """Add a new procedural memory (learned pattern/procedure)."""
        if not self.embeddings:
            return None
        
        # Create searchable text from the procedure
        procedure_text = f"{pattern_name}: {' '.join(trigger_conditions)} -> {' '.join(action_sequence)}"
        embedding = self._get_embedding(procedure_text)
        if not embedding:
            return None
        
        memory_id = self._generate_id(procedure_text)
        now = datetime.now().isoformat()
        
        memory = ProceduralMemory(
            id=memory_id,
            pattern_name=pattern_name,
            trigger_conditions=trigger_conditions,
            action_sequence=action_sequence,
            embedding=embedding,
            success_rate=0.0,
            usage_count=0,
            context=context,
            learned_from=learned_from,
            created_at=now,
            updated_at=now
        )
        
        self.procedural_memories[memory_id] = memory
        
        # Manage memory limits
        if len(self.procedural_memories) > self.max_procedural_memories:
            self._prune_procedural_memories()
        
        self._save_memories()
        logger.info(f"Added procedural memory: {pattern_name}")
        return memory_id
    
    def search_semantic_memories(self, query: str, top_k: int = 5, 
                                threshold: float = 0.7) -> List[Dict]:
        """Search semantic memories by similarity."""
        if not self.embeddings or not self.semantic_memories:
            return []
        
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            return []
        
        results = []
        for memory in self.semantic_memories.values():
            if memory.embedding:
                similarity = cosine_similarity(
                    [query_embedding], [memory.embedding]
                )[0][0]
                
                if similarity >= threshold:
                    # Update access count
                    memory.access_count += 1
                    
                    results.append({
                        'id': memory.id,
                        'content': memory.content,
                        'category': memory.category,
                        'confidence': memory.confidence,
                        'similarity': similarity,
                        'source': memory.source
                    })
        
        # Sort by similarity and return top_k
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]
    
    def search_episodic_memories(self, query: str, top_k: int = 3,
                               threshold: float = 0.6) -> List[Dict]:
        """Search episodic memories by similarity."""
        if not self.embeddings or not self.episodic_memories:
            return []
        
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            return []
        
        results = []
        for memory in self.episodic_memories.values():
            if memory.embedding:
                similarity = cosine_similarity(
                    [query_embedding], [memory.embedding]
                )[0][0]
                
                if similarity >= threshold:
                    results.append({
                        'id': memory.id,
                        'summary': memory.summary,
                        'key_events': memory.key_events,
                        'tools_used': memory.tools_used,
                        'outcomes': memory.outcomes,
                        'similarity': similarity,
                        'importance_score': memory.importance_score
                    })
        
        # Sort by similarity and importance
        results.sort(key=lambda x: (x['similarity'] * x['importance_score']), reverse=True)
        return results[:top_k]
    
    def search_procedural_memories(self, query: str, top_k: int = 3,
                                 threshold: float = 0.7) -> List[Dict]:
        """Search procedural memories by similarity."""
        if not self.embeddings or not self.procedural_memories:
            return []
        
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            return []
        
        results = []
        for memory in self.procedural_memories.values():
            if memory.embedding:
                similarity = cosine_similarity(
                    [query_embedding], [memory.embedding]
                )[0][0]
                
                if similarity >= threshold:
                    # Update usage count
                    memory.usage_count += 1
                    
                    results.append({
                        'id': memory.id,
                        'pattern_name': memory.pattern_name,
                        'trigger_conditions': memory.trigger_conditions,
                        'action_sequence': memory.action_sequence,
                        'success_rate': memory.success_rate,
                        'similarity': similarity,
                        'context': memory.context
                    })
        
        # Sort by similarity and success rate
        results.sort(key=lambda x: (x['similarity'] * (x['success_rate'] + 0.1)), reverse=True)
        return results[:top_k]
    
    def get_relevant_context(self, query: str, max_memories: int = 10) -> Dict:
        """Get relevant context from all memory types for a query."""
        context = {
            'semantic': self.search_semantic_memories(query, top_k=5),
            'episodic': self.search_episodic_memories(query, top_k=3),
            'procedural': self.search_procedural_memories(query, top_k=2)
        }
        
        # Limit total memories returned
        total_memories = sum(len(memories) for memories in context.values())
        if total_memories > max_memories:
            # Prioritize semantic memories, then episodic, then procedural
            context['semantic'] = context['semantic'][:6]
            context['episodic'] = context['episodic'][:3]
            context['procedural'] = context['procedural'][:1]
        
        return context
    
    def _prune_semantic_memories(self):
        """Remove least important semantic memories when limit is exceeded."""
        if len(self.semantic_memories) <= self.max_semantic_memories:
            return
        
        # Sort by access count and confidence, remove lowest scoring
        memories_with_scores = []
        for memory_id, memory in self.semantic_memories.items():
            score = memory.access_count * memory.confidence
            memories_with_scores.append((memory_id, score))
        
        memories_with_scores.sort(key=lambda x: x[1])
        to_remove = len(self.semantic_memories) - self.max_semantic_memories
        
        for memory_id, _ in memories_with_scores[:to_remove]:
            del self.semantic_memories[memory_id]
        
        logger.info(f"Pruned {to_remove} semantic memories")
    
    def _prune_episodic_memories(self):
        """Remove least important episodic memories when limit is exceeded."""
        if len(self.episodic_memories) <= self.max_episodic_memories:
            return
        
        # Sort by importance score and recency, remove lowest scoring
        memories_with_scores = []
        for memory_id, memory in self.episodic_memories.items():
            # Calculate recency score (more recent = higher score)
            created_time = datetime.fromisoformat(memory.created_at)
            days_old = (datetime.now() - created_time).days
            recency_score = max(0, 1 - days_old / 365)  # Decay over a year
            
            score = memory.importance_score * recency_score
            memories_with_scores.append((memory_id, score))
        
        memories_with_scores.sort(key=lambda x: x[1])
        to_remove = len(self.episodic_memories) - self.max_episodic_memories
        
        for memory_id, _ in memories_with_scores[:to_remove]:
            del self.episodic_memories[memory_id]
        
        logger.info(f"Pruned {to_remove} episodic memories")
    
    def _prune_procedural_memories(self):
        """Remove least effective procedural memories when limit is exceeded."""
        if len(self.procedural_memories) <= self.max_procedural_memories:
            return
        
        # Sort by success rate and usage count, remove lowest scoring
        memories_with_scores = []
        for memory_id, memory in self.procedural_memories.items():
            score = memory.success_rate * (memory.usage_count + 1)
            memories_with_scores.append((memory_id, score))
        
        memories_with_scores.sort(key=lambda x: x[1])
        to_remove = len(self.procedural_memories) - self.max_procedural_memories
        
        for memory_id, _ in memories_with_scores[:to_remove]:
            del self.procedural_memories[memory_id]
        
        logger.info(f"Pruned {to_remove} procedural memories")
    
    def get_memory_stats(self) -> Dict:
        """Get statistics about the memory store."""
        return {
            'semantic_count': len(self.semantic_memories),
            'episodic_count': len(self.episodic_memories),
            'procedural_count': len(self.procedural_memories),
            'total_memories': len(self.semantic_memories) + len(self.episodic_memories) + len(self.procedural_memories),
            'embeddings_enabled': self.embeddings is not None
        }