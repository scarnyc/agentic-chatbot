# tools/unified_multimodal_tools.py

"""
Unified multimodal tools that automatically use the best available vector database.
This provides a single interface that works with either PostgreSQL or Pinecone.
"""

import base64
import io
import logging
from typing import Dict, List, Optional, Any
from langchain.tools import tool

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from core.vector_db_factory import default_vector_db, vector_db_factory

logger = logging.getLogger(__name__)

@tool
def store_text_memory(
    content: str,
    category: str = "general",
    metadata: str = "{}"
) -> str:
    """
    Store text content in the vector database for long-term memory.
    Automatically uses the best available vector database (PostgreSQL or Pinecone).
    
    Args:
        content: The text content to store
        category: Category of the content (e.g., "fact", "preference", "conversation")
        metadata: JSON string with additional metadata
    
    Returns:
        str: Success or error message
    
    Use this tool to:
    - Store important facts or information for future reference
    - Save user preferences and learned behaviors
    - Archive significant conversation insights
    - Build long-term memory for better context
    """
    try:
        if not default_vector_db:
            return "Vector database not available. Check configuration (DATABASE_URL or PINECONE_API_KEY)."
        
        import json
        metadata_dict = json.loads(metadata) if metadata != "{}" else {}
        
        success = default_vector_db.store_text_memory(
            content=content,
            category=category,
            metadata=metadata_dict
        )
        
        if success:
            api_logger = logging.getLogger('api_calls')
            db_type = type(default_vector_db).__name__
            api_logger.info(f"Stored text in {db_type}: category={category}, content_length={len(content)}")
            return f"Successfully stored text content in vector database (category: {category})"
        else:
            return "Failed to store text content - vector database error"
            
    except Exception as e:
        error_msg = f"Error storing text in vector database: {str(e)}"
        logger.error(error_msg)
        return error_msg

@tool
def store_image_memory(
    image_base64: str,
    description: str,
    metadata: str = "{}"
) -> str:
    """
    Store an image with description in the vector database for multimodal memory.
    Automatically uses the best available vector database (PostgreSQL or Pinecone).
    
    Args:
        image_base64: Base64 encoded image data
        description: Text description of the image content
        metadata: JSON string with additional metadata
    
    Returns:
        str: Success or error message
    
    Use this tool to:
    - Store important visual information
    - Save screenshots, diagrams, or charts for future reference
    - Build visual memory alongside textual memory
    - Enable image-based retrieval and search
    """
    try:
        if not default_vector_db:
            return "Vector database not available. Check configuration (DATABASE_URL or PINECONE_API_KEY)."
        
        import json
        metadata_dict = json.loads(metadata) if metadata != "{}" else {}
        
        # Validate image data
        if HAS_PIL:
            try:
                image_bytes = base64.b64decode(image_base64)
                image = Image.open(io.BytesIO(image_bytes))
                image.verify()  # Check if image is valid
            except Exception as e:
                return f"Invalid image data: {str(e)}"
        else:
            try:
                image_bytes = base64.b64decode(image_base64)
            except Exception as e:
                return f"Invalid base64 image data: {str(e)}"
        
        success = default_vector_db.store_image_memory(
            image_data=image_base64,
            description=description,
            metadata=metadata_dict
        )
        
        if success:
            api_logger = logging.getLogger('api_calls')
            db_type = type(default_vector_db).__name__
            api_logger.info(f"Stored image in {db_type}: description_length={len(description)}")
            return f"Successfully stored image in vector database with description: {description[:100]}..."
        else:
            return "Failed to store image - vector database error"
            
    except Exception as e:
        error_msg = f"Error storing image in vector database: {str(e)}"
        logger.error(error_msg)
        return error_msg

@tool
def search_memories(
    query: str,
    query_type: str = "text",
    limit: int = 5,
    category_filter: str = ""
) -> str:
    """
    Search the vector database for relevant content using semantic similarity.
    Automatically uses the best available vector database (PostgreSQL or Pinecone).
    
    Args:
        query: Search query text
        query_type: Type of search ("text" or "multimodal")
        limit: Maximum number of results to return (1-20)
        category_filter: Optional category to filter results
    
    Returns:
        str: Formatted search results or error message
    
    Use this tool to:
    - Find relevant past conversations or facts
    - Retrieve visual content by text description
    - Access stored knowledge for better responses
    - Provide context from long-term memory
    """
    try:
        if not default_vector_db:
            return "Vector database not available. Check configuration (DATABASE_URL or PINECONE_API_KEY)."
        
        # Validate inputs
        limit = max(1, min(20, limit))
        if query_type not in ["text", "multimodal"]:
            query_type = "text"
        
        # Build filter
        filter_metadata = {}
        if category_filter:
            filter_metadata["category"] = category_filter
        
        results = default_vector_db.search_memories(
            query=query,
            query_type=query_type,
            limit=limit,
            filter_metadata=filter_metadata if filter_metadata else None
        )
        
        if not results:
            return "No relevant memories found in vector database."
        
        # Format results
        formatted_results = []
        for i, result in enumerate(results, 1):
            content_preview = result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"]
            
            result_text = f"{i}. **{result['content_type'].title()} Memory** (Score: {result['score']:.3f})\n"
            result_text += f"   Content: {content_preview}\n"
            
            # Add metadata info
            metadata = result.get("metadata", {})
            if metadata:
                metadata_items = []
                for key, value in metadata.items():
                    if key not in ["timestamp"]:  # Skip timestamp for brevity
                        metadata_items.append(f"{key}: {value}")
                if metadata_items:
                    result_text += f"   Metadata: {', '.join(metadata_items)}\n"
            
            # Note if image is attached
            if result.get("image_data"):
                result_text += f"   📷 Contains image data\n"
            
            formatted_results.append(result_text)
        
        api_logger = logging.getLogger('api_calls')
        db_type = type(default_vector_db).__name__
        api_logger.info(f"{db_type} search: query='{query[:50]}...', results={len(results)}")
        
        response = f"Found {len(results)} relevant memories:\n\n" + "\n".join(formatted_results)
        return response
        
    except Exception as e:
        error_msg = f"Error searching vector database: {str(e)}"
        logger.error(error_msg)
        return error_msg

@tool
def get_vector_db_info() -> str:
    """
    Get information about the current vector database configuration and available options.
    
    Returns:
        str: Database information and status
    
    Use this tool to:
    - Check which vector database is currently active
    - See available database options
    - Monitor system health
    - Debug configuration issues
    """
    try:
        # Get information about available databases
        available_dbs = vector_db_factory.get_available_databases()
        
        # Current database info
        if default_vector_db:
            current_stats = default_vector_db.get_stats()
            current_db_name = type(default_vector_db).__name__
            health_status = "healthy" if default_vector_db.health_check() else "unhealthy"
        else:
            current_stats = {"status": "not_initialized"}
            current_db_name = "None"
            health_status = "not_available"
        
        response = f"""Vector Database Configuration:

🎯 **Currently Active**: {current_db_name}
📊 **Status**: {current_stats.get('status', 'unknown').title()}
💚 **Health**: {health_status.title()}

📈 **Current Database Stats**:
"""
        
        if default_vector_db and current_stats.get("status") == "connected":
            response += f"""- Total Vectors: {current_stats.get('total_vectors', 0):,}
- Namespace: {current_stats.get('namespace', 'default')}
- Database Type: {current_stats.get('database_type', current_db_name)}
"""
            if current_stats.get('table_size'):
                response += f"- Storage Size: {current_stats.get('table_size')}\n"
        else:
            response += "- No active database connection\n"
        
        response += f"""
🔧 **Available Databases**:

**PostgreSQL**:
- Available: {'✅ Yes' if available_dbs['postgresql']['available'] else '❌ No'}
"""
        
        if available_dbs['postgresql']['available']:
            response += f"- Configuration: {available_dbs['postgresql'].get('config', 'Local')}\n"
        else:
            response += f"- Issue: {available_dbs['postgresql']['reason']}\n"
        
        response += f"""
**Pinecone**:
- Available: {'✅ Yes' if available_dbs['pinecone']['available'] else '❌ No'}
"""
        
        if available_dbs['pinecone']['available']:
            response += f"- Configuration: {available_dbs['pinecone'].get('config', 'Configured')}\n"
        else:
            response += f"- Issue: {available_dbs['pinecone']['reason']}\n"
        
        response += """
💡 **Setup Instructions**:
- PostgreSQL: Set DATABASE_URL environment variable
- Pinecone: Set PINECONE_API_KEY environment variable
- Auto-detection prioritizes PostgreSQL (cost-effective) over Pinecone
"""
        
        api_logger = logging.getLogger('api_calls')
        api_logger.info(f"Vector DB info requested: active={current_db_name}")
        
        return response
        
    except Exception as e:
        error_msg = f"Error getting vector database info: {str(e)}"
        logger.error(error_msg)
        return error_msg

@tool
def analyze_image_and_store(
    image_base64: str,
    analysis_request: str = "Analyze this image and describe what you see",
    store_in_memory: bool = True,
    category: str = "visual_analysis"
) -> str:
    """
    Analyze an image using Claude's vision capabilities and optionally store in vector database.
    Automatically uses the best available vector database (PostgreSQL or Pinecone).
    
    Args:
        image_base64: Base64 encoded image data
        analysis_request: What to analyze about the image
        store_in_memory: Whether to store the analysis in vector database
        category: Category for storage if store_in_memory is True
    
    Returns:
        str: Analysis results and storage confirmation
    
    Use this tool to:
    - Understand visual content in conversations
    - Extract information from images, charts, diagrams
    - Build visual memory for future reference
    - Combine image analysis with searchable storage
    """
    try:
        analysis = f"Image analysis requested: {analysis_request}\n"
        analysis += "📷 Image received and processed.\n"
        
        # Validate image
        if HAS_PIL:
            try:
                image_bytes = base64.b64decode(image_base64)
                image = Image.open(io.BytesIO(image_bytes))
                width, height = image.size
                format_type = image.format
                analysis += f"📐 Image dimensions: {width}x{height}, Format: {format_type}\n"
            except Exception as e:
                return f"Invalid image data: {str(e)}"
        else:
            try:
                image_bytes = base64.b64decode(image_base64)
                analysis += f"📐 Image validated: {len(image_bytes)} bytes\n"
            except Exception as e:
                return f"Invalid base64 image data: {str(e)}"
        
        # TODO: Integrate with Claude vision API when available in LangChain
        analysis += "\n🔧 **Note**: Full Claude vision integration pending LangChain support.\n"
        analysis += "Currently processing image metadata and preparing for analysis.\n"
        
        # Store in vector database if requested
        if store_in_memory and default_vector_db:
            description = f"Image analysis: {analysis_request} - {format_type} image ({width}x{height})"
            success = default_vector_db.store_image_memory(
                image_data=image_base64,
                description=description,
                metadata={"category": category, "analysis_type": analysis_request}
            )
            
            if success:
                db_type = type(default_vector_db).__name__
                analysis += f"\n✅ Image and analysis stored in {db_type} vector database (category: {category})"
            else:
                analysis += "\n❌ Failed to store in vector database"
        elif store_in_memory and not default_vector_db:
            analysis += "\n⚠️ Vector database not available for storage"
        
        api_logger = logging.getLogger('api_calls')
        api_logger.info(f"Image analysis requested: {width}x{height} {format_type}, store={store_in_memory}")
        
        return analysis
        
    except Exception as e:
        error_msg = f"Error analyzing image: {str(e)}"
        logger.error(error_msg)
        return error_msg