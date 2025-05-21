# app.py

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
from app import langgraph_app

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
        
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

manager = ConnectionManager()

# Models
class Message(BaseModel):
    content: str
    role: str = "user"
    
class Conversation(BaseModel):
    id: str = None
    messages: List[Dict[str, Any]] = []

# Store conversations
conversations: Dict[str, Conversation] = {}

# Routes
@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/conversations")
async def create_conversation():
    conversation_id = str(uuid.uuid4())
    conversations[conversation_id] = Conversation(id=conversation_id)
    return {"conversation_id": conversation_id}

@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    await manager.connect(websocket, conversation_id)
    
    # Initialize conversation if it doesn't exist
    if conversation_id not in conversations:
        conversations[conversation_id] = Conversation(id=conversation_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                
                if payload.get("type") == "message":
                    message_content = payload.get("content", "")
                    
                    # Add user message to conversation history
                    conversations[conversation_id].messages.append({
                        "role": "user",
                        "content": message_content
                    })
                    
                    # Send acknowledgment
                    await websocket.send_text(json.dumps({
                        "type": "message_received",
                        "message_id": payload.get("id", "")
                    }))
                    
                    # Process message using LangGraph
                    async def process_and_stream():
                        config = {"configurable": {"thread_id": conversation_id}}
                        partial_response = ""
                        
                        try:
                            for event in langgraph_app.stream({"messages": [("user", message_content)]}, config):
                                for key, value in event.items():
                                    if "messages" in value and value["messages"]:
                                        ai_message = value["messages"][-1]
                                        if hasattr(ai_message, "content"):
                                            content = ai_message.content
                                            if content != partial_response:
                                                # Get the difference (new content)
                                                diff = content[len(partial_response):]
                                                partial_response = content
                                                
                                                # Send the new content chunk
                                                await websocket.send_text(json.dumps({
                                                    "type": "message_chunk",
                                                    "content": diff,
                                                    "is_complete": False
                                                }))
                                                
                                                # Small delay to avoid overwhelming the client
                                                await asyncio.sleep(0.01)
                            
                            # Add final response to conversation history
                            conversations[conversation_id].messages.append({
                                "role": "assistant",
                                "content": partial_response
                            })
                            
                            # Send completion signal
                            await websocket.send_text(json.dumps({
                                "type": "message_complete",
                                "content": partial_response
                            }))
                        
                        except Exception as e:
                            logger.error(f"Error in streaming process: {e}")
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "content": f"An error occurred while processing your message: {str(e)}"
                            }))
                    
                    # Start processing in background
                    asyncio.create_task(process_and_stream())
            
            except json.JSONDecodeError:
                logger.error("Received invalid JSON from WebSocket")
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
    
    except WebSocketDisconnect:
        manager.disconnect(conversation_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(conversation_id)

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting AI by Design Copilot server")
    uvicorn.run(app, host="0.0.0.0", port=8000)