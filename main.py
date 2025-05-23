"""
Python-based agentic workflow powered by Anthropic & LangGraph.
This agent is capable of using Tavily web search, and executing code;
It also has access to Wikipedia info while incorporating memory.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
import asyncio
import logging
from core.app import langgraph_app, process_conversation_for_memory, get_memory_stats # Assuming core.app contains your LangGraph setup
from core.cache import get_cache_stats, clear_cache
from core.error_recovery import get_error_recovery_stats

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
                                    
                                    # Check for thinking content in the event
                                    if isinstance(value, dict) and "thinking" in value:
                                        thinking_content = value["thinking"]
                                        # Send thinking content to UI
                                        await websocket.send_text(json.dumps({
                                            "type": "thinking",
                                            "content": thinking_content
                                        }))
                                        websocket_logger.info(f"Sent thinking content: {len(thinking_content)} characters")
                                    
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
                                                
                                                # Check for thinking content in message additional_kwargs
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
