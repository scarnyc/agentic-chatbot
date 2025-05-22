"""
Python-based agentic workflow powered by Anthropic & LangGraph.
This agent is capable of using Tavily web search, and executing code;
It also has access to Wikipedia info while incorporating memory.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
import asyncio
import logging
from core.app import langgraph_app # Assuming core.app contains your LangGraph setup

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    if stripped_text == "[object Object]":
        return True
    
    # Check for patterns that look like stringified JSON objects/arrays from tool outputs
    # (e.g., from the screenshot content)
    if (stripped_text.startswith("{") and stripped_text.endswith("}")) or \
       (stripped_text.startswith("[") and stripped_text.endswith("]")):
        # More specific checks for the kind of content seen in the screenshot
        if '"title":' in stripped_text and '"url":' in stripped_text and '"content":' in stripped_text:
            logger.warning(f"Identified problematic JSON-like string: {stripped_text[:150]}...")
            return True
        if "Weather in Queens" in stripped_text and "weatherapi.com" in stripped_text: # Specific to weather example
             logger.warning(f"Identified problematic weather API string: {stripped_text[:150]}...")
             return True
             
    # Add more heuristics if needed
    return False

@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    await websocket.accept() 

    if conversation_id not in conversations:
        logger.warning(f"WebSocket for conversation_id '{conversation_id}' accepted, but ID not found. Closing.")
        await websocket.close(code=1008) 
        return

    manager.register_connection(websocket, conversation_id)
    logger.info(f"WebSocket registered for conversation: {conversation_id}")
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                
                if payload.get("type") == "message":
                    message_content = payload.get("content", "")
                    if not isinstance(message_content, str): 
                        logger.warning("Received non-string message content from client.")
                        message_content = str(message_content)

                    logger.info(f"Received message from client ({conversation_id}): {message_content[:100]}...")
                    
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
                            async for event in langgraph_app.astream(langgraph_input, config):
                                for key, value in event.items():
                                    if isinstance(value, dict) and "messages" in value:
                                        for msg_obj in value["messages"]:
                                            if hasattr(msg_obj, 'role') and msg_obj.role == 'ai' and hasattr(msg_obj, 'content'):
                                                chunk_candidate = msg_obj.content
                                                
                                                # Process the chunk candidate
                                                if chunk_candidate is None:
                                                    continue # Skip None chunks

                                                if not isinstance(chunk_candidate, str):
                                                    logger.warning(f"Received non-string chunk from LLM: {type(chunk_candidate)}. Stringifying.")
                                                    chunk_candidate = str(chunk_candidate)

                                                if is_problematic_content(chunk_candidate):
                                                    logger.warning(f"Skipping problematic chunk: {chunk_candidate[:100]}...")
                                                    continue # Skip this problematic chunk

                                                if chunk_candidate: # Ensure it's a non-empty string after checks
                                                    accumulated_response_content += chunk_candidate
                                                    await websocket.send_text(json.dumps({
                                                        "type": "message_chunk",
                                                        "content": chunk_candidate, 
                                                    }))
                                                    has_sent_chunks = True
                                                    await asyncio.sleep(0.01)
                            
                            logger.info(f"Streaming complete for ({conversation_id}): {message_content[:100]}...")
                            
                            # Final processing of accumulated content
                            final_response_content = accumulated_response_content
                            if is_problematic_content(final_response_content):
                                logger.error(f"Final accumulated response is still problematic: {final_response_content[:200]}... Replacing.")
                                if has_sent_chunks: # If some valid chunks were sent, maybe just indicate an issue at the end
                                     final_response_content = "\n\n[Some parts of the response could not be displayed correctly.]"
                                     # Send this as a final chunk
                                     await websocket.send_text(json.dumps({
                                        "type": "message_chunk",
                                        "content": final_response_content
                                     }))
                                     accumulated_response_content += final_response_content # for history
                                else: # No valid chunks were ever sent
                                    final_response_content = "I encountered an issue formatting the response. Please try rephrasing your query."
                                    # Send this as the only chunk if nothing else was sent
                                    await websocket.send_text(json.dumps({
                                        "type": "message_chunk",
                                        "content": final_response_content
                                    }))
                                accumulated_response_content = final_response_content


                            if not accumulated_response_content.strip() and not has_sent_chunks: # If response is empty and nothing was sent
                               logger.warning("Final response is empty after filtering. Sending a generic message.")
                               final_response_content = "I was unable to generate a textual response for this query. Please try again."
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

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting AI by Design Copilot server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
