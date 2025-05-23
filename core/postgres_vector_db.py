# core/postgres_vector_db.py

import os
import json
import base64
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
import io

import numpy as np
from langchain_openai import OpenAIEmbeddings

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, Json
    from psycopg2.pool import SimpleConnectionPool
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

try:
    from PIL import Image
    import clip
    import torch
    HAS_MULTIMODAL = True
except ImportError:
    HAS_MULTIMODAL = False
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class PostgresVectorRecord:
    """Unified record for text and multimodal content in PostgreSQL."""
    id: Optional[int] = None
    content: str = ""
    content_type: str = "text"  # "text", "image", "multimodal"
    category: str = "general"
    metadata: Dict[str, Any] = None
    embedding: Optional[List[float]] = None
    image_data: Optional[str] = None  # base64 encoded image
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()

class PostgreSQLVectorDB:
    """
    PostgreSQL + pgvector implementation for unified text and multimodal vector storage.
    Designed for easy migration to MCP server architecture.
    """
    
    def __init__(self, namespace: str = "agentic-memory"):
        if not HAS_PSYCOPG2:
            raise ImportError("PostgreSQL dependencies not installed. Run: pip install psycopg2-binary pgvector")
            
        self.namespace = namespace
        self.database_url = os.getenv("DATABASE_URL", "postgresql://localhost:5432/agentic_vectors")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Connection pool
        self.pool = None
        
        # Embedding models
        self.text_embeddings = None
        self.clip_model = None
        self.clip_preprocess = None
        self.device = "cuda" if HAS_MULTIMODAL and torch.cuda.is_available() else "cpu"
        
        self._initialize_database()
        self._initialize_embedding_models()
    
    def _initialize_database(self) -> bool:
        """Initialize PostgreSQL database and create necessary tables."""
        try:
            # Create connection pool
            self.pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=self.database_url
            )
            
            # Test connection and setup
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cur:
                    # Enable pgvector extension
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    
                    # Create embeddings table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS embeddings (
                            id SERIAL PRIMARY KEY,
                            namespace VARCHAR(100) DEFAULT 'default',
                            vector vector(512),
                            content TEXT NOT NULL,
                            content_type VARCHAR(20) CHECK (content_type IN ('text', 'image', 'multimodal')),
                            category VARCHAR(100) DEFAULT 'general',
                            metadata JSONB DEFAULT '{}',
                            image_data TEXT,
                            timestamp TIMESTAMP DEFAULT NOW()
                        );
                    """)
                    
                    # Create indexes for performance
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_embeddings_vector 
                        ON embeddings USING hnsw (vector vector_cosine_ops);
                    """)
                    
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_embeddings_namespace 
                        ON embeddings (namespace);
                    """)
                    
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_embeddings_category 
                        ON embeddings (category);
                    """)
                    
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_embeddings_content_type 
                        ON embeddings (content_type);
                    """)
                    
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_embeddings_timestamp 
                        ON embeddings (timestamp);
                    """)
                    
                    conn.commit()
                    logger.info("PostgreSQL vector database initialized successfully")
                    
            finally:
                self.pool.putconn(conn)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL database: {e}")
            return False
    
    def _initialize_embedding_models(self) -> bool:
        """Initialize embedding models."""
        try:
            # Initialize text embeddings (OpenAI for consistency)
            if self.openai_api_key:
                self.text_embeddings = OpenAIEmbeddings(
                    api_key=self.openai_api_key,
                    model="text-embedding-3-small"
                )
                logger.info("OpenAI text embeddings initialized")
            
            # Initialize CLIP for multimodal embeddings
            if HAS_MULTIMODAL:
                try:
                    self.clip_model, self.clip_preprocess = clip.load("ViT-B/32", device=self.device)
                    logger.info(f"CLIP model loaded on device: {self.device}")
                except Exception as e:
                    logger.warning(f"Failed to load CLIP model: {e}")
                    self.clip_model = None
            else:
                logger.warning("Multimodal dependencies not available, CLIP disabled")
                self.clip_model = None
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding models: {e}")
            return False
    
    def _generate_id(self, content: str, content_type: str) -> str:
        """Generate unique ID for content."""
        hash_input = f"{content_type}:{content}:{datetime.now().isoformat()}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def _embed_text(self, text: str) -> Optional[List[float]]:
        """Generate text embedding using OpenAI."""
        try:
            if not self.text_embeddings:
                return None
            embedding = self.text_embeddings.embed_query(text)
            
            # Normalize to 512 dimensions for consistency with CLIP
            if len(embedding) != 512:
                # Pad or truncate to 512 dimensions
                if len(embedding) > 512:
                    embedding = embedding[:512]
                else:
                    embedding = embedding + [0.0] * (512 - len(embedding))
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate text embedding: {e}")
            return None
    
    def _embed_image(self, image_data: str) -> Optional[List[float]]:
        """Generate image embedding using CLIP."""
        try:
            if not self.clip_model or not HAS_MULTIMODAL:
                return None
                
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Preprocess and embed
            image_input = self.clip_preprocess(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_input)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            return image_features.cpu().numpy().flatten().tolist()
            
        except Exception as e:
            logger.error(f"Failed to generate image embedding: {e}")
            return None
    
    def _embed_multimodal(self, text: str, image_data: Optional[str] = None) -> Optional[List[float]]:
        """Generate combined text+image embedding."""
        try:
            if not self.clip_model or not HAS_MULTIMODAL:
                return self._embed_text(text)
            
            # Encode text with CLIP
            text_tokens = clip.tokenize([text]).to(self.device)
            
            with torch.no_grad():
                text_features = self.clip_model.encode_text(text_tokens)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            
            # If image provided, combine embeddings
            if image_data:
                image_embedding = self._embed_image(image_data)
                if image_embedding:
                    text_embedding = text_features.cpu().numpy().flatten()
                    # Average the embeddings
                    combined = (text_embedding + np.array(image_embedding)) / 2
                    return combined.tolist()
            
            return text_features.cpu().numpy().flatten().tolist()
            
        except Exception as e:
            logger.error(f"Failed to generate multimodal embedding: {e}")
            return None

    # MCP-ready interface methods
    
    def store_text_memory(
        self, 
        content: str, 
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store text-based memory (MCP compatible)."""
        try:
            if not self.pool:
                return False
                
            metadata = metadata or {}
            embedding = self._embed_text(content)
            if not embedding:
                return False
            
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO embeddings 
                        (namespace, vector, content, content_type, category, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (
                        self.namespace,
                        embedding,
                        content,
                        "text",
                        category,
                        Json(metadata)
                    ))
                    
                    record_id = cur.fetchone()[0]
                    conn.commit()
                    
                    logger.info(f"Stored text memory: {record_id}")
                    return True
                    
            finally:
                self.pool.putconn(conn)
            
        except Exception as e:
            logger.error(f"Failed to store text memory: {e}")
            return False
    
    def store_image_memory(
        self,
        image_data: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store image-based memory (MCP compatible)."""
        try:
            if not self.pool:
                return False
                
            metadata = metadata or {}
            embedding = self._embed_multimodal(description, image_data)
            if not embedding:
                return False
            
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO embeddings 
                        (namespace, vector, content, content_type, category, metadata, image_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (
                        self.namespace,
                        embedding,
                        description,
                        "image",
                        metadata.get("category", "visual"),
                        Json(metadata),
                        image_data
                    ))
                    
                    record_id = cur.fetchone()[0]
                    conn.commit()
                    
                    logger.info(f"Stored image memory: {record_id}")
                    return True
                    
            finally:
                self.pool.putconn(conn)
            
        except Exception as e:
            logger.error(f"Failed to store image memory: {e}")
            return False
    
    def search_memories(
        self,
        query: str,
        query_type: str = "text",
        limit: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search memories by text query (MCP compatible)."""
        try:
            if not self.pool:
                return []
            
            # Generate query embedding
            if query_type == "text":
                query_embedding = self._embed_text(query)
            else:
                query_embedding = self._embed_multimodal(query)
                
            if not query_embedding:
                return []
            
            conn = self.pool.getconn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Build WHERE clause for filtering
                    where_conditions = ["namespace = %s"]
                    params = [self.namespace]
                    
                    if filter_metadata:
                        for key, value in filter_metadata.items():
                            if key in ["category", "content_type"]:
                                where_conditions.append(f"{key} = %s")
                                params.append(value)
                            else:
                                where_conditions.append("metadata ->> %s = %s")
                                params.extend([key, str(value)])
                    
                    where_clause = " AND ".join(where_conditions)
                    
                    # Execute similarity search
                    query_sql = f"""
                        SELECT id, content, content_type, category, metadata, image_data,
                               1 - (vector <=> %s::vector) as similarity,
                               timestamp
                        FROM embeddings
                        WHERE {where_clause}
                        ORDER BY vector <=> %s::vector
                        LIMIT %s;
                    """
                    
                    params = [query_embedding] + params + [query_embedding, limit]
                    cur.execute(query_sql, params)
                    
                    results = cur.fetchall()
                    
                    # Format results
                    formatted_results = []
                    for row in results:
                        result = {
                            "id": str(row["id"]),
                            "score": float(row["similarity"]),
                            "content": row["content"],
                            "content_type": row["content_type"],
                            "metadata": dict(row["metadata"]) if row["metadata"] else {},
                        }
                        
                        # Add category to metadata
                        result["metadata"]["category"] = row["category"]
                        result["metadata"]["timestamp"] = row["timestamp"].isoformat() if row["timestamp"] else None
                        
                        # Include image data if present
                        if row["image_data"]:
                            result["image_data"] = row["image_data"]
                        
                        formatted_results.append(result)
                    
                    logger.info(f"Found {len(formatted_results)} memories for query: {query[:50]}...")
                    return formatted_results
                    
            finally:
                self.pool.putconn(conn)
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics (MCP compatible)."""
        try:
            if not self.pool:
                return {"status": "disconnected"}
            
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cur:
                    # Get total vector count
                    cur.execute("SELECT COUNT(*) FROM embeddings WHERE namespace = %s;", (self.namespace,))
                    total_vectors = cur.fetchone()[0]
                    
                    # Get count by content type
                    cur.execute("""
                        SELECT content_type, COUNT(*) 
                        FROM embeddings 
                        WHERE namespace = %s 
                        GROUP BY content_type;
                    """, (self.namespace,))
                    
                    content_type_counts = dict(cur.fetchall())
                    
                    # Get database size
                    cur.execute("""
                        SELECT pg_size_pretty(pg_total_relation_size('embeddings')) as table_size;
                    """)
                    table_size = cur.fetchone()[0]
                    
                    return {
                        "status": "connected",
                        "total_vectors": total_vectors,
                        "content_type_counts": content_type_counts,
                        "namespace": self.namespace,
                        "dimension": 512,
                        "device": self.device,
                        "table_size": table_size,
                        "database_type": "PostgreSQL + pgvector",
                        "models": {
                            "text_embeddings": "text-embedding-3-small" if self.text_embeddings else None,
                            "clip_model": "ViT-B/32" if self.clip_model else None
                        }
                    }
                    
            finally:
                self.pool.putconn(conn)
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"status": "error", "error": str(e)}
    
    def health_check(self) -> bool:
        """Check if the vector DB is healthy (MCP compatible)."""
        try:
            if not self.pool:
                return False
            
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cur:
                    # Test basic query
                    cur.execute("SELECT 1;")
                    result = cur.fetchone()
                    
                    # Test vector operations
                    cur.execute("SELECT '[1,2,3]'::vector <=> '[1,2,4]'::vector;")
                    similarity = cur.fetchone()[0]
                    
                    return result[0] == 1 and isinstance(similarity, float)
                    
            finally:
                self.pool.putconn(conn)
            
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False
    
    def clear_namespace(self, namespace: Optional[str] = None) -> bool:
        """Clear all vectors in a namespace (useful for testing)."""
        try:
            if not self.pool:
                return False
            
            target_namespace = namespace or self.namespace
            
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM embeddings WHERE namespace = %s;", (target_namespace,))
                    deleted_count = cur.rowcount
                    conn.commit()
                    
                    logger.info(f"Cleared {deleted_count} vectors from namespace: {target_namespace}")
                    return True
                    
            finally:
                self.pool.putconn(conn)
            
        except Exception as e:
            logger.error(f"Failed to clear namespace: {e}")
            return False
    
    def close(self):
        """Close database connections."""
        if self.pool:
            self.pool.closeall()
            logger.info("Closed PostgreSQL connection pool")

# Global instance will be created by the factory when needed
postgres_vector_db = None