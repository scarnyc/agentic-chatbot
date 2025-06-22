"""
Python-based agentic workflow powered by Anthropic & LangGraph.
This agent is capable of using Tavily web search, and executing code;
It also has access to Wikipedia info while incorporating memory.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio
import logging
import base64
import io
import os
from anthropic import Anthropic

# Handle PIL import gracefully
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Warning: PIL (Pillow) not available. Image processing will be limited.")
from core.app import langgraph_app, process_conversation_for_memory, get_memory_stats # Assuming core.app contains your LangGraph setup
from core.cache import get_cache_stats, clear_cache
from core.error_recovery import get_error_recovery_stats

# Reinitialize vector database after environment is loaded
from core.vector_db_factory import reinitialize_default_vector_db
reinitialize_default_vector_db()

# Initialize logging
from core.logging_config import setup_logging, get_logger

# Set up comprehensive logging
loggers = setup_logging(log_level=logging.INFO)
logger = get_logger(__name__)
websocket_logger = get_logger('websocket')

# Initialize FastAPI
app = FastAPI(title="AI by Design Copilot")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        
    def register_connection(self, websocket: WebSocket, client_id: str):
        self.active_connections[client_id] = websocket
        
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Disconnected and removed client: {client_id}")
        else:
            logger.warning(f"Attempted to disconnect unknown client: {client_id}")

manager = ConnectionManager()

# Models
class Message(BaseModel):
    content: str
    role: str = "user"
    
class Conversation(BaseModel):
    id: str = None
    messages: List[Dict[str, Any]] = []

conversations: Dict[str, Conversation] = {}

@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/conversations")
async def create_conversation():
    conversation_id = str(uuid.uuid4())
    conversations[conversation_id] = Conversation(id=conversation_id)
    logger.info(f"Created new conversation: {conversation_id}")
    return {"conversation_id": conversation_id}

@app.get("/api/cache/stats")
async def get_cache_statistics():
    """Get cache statistics."""
    return JSONResponse(content=get_cache_stats())

@app.post("/api/cache/clear")
async def clear_cache_endpoint():
    """Clear all cache entries."""
    clear_cache()
    return JSONResponse(content={"message": "Cache cleared successfully"})

@app.get("/api/health")
async def health_check():
    """Health check endpoint with cache, error recovery, and memory stats."""
    cache_stats = get_cache_stats()
    error_stats = get_error_recovery_stats()
    memory_stats = get_memory_stats()
    return JSONResponse(content={
        "status": "healthy",
        "cache": cache_stats,
        "error_recovery": error_stats,
        "memory": memory_stats,
        "active_conversations": len(conversations)
    })

@app.get("/api/error-recovery/stats")
async def get_error_recovery_statistics():
    """Get error recovery statistics."""
    return JSONResponse(content=get_error_recovery_stats())

@app.get("/api/memory/stats")
async def get_memory_statistics():
    """Get long-term memory statistics."""
    return JSONResponse(content=get_memory_stats())

@app.post("/api/memory/process/{conversation_id}")
async def process_conversation_memory(conversation_id: str):
    """Manually process a conversation for memory extraction."""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Convert conversation messages to proper format for memory processing
    messages = []
    for msg in conversations[conversation_id].messages:
        if msg["role"] == "user":
            messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            messages.append({"role": "assistant", "content": msg["content"]})
    
    # Process for memory
    process_conversation_for_memory(messages, conversation_id)
    
    return JSONResponse(content={
        "message": "Conversation processed for memory extraction",
        "conversation_id": conversation_id,
        "message_count": len(messages)
    })

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    message: Optional[str] = Form(None),
    conversation_id: str = Form(...)
):
    """Handle file upload and analysis."""
    try:
        # Validate conversation exists
        if conversation_id not in conversations:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Validate file type
        allowed_types = {
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf'
        }
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file type. Please upload an image (JPEG, PNG, GIF, WebP) or PDF."
            )
        
        # Validate file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail="File size must be less than 10MB")
        
        # Process the file based on type
        if file.content_type.startswith('image/'):
            analysis = await process_image_file(file_content, file.filename, message)
        elif file.content_type == 'application/pdf':
            analysis = await process_pdf_file(file_content, file.filename, message)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        # Add the analysis to conversation history
        user_message = message or f"Please analyze this file: {file.filename}"
        conversations[conversation_id].messages.append({
            "role": "user", 
            "content": user_message
        })
        conversations[conversation_id].messages.append({
            "role": "assistant",
            "content": analysis
        })
        
        logger.info(f"File processed successfully: {file.filename} for conversation {conversation_id}")
        
        return JSONResponse(content={
            "analysis": analysis,
            "filename": file.filename,
            "file_type": file.content_type
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@app.post("/api/batch-upload")
async def batch_upload_files(
    directory_path: str = Form(...),
    conversation_id: str = Form(...)
):
    """Handle batch upload and processing of files from a directory."""
    try:
        # Validate conversation exists
        if conversation_id not in conversations:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Validate directory exists
        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            raise HTTPException(status_code=400, detail="Directory path does not exist or is not a directory")
        
        # Find all supported files in directory
        supported_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf'}
        files_found = []
        
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            if (os.path.isfile(file_path) and 
                any(filename.lower().endswith(ext) for ext in supported_extensions)):
                files_found.append((filename, file_path))
        
        if not files_found:
            raise HTTPException(
                status_code=400, 
                detail="No supported files found in directory (supported: JPG, PNG, GIF, WebP, PDF)"
            )
        
        # Create output directory
        output_dir = os.path.join(directory_path, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Process files in batch
        processed_files = []
        errors = []
        
        for filename, file_path in files_found:
            try:
                # Read file content
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                # Validate file size (10MB limit)
                max_size = 10 * 1024 * 1024  # 10MB
                if len(file_content) > max_size:
                    errors.append(f"{filename}: File size too large (>10MB)")
                    continue
                
                # Determine file type
                file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
                
                if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    analysis = await process_image_file(file_content, filename, f"Analyze this image: {filename}")
                elif file_extension == 'pdf':
                    analysis = await process_pdf_file(file_content, filename, f"Analyze this PDF: {filename}")
                else:
                    errors.append(f"{filename}: Unsupported file type")
                    continue
                
                # Write analysis to text file
                base_name = os.path.splitext(filename)[0]
                output_filename = f"{base_name}_analysis.txt"
                output_path = os.path.join(output_dir, output_filename)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(analysis)
                
                processed_files.append({
                    "original_filename": filename,
                    "output_filename": output_filename,
                    "output_path": output_path,
                    "analysis": analysis
                })
                
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")
        
        if not processed_files:
            raise HTTPException(
                status_code=500, 
                detail=f"No files were processed successfully. Errors: {'; '.join(errors)}"
            )
        
        # Add batch processing message to conversation
        batch_message = f"Batch process {len(files_found)} files from directory: {directory_path}"
        success_message = f"SUCCESS! Processed {len(processed_files)} files. Output saved to: {output_dir}"
        
        if errors:
            success_message += f"\n\nErrors encountered: {'; '.join(errors)}"
        
        # Show example of one analysis
        example_analysis = processed_files[0]["analysis"] if processed_files else "No successful analyses"
        success_message += f"\n\nExample analysis ({processed_files[0]['original_filename']}):\n{example_analysis[:500]}..."
        
        conversations[conversation_id].messages.append({
            "role": "user", 
            "content": batch_message
        })
        conversations[conversation_id].messages.append({
            "role": "assistant",
            "content": success_message
        })
        
        logger.info(f"Batch processed {len(processed_files)} files from {directory_path}")
        
        return JSONResponse(content={
            "message": "SUCCESS!",
            "processed_count": len(processed_files),
            "total_files": len(files_found),
            "output_directory": output_dir,
            "processed_files": [f["original_filename"] for f in processed_files],
            "errors": errors,
            "example_analysis": example_analysis
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process batch upload: {str(e)}")

async def process_image_file(file_content: bytes, filename: str, user_message: Optional[str]) -> str:
    """Process uploaded image file using direct Anthropic Vision API."""
    try:
        # Convert image to base64
        image_base64 = base64.b64encode(file_content).decode('utf-8')
        
        # Get image format for the API
        file_extension = filename.lower().split('.')[-1] if '.' in filename else 'unknown'
        media_type_map = {
            'png': 'image/png',
            'jpg': 'image/jpeg', 
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'webp': 'image/webp'
        }
        media_type = media_type_map.get(file_extension, 'image/png')
        
        # Create analysis request
        analysis_request = user_message or "Analyze this image and describe what you see in detail"
        
        # Use direct Anthropic Vision API
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",  # Same model as the rest of the app
            max_tokens=1000,
            messages=[{
                "role": "user", 
                "content": [
                    {"type": "text", "text": analysis_request},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_base64
                        }
                    }
                ]
            }]
        )
        
        # Extract the analysis from the response
        analysis_text = response.content[0].text
        
        # Get file info for storage
        file_size_mb = len(file_content) / (1024 * 1024)
        
        # Format the response nicely
        formatted_response = f"""🖼️ **Image Analysis: {filename}**

📊 **File Information:**
- File name: {filename}
- File size: {file_size_mb:.2f} MB
- Format: {file_extension.upper()}

🔍 **Claude's Analysis:**
{analysis_text}

✅ **Analysis complete** - Image processed using Claude 4 Sonnet vision capabilities."""

        # Store in vector database for memory
        from tools.unified_multimodal_tools import store_text_memory, store_image_memory
        
        # Store the image and analysis
        store_image_memory.invoke({
            "image_base64": image_base64,
            "description": f"Image analysis: {analysis_text[:200]}...",
            "metadata": f'{{"filename": "{filename}", "analysis_request": "{analysis_request}", "size_mb": {file_size_mb:.2f}}}'
        })
        
        # Also store the full analysis as text
        store_text_memory.invoke({
            "content": f"Image analysis for {filename}: {analysis_text}",
            "category": "image_analysis",
            "metadata": f'{{"filename": "{filename}", "type": "vision_analysis"}}'
        })
        
        logger.info(f"Image analyzed successfully with Claude Vision: {filename}")
        return formatted_response
        
    except Exception as e:
        logger.error(f"Image processing error: {e}")
        
        # Fallback error message
        file_size_mb = len(file_content) / (1024 * 1024) if file_content else 0
        return f"""🖼️ **Image Upload: {filename}**

❌ **Analysis Error:** {str(e)}

📊 **File Information:**
- File name: {filename}
- File size: {file_size_mb:.2f} MB

💡 **The image was uploaded successfully, but vision analysis failed. This could be due to:**
- API key issues
- Network connectivity
- Unsupported image format
- File corruption

Please try uploading again or check the server logs for more details."""

async def process_pdf_file(file_content: bytes, filename: str, user_message: Optional[str]) -> str:
    """Process uploaded PDF file using Anthropic's native PDF support."""
    try:
        # Convert PDF to base64
        pdf_base64 = base64.b64encode(file_content).decode('utf-8')
        
        # Get file size for info
        file_size_mb = len(file_content) / (1024 * 1024)
        
        # Validate file size (Anthropic has limits)
        max_size_mb = 32  # Anthropic's PDF limit is 32MB
        if file_size_mb > max_size_mb:
            return f"""📄 **PDF File: {filename}**

❌ **File Too Large:** {file_size_mb:.2f} MB

The PDF file is too large for direct analysis. Anthropic supports PDFs up to {max_size_mb}MB.

🔧 **Suggestions:**
- Compress the PDF to reduce file size
- Split large PDFs into smaller sections
- Extract key pages and upload them separately
- Copy and paste specific text sections you want analyzed

Would you like help with PDF compression or other alternatives?"""
        
        # Create analysis request
        analysis_request = user_message or "Analyze this PDF document. Summarize the content, extract key information, and identify main topics."
        
        # Use direct Anthropic API with PDF support
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",  # Same model as the rest of the app
            max_tokens=2000,  # More tokens for PDF analysis
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": analysis_request},
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_base64
                        }
                    }
                ]
            }]
        )
        
        # Extract the analysis from the response
        analysis_text = response.content[0].text
        
        # Format the response nicely
        formatted_response = f"""📄 **PDF Analysis: {filename}**

📊 **File Information:**
- File name: {filename}
- File size: {file_size_mb:.2f} MB
- Type: PDF document

🔍 **Claude's Analysis:**
{analysis_text}

✅ **Analysis complete** - PDF processed using Claude 4 Sonnet's native PDF capabilities."""

        # Store in vector database for memory
        from tools.unified_multimodal_tools import store_text_memory
        
        # Store the PDF analysis
        store_text_memory.invoke({
            "content": f"PDF analysis for {filename}: {analysis_text}",
            "category": "pdf_analysis",
            "metadata": f'{{"filename": "{filename}", "type": "pdf_analysis", "size_mb": {file_size_mb:.2f}, "analysis_request": "{analysis_request}"}}'
        })
        
        # Also store a summary for quick reference
        summary = analysis_text[:300] + "..." if len(analysis_text) > 300 else analysis_text
        store_text_memory.invoke({
            "content": f"PDF document {filename} contains: {summary}",
            "category": "uploaded_file",
            "metadata": f'{{"filename": "{filename}", "type": "pdf", "size_mb": {file_size_mb:.2f}}}'
        })
        
        logger.info(f"PDF analyzed successfully with Claude: {filename} ({file_size_mb:.2f} MB)")
        return formatted_response
        
    except Exception as e:
        logger.error(f"PDF processing error: {e}")
        
        # Fallback error message
        file_size_mb = len(file_content) / (1024 * 1024) if file_content else 0
        return f"""📄 **PDF Upload: {filename}**

❌ **Analysis Error:** {str(e)}

📊 **File Information:**
- File name: {filename}
- File size: {file_size_mb:.2f} MB

💡 **The PDF was uploaded successfully, but analysis failed. This could be due to:**
- PDF contains only scanned images (try OCR first)
- Corrupted or password-protected PDF
- Network connectivity issues
- API limitations

🔧 **Alternative approaches:**
- Try converting PDF to text and pasting directly
- Upload individual pages as images
- Use a PDF text extraction tool first

Please try again or contact support if the issue persists."""

def is_obviously_raw_data(text: str) -> bool:
    """
    Conservative check for obviously raw data that should not be shown to users.
    Only blocks very obvious cases to avoid false positives.
    """
    if not isinstance(text, str):
        return True
    
    stripped_text = text.strip()
    if not stripped_text:
        return False
    
    # Check for exact "[object Object]" matches
    if stripped_text == "[object Object]" or "[object Object]" in stripped_text:
        return True
    
    # Check for obvious JSON structure (starts and ends with braces/brackets + has multiple quotes/colons)
    if ((stripped_text.startswith("{") and stripped_text.endswith("}")) or 
        (stripped_text.startswith("[") and stripped_text.endswith("]"))):
        # Only flag if it has lots of JSON-like syntax
        if stripped_text.count('"') > 10 and stripped_text.count(':') > 5 and stripped_text.count(',') > 5:
            return True
    
    return False

def is_problematic_content(text: str) -> bool:
    """
    Heuristically checks if the text is a raw data structure or common placeholder.
    """
    if not isinstance(text, str):
        return True # Non-strings are problematic by definition here
    
    stripped_text = text.strip()
    if not stripped_text: # Empty strings are not problematic, just empty
        return False

    # Check for common object/array string representations
    if stripped_text == "[object Object]" or "[object Object]" in stripped_text:
        return True
    
    # Check for patterns that look like stringified JSON objects/arrays from tool outputs
    if (stripped_text.startswith("{") and stripped_text.endswith("}")) or \
       (stripped_text.startswith("[") and stripped_text.endswith("]")):
        # More specific checks for the kind of content seen in the screenshot
        if '"title":' in stripped_text and '"url":' in stripped_text and '"content":' in stripped_text:
            logger.warning(f"Identified problematic JSON-like string: {stripped_text[:150]}...")
            return True
        if "Weather in Queens" in stripped_text and "weatherapi.com" in stripped_text:
             logger.warning(f"Identified problematic weather API string: {stripped_text[:150]}...")
             return True
        # Check for other JSON-like patterns that suggest raw tool output
        # Be more conservative - only flag obvious JSON structures
        if (stripped_text.count('"') > 6 and stripped_text.count(':') > 3 and stripped_text.count(',') > 5) or \
           (stripped_text.count(',') > 8 and ('{' in stripped_text or '[' in stripped_text)):
            logger.warning(f"Identified potential raw tool output: {stripped_text[:150]}...")
            return True
             
    # Check for common raw data patterns
    if stripped_text.startswith('{"') or stripped_text.startswith('[{'):
        return True
        
    # Check for multiple object references
    if stripped_text.count('[object Object]') > 1:
        return True
    
    return False

@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    await websocket.accept() 

    if conversation_id not in conversations:
        websocket_logger.warning(f"WebSocket for conversation_id '{conversation_id}' accepted, but ID not found. Closing.")
        await websocket.close(code=1008) 
        return

    manager.register_connection(websocket, conversation_id)
    websocket_logger.info(f"WebSocket registered for conversation: {conversation_id}")
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                
                if payload.get("type") == "message":
                    message_content = payload.get("content", "")
                    if not isinstance(message_content, str): 
                        websocket_logger.warning("Received non-string message content from client.")
                        message_content = str(message_content)

                    websocket_logger.info(f"Received message from client ({conversation_id}): {message_content[:100]}...")
                    
                    conversations[conversation_id].messages.append({
                        "role": "user",
                        "content": message_content
                    })
                    
                    async def process_and_stream():
                        config = {"configurable": {"thread_id": conversation_id}}
                        langgraph_input = {"messages": [("user", message_content)]}
                        accumulated_response_content = ""
                        has_sent_chunks = False
                        
                        try:
                            logger.info(f"Streaming response for ({conversation_id}): {message_content[:100]}...")
                            current_node = None
                            
                            async for event in langgraph_app.astream(langgraph_input, config):
                                for key, value in event.items():
                                    # Track node transitions for typing indicators
                                    if key != current_node:
                                        current_node = key
                                        
                                        # Send typing indicators based on node transitions
                                        if key == "tools":
                                            await websocket.send_text(json.dumps({
                                                "type": "tool_start",
                                                "tool_name": "processing"
                                            }))
                                        elif key == "chatbot" and current_node == "tools":
                                            await websocket.send_text(json.dumps({
                                                "type": "tool_end"
                                            }))
                                    
                                    # Check for thinking content in the event (for future LangChain support)
                                    if isinstance(value, dict) and "thinking" in value:
                                        thinking_content = value["thinking"]
                                        # Send thinking content to UI
                                        await websocket.send_text(json.dumps({
                                            "type": "thinking",
                                            "content": thinking_content
                                        }))
                                        websocket_logger.info(f"Sent thinking content from event: {len(thinking_content)} characters")
                                    
                                    if isinstance(value, dict) and "messages" in value:
                                        for msg_obj in value["messages"]:
                                            # Check if this message has tool calls to detect specific tools
                                            if (hasattr(msg_obj, 'tool_calls') and msg_obj.tool_calls and 
                                                key == "chatbot"):
                                                for tool_call in msg_obj.tool_calls:
                                                    tool_name = tool_call.get('name', 'unknown')
                                                    await websocket.send_text(json.dumps({
                                                        "type": "tool_start",
                                                        "tool_name": tool_name
                                                    }))
                                            
                                            # Check if this is an AI message (LangChain AIMessage)
                                            if (hasattr(msg_obj, 'content') and 
                                                (str(type(msg_obj)).find('AIMessage') != -1 or 
                                                 (hasattr(msg_obj, 'type') and str(msg_obj.type) == 'ai'))):
                                                
                                                # Check for thinking content in message additional_kwargs (for future LangChain support)
                                                if (hasattr(msg_obj, 'additional_kwargs') and 
                                                    'thinking' in msg_obj.additional_kwargs):
                                                    thinking_content = msg_obj.additional_kwargs['thinking']
                                                    await websocket.send_text(json.dumps({
                                                        "type": "thinking",
                                                        "content": thinking_content
                                                    }))
                                                    websocket_logger.info(f"Sent thinking from message: {len(thinking_content)} characters")
                                                
                                                chunk_candidate = msg_obj.content
                                                
                                                # Process the chunk candidate
                                                if chunk_candidate is None:
                                                    continue # Skip None chunks

                                                # Handle different content types from LangChain messages
                                                if not isinstance(chunk_candidate, str):
                                                    # If it's a list, try to extract text content
                                                    if isinstance(chunk_candidate, list):
                                                        text_parts = []
                                                        for item in chunk_candidate:
                                                            if isinstance(item, dict):
                                                                # Handle different content block types
                                                                if item.get('type') == 'text' and 'text' in item:
                                                                    text_parts.append(item['text'])
                                                                elif 'text' in item and not item.get('type') == 'thinking':
                                                                    # Include text blocks but skip thinking blocks
                                                                    text_parts.append(item['text'])
                                                            elif isinstance(item, str):
                                                                text_parts.append(item)
                                                        chunk_candidate = ' '.join(text_parts) if text_parts else None
                                                    else:
                                                        logger.warning(f"Received non-string chunk from LLM: {type(chunk_candidate)}. Attempting extraction.")
                                                        # Try to extract text if it's a complex object
                                                        if hasattr(chunk_candidate, 'content'):
                                                            chunk_candidate = str(chunk_candidate.content)
                                                        elif hasattr(chunk_candidate, 'text'):
                                                            chunk_candidate = str(chunk_candidate.text)
                                                        else:
                                                            chunk_candidate = str(chunk_candidate)
                                                
                                                if chunk_candidate is None or not isinstance(chunk_candidate, str):
                                                    continue

                                                # Apply less aggressive filtering - only block obvious raw data
                                                if chunk_candidate.strip() and not is_obviously_raw_data(chunk_candidate):
                                                    # Add intelligent spacing for sentence boundaries
                                                    if (accumulated_response_content and 
                                                        accumulated_response_content[-1] not in ' \n\t' and
                                                        chunk_candidate[0] not in ' \n\t' and
                                                        (accumulated_response_content.endswith('.') or 
                                                         accumulated_response_content.endswith('!') or 
                                                         accumulated_response_content.endswith('?') or
                                                         accumulated_response_content.endswith(':'))):
                                                        chunk_candidate = ' ' + chunk_candidate
                                                    
                                                    accumulated_response_content += chunk_candidate
                                                    await websocket.send_text(json.dumps({
                                                        "type": "message_chunk",
                                                        "content": chunk_candidate, 
                                                    }))
                                                    has_sent_chunks = True
                                                    await asyncio.sleep(0.01)
                                                elif chunk_candidate.strip():
                                                    logger.warning(f"Skipping raw data chunk: {chunk_candidate[:200]}...")
                            
                            logger.info(f"Streaming complete for ({conversation_id}): {message_content[:100]}...")
                            
                            # Final processing of accumulated content
                            if not accumulated_response_content.strip() and not has_sent_chunks:
                               logger.warning("No valid content was generated. Sending fallback message.")
                               final_response_content = "I was unable to generate a response for this query. Please try again."
                               await websocket.send_text(json.dumps({
                                   "type": "message_chunk",
                                   "content": final_response_content,
                               }))
                               accumulated_response_content = final_response_content


                            if accumulated_response_content.strip(): # Only save if there's meaningful content
                                conversations[conversation_id].messages.append({
                                    "role": "assistant",
                                    "content": accumulated_response_content # Save the cleaned/final version
                                })
                            
                            await websocket.send_text(json.dumps({"type": "message_complete"}))
                        
                        except Exception as e:
                            logger.error(f"Error in LangGraph streaming process ({conversation_id}): {e}", exc_info=True)
                            error_message = f"An error occurred while processing your message: {str(e)}"
                            try:
                                # Send error as a chunk so it appears
                                await websocket.send_text(json.dumps({"type": "message_chunk", "content": error_message}))
                                await websocket.send_text(json.dumps({"type": "message_complete"}))
                            except Exception as ws_send_err:
                                logger.error(f"Failed to send error to WebSocket: {ws_send_err}")
                    
                    asyncio.create_task(process_and_stream())
            
            except json.JSONDecodeError:
                logger.error(f"Received invalid JSON from WebSocket ({conversation_id})")
                # Try to inform client if possible
                try:
                    await websocket.send_text(json.dumps({"type": "message_chunk", "content": "Error: Invalid request format."}))
                    await websocket.send_text(json.dumps({"type": "message_complete"}))
                except: pass
            except Exception as e:
                logger.error(f"Error processing WebSocket message ({conversation_id}): {e}", exc_info=True)
                try:
                    await websocket.send_text(json.dumps({"type": "message_chunk", "content": "An internal error occurred."}))
                    await websocket.send_text(json.dumps({"type": "message_complete"}))
                except Exception:
                    pass
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for conversation: {conversation_id}")
    except Exception as e:
        logger.error(f"Unexpected WebSocket error ({conversation_id}): {e}", exc_info=True)
    finally:
        manager.disconnect(conversation_id)
        
        # Process conversation for long-term memory when disconnecting
        if conversation_id in conversations and len(conversations[conversation_id].messages) > 1:
            try:
                # Convert conversation messages to proper format for memory processing
                messages = []
                for msg in conversations[conversation_id].messages:
                    if msg["role"] == "user":
                        from langchain_core.messages import HumanMessage
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        from langchain_core.messages import AIMessage
                        messages.append(AIMessage(content=msg["content"]))
                
                # Process for memory extraction
                process_conversation_for_memory(messages, conversation_id)
                logger.info(f"Processed conversation {conversation_id} for long-term memory on disconnect")
            except Exception as memory_error:
                logger.error(f"Error processing conversation {conversation_id} for memory: {memory_error}")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting AI by Design Copilot server on http://0.0.0.0:8000")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_config=None,  # Disable uvicorn's default logging
        access_log=False  # Disable access logging since we handle it ourselves
    )
