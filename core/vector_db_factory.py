# core/vector_db_factory.py

"""
Factory pattern for vector database implementations.
Allows easy switching between PostgreSQL and Pinecone backends.
"""

import os
import logging
from typing import Optional, Union
from enum import Enum
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

logger = logging.getLogger(__name__)

class VectorDBType(Enum):
    """Supported vector database types."""
    POSTGRESQL = "postgresql"
    PINECONE = "pinecone"
    MOCK = "mock"  # Mock database for testing and fallback
    AUTO = "auto"  # Automatically detect based on environment

class VectorDBFactory:
    """Factory for creating vector database instances."""
    
    @staticmethod
    def create_vector_db(
        db_type: Union[VectorDBType, str] = VectorDBType.AUTO,
        namespace: str = "agentic-memory"
    ):
        """
        Create a vector database instance based on type and environment.
        
        Args:
            db_type: Type of vector database to create
            namespace: Namespace for the vector database
            
        Returns:
            Vector database instance
        """
        if isinstance(db_type, str):
            db_type = VectorDBType(db_type.lower())
        
        # Auto-detect based on environment variables
        if db_type == VectorDBType.AUTO:
            db_type = VectorDBFactory._auto_detect_db_type()
        
        if db_type == VectorDBType.POSTGRESQL:
            return VectorDBFactory._create_postgresql_db(namespace)
        elif db_type == VectorDBType.PINECONE:
            return VectorDBFactory._create_pinecone_db(namespace)
        elif db_type == VectorDBType.MOCK:
            return VectorDBFactory._create_mock_db(namespace)
        else:
            raise ValueError(f"Unsupported vector database type: {db_type}")
    
    @staticmethod
    def _auto_detect_db_type() -> VectorDBType:
        """Auto-detect which vector database to use based on environment and availability."""
        
        # Force reload environment variables
        load_dotenv(override=True)
        
        # Check for PostgreSQL configuration AND dependencies
        database_url = os.getenv("DATABASE_URL")
        postgres_configured = database_url and "postgresql" in database_url.lower()
        
        # Check if PostgreSQL dependencies are available
        postgres_deps_available = VectorDBFactory._check_postgresql_deps()
        postgres_available = postgres_configured and postgres_deps_available
        
        # Check for Pinecone configuration
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        pinecone_available = bool(pinecone_api_key)
        
        # Debug logging
        logger.info(f"DATABASE_URL found: {bool(database_url)}")
        logger.info(f"PostgreSQL configured: {postgres_configured}")
        logger.info(f"PostgreSQL deps available: {postgres_deps_available}")
        logger.info(f"Pinecone available: {pinecone_available}")
        
        # Preference order: PostgreSQL first (cost-effective), then Pinecone, then Mock
        if postgres_available:
            logger.info("Auto-detected PostgreSQL vector database")
            return VectorDBType.POSTGRESQL
        elif pinecone_available:
            logger.info("Auto-detected Pinecone vector database")
            return VectorDBType.PINECONE
        else:
            # Fall back to mock database
            logger.info(f"No vector database available, using mock database (DB_URL: {database_url}, deps: {postgres_deps_available})")
            return VectorDBType.MOCK
    
    @staticmethod
    def _check_postgresql_deps() -> bool:
        """Check if PostgreSQL dependencies are available."""
        try:
            import psycopg2
            return True
        except ImportError:
            return False
    
    @staticmethod
    def _create_postgresql_db(namespace: str):
        """Create PostgreSQL vector database instance."""
        try:
            from core.postgres_vector_db import PostgreSQLVectorDB
            return PostgreSQLVectorDB(namespace=namespace)
        except ImportError as e:
            logger.error(f"Failed to import PostgreSQL vector DB: {e}")
            raise ImportError("PostgreSQL dependencies not installed. Run: pip install psycopg2-binary pgvector")
    
    @staticmethod
    def _create_pinecone_db(namespace: str):
        """Create Pinecone vector database instance."""
        try:
            from core.vector_db import UnifiedVectorDB
            return UnifiedVectorDB(namespace=namespace)
        except ImportError as e:
            logger.error(f"Failed to import Pinecone vector DB: {e}")
            raise ImportError("Pinecone dependencies not installed. Run: pip install pinecone-client")
    
    @staticmethod
    def _create_mock_db(namespace: str):
        """Create mock vector database instance."""
        try:
            from core.mock_vector_db import MockVectorDB
            return MockVectorDB(namespace=namespace)
        except ImportError as e:
            logger.error(f"Failed to import mock vector DB: {e}")
            raise ImportError("Mock vector database not available")
    
    @staticmethod
    def get_available_databases() -> dict:
        """Get information about available vector databases."""
        info = {
            "postgresql": {
                "available": False,
                "reason": None,
                "config_required": ["DATABASE_URL or local PostgreSQL"]
            },
            "pinecone": {
                "available": False,
                "reason": None,
                "config_required": ["PINECONE_API_KEY"]
            },
            "mock": {
                "available": True,
                "reason": "Always available for testing and fallback",
                "config_required": []
            }
        }
        
        # Check PostgreSQL
        try:
            from core.postgres_vector_db import PostgreSQLVectorDB
            database_url = os.getenv("DATABASE_URL", "postgresql://localhost:5432/agentic_vectors")
            if database_url:
                info["postgresql"]["available"] = True
                info["postgresql"]["config"] = database_url.split("@")[1] if "@" in database_url else "Local"
            else:
                info["postgresql"]["reason"] = "No DATABASE_URL configured"
        except ImportError:
            info["postgresql"]["reason"] = "Dependencies not installed (psycopg2-binary, pgvector)"
        except Exception as e:
            info["postgresql"]["reason"] = f"Configuration error: {e}"
        
        # Check Pinecone
        try:
            from core.vector_db import UnifiedVectorDB
            pinecone_api_key = os.getenv("PINECONE_API_KEY")
            if pinecone_api_key:
                info["pinecone"]["available"] = True
                info["pinecone"]["config"] = f"API key configured"
            else:
                info["pinecone"]["reason"] = "No PINECONE_API_KEY configured"
        except ImportError:
            info["pinecone"]["reason"] = "Dependencies not installed (pinecone-client)"
        except Exception as e:
            info["pinecone"]["reason"] = f"Configuration error: {e}"
        
        return info

# Global factory instance
vector_db_factory = VectorDBFactory()

# Function to reinitialize the default vector database
def reinitialize_default_vector_db():
    """Reinitialize the default vector database with current environment."""
    global default_vector_db
    try:
        default_vector_db = vector_db_factory.create_vector_db()
        logger.info(f"Reinitialized default vector database: {type(default_vector_db).__name__}")
        return default_vector_db
    except Exception as e:
        logger.error(f"Failed to reinitialize default vector database: {e}")
        return None

# Create the default vector database instance
try:
    default_vector_db = vector_db_factory.create_vector_db()
    logger.info(f"Initialized default vector database: {type(default_vector_db).__name__}")
except Exception as e:
    logger.error(f"Failed to initialize default vector database: {e}")
    default_vector_db = None