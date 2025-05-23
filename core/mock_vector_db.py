# core/mock_vector_db.py

"""
Mock vector database for testing and fallback when no real vector database is available.
Provides the same interface as PostgreSQL and Pinecone implementations.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class MockVectorDB:
    """
    Mock vector database implementation for testing and fallback scenarios.
    Stores data in memory only - not persistent.
    """
    
    def __init__(self, namespace: str = "agentic-memory"):
        self.namespace = namespace
        self.memories = []  # In-memory storage
        self.memory_id_counter = 0
        logger.info(f"Initialized mock vector database with namespace: {namespace}")
    
    def store_text_memory(self, content: str, category: str = "general", metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store text memory in mock database."""
        try:
            self.memory_id_counter += 1
            memory = {
                "id": f"mock_{self.memory_id_counter}",
                "content": content,
                "content_type": "text",
                "category": category,
                "metadata": metadata or {},
                "timestamp": datetime.now(),
                "score": 1.0  # Mock score
            }
            self.memories.append(memory)
            logger.info(f"Stored text memory in mock DB: {len(content)} chars")
            return True
        except Exception as e:
            logger.error(f"Failed to store text memory in mock DB: {e}")
            return False
    
    def store_image_memory(self, image_data: str, description: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store image memory in mock database."""
        try:
            self.memory_id_counter += 1
            memory = {
                "id": f"mock_{self.memory_id_counter}",
                "content": description,
                "content_type": "image",
                "image_data": image_data,
                "metadata": metadata or {},
                "timestamp": datetime.now(),
                "score": 1.0  # Mock score
            }
            self.memories.append(memory)
            logger.info(f"Stored image memory in mock DB: {len(description)} chars description")
            return True
        except Exception as e:
            logger.error(f"Failed to store image memory in mock DB: {e}")
            return False
    
    def search_memories(self, query: str, query_type: str = "text", limit: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search memories in mock database using simple text matching."""
        try:
            results = []
            query_lower = query.lower()
            
            for memory in self.memories:
                # Simple text matching for mock search
                content_lower = memory["content"].lower()
                if query_lower in content_lower:
                    # Calculate mock similarity score based on query length vs content match
                    score = len(query) / len(memory["content"]) if memory["content"] else 0.1
                    memory_copy = memory.copy()
                    memory_copy["score"] = min(score, 1.0)
                    results.append(memory_copy)
            
            # Sort by mock score and limit results
            results.sort(key=lambda x: x["score"], reverse=True)
            results = results[:limit]
            
            logger.info(f"Mock search found {len(results)} results for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search mock DB: {e}")
            return []
    
    def health_check(self) -> bool:
        """Health check for mock database."""
        return True  # Mock is always healthy
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics from mock database."""
        text_memories = sum(1 for m in self.memories if m["content_type"] == "text")
        image_memories = sum(1 for m in self.memories if m["content_type"] == "image")
        
        return {
            "status": "connected",
            "database_type": "MockVectorDB",
            "namespace": self.namespace,
            "total_vectors": len(self.memories),
            "text_memories": text_memories,
            "image_memories": image_memories,
            "table_size": f"{len(self.memories)} memories (in-memory)"
        }
    
    def close(self):
        """Close mock database connection."""
        logger.info("Closing mock vector database")
        self.memories.clear()

# Global instance (can be used as singleton)
mock_vector_db = None