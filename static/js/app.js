// static/js/app.js
document.addEventListener('DOMContentLoaded', () => {
    // DOM elements
    const messagesContainer = document.getElementById('messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    
    // State
    let conversationId = null;
    let ws = null;
    let currentAssistantMessageDiv = null; // To hold the current assistant message div for streaming
    
    // Auto-resize text area
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = (messageInput.scrollHeight) + 'px';
    });
    
    // Scroll to bottom functionality
    const scrollToBottom = () => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    };
    
    // Initialize conversation
    const initConversation = async () => {
        try {
            // Clear any existing messages first
            messagesContainer.innerHTML = '';
            
            // Add proper welcome message
            addMessageToUI("Hi! I'm your AI by Design Copilot. I can answer questions by searching Wikipedia and the Web. I can also write and execute code securely. How can I help you today?", 'assistant');
            
            const response = await fetch('/api/conversations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            conversationId = data.conversation_id;
            
            // Initialize WebSocket
            initWebSocket();
        } catch (error) {
            console.error('Error initializing conversation:', error);
            addErrorMessageToUI('Failed to initialize conversation. Please refresh the page.');
        }
    };
    
    // Initialize WebSocket
    const initWebSocket = () => {
        // Close existing connection if any
        if (ws) {
            ws.close();
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        ws = new WebSocket(`${protocol}//${window.location.host}/ws/${conversationId}`);
        
        ws.onopen = () => {
            console.log('WebSocket connection established');
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'message_chunk') {
                // Ensure content is a string and not an object stringification
                if (typeof data.content === 'string' && !data.content.includes('[object Object]')) {
                    appendToAssistantMessage(data.content);
                } else {
                    console.warn("Skipping message_chunk due to invalid content:", data.content);
                }
            } else if (data.type === 'message_complete') {
                // Ensure message is complete and scroll
                currentAssistantMessageDiv = null; // Reset for the next message
                setTimeout(scrollToBottom, 100);
            } else if (data.type === 'error') {
                addErrorMessageToUI(data.content);
                currentAssistantMessageDiv = null; // Reset if an error occurs
            }
        };
        
        ws.onclose = () => {
            console.log('WebSocket connection closed');
            // Try to reconnect after a short delay
            setTimeout(initWebSocket, 3000);
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            addErrorMessageToUI('WebSocket connection error. Please try refreshing.');
        };
    };
    
    // Add a complete message to the UI (user or initial assistant)
    const addMessageToUI = (content, role = 'user') => {
        // Basic check for invalid content
        if (!content || (typeof content === 'string' && content.includes('[object Object]'))) {
            console.warn("Skipping addMessageToUI due to invalid content:", content);
            return null;
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const messageContentDiv = document.createElement('div');
        messageContentDiv.className = 'message-content';
        
        // Sanitize and set content (simple textContent for user, innerHTML for assistant if needed for formatting)
        if (role === 'user') {
            messageContentDiv.textContent = content;
        } else {
            // For assistant, allow HTML if it's properly sanitized by the backend
            // For now, let's assume content is safe or use a sanitizer if available
            messageContentDiv.innerHTML = content; 
        }
        
        messageDiv.appendChild(messageContentDiv);
        messagesContainer.appendChild(messageDiv);
        
        scrollToBottom();
        return messageDiv;
    };

    // Append content to the current assistant message (for streaming)
    const appendToAssistantMessage = (chunk) => {
        // Ensure chunk is a string and not an object stringification
        if (typeof chunk !== 'string' || chunk.includes('[object Object]')) {
            console.warn("Skipping appendToAssistantMessage due to invalid chunk:", chunk);
            return;
        }

        // If there's no current assistant message div, create one
        if (!currentAssistantMessageDiv) {
            currentAssistantMessageDiv = document.createElement('div');
            currentAssistantMessageDiv.className = 'message assistant';
            
            const messageContent = document.createElement('div');
            messageContent.className = 'message-content';
            // Start empty - will be filled by streaming response
            
            currentAssistantMessageDiv.appendChild(messageContent);
            messagesContainer.appendChild(currentAssistantMessageDiv);
        }
        
        const messageContent = currentAssistantMessageDiv.querySelector('.message-content');
        if (messageContent) {
            // Append the chunk (assuming it's safe HTML or plain text)
            messageContent.innerHTML += chunk; 
            
            // Auto-scroll if near bottom
            const scrollPosition = messagesContainer.scrollTop + messagesContainer.clientHeight;
            const scrollThreshold = messagesContainer.scrollHeight - 100; // Adjust threshold as needed
            
            if (scrollPosition >= scrollThreshold) {
                scrollToBottom();
            }
        }
    };
    
    // Add an error message to the UI
    const addErrorMessageToUI = (content) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system'; // Or a specific error class
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content error'; // Style this class for errors
        messageContent.textContent = content;
        
        messageDiv.appendChild(messageContent);
        messagesContainer.appendChild(messageDiv);
        
        scrollToBottom();
    };
    
    // Send a message
    const sendMessage = () => {
        const content = messageInput.value.trim();
        
        if (!content) return;
        
        // Add user message to UI
        addMessageToUI(content, 'user');
        
        // Reset current assistant message div for the new response
        currentAssistantMessageDiv = null; 
        
        // Send via WebSocket
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'message',
                content: content,
                id: Date.now().toString() // Unique ID for the message
            }));
        } else {
            addErrorMessageToUI('Connection lost. Please refresh the page.');
        }
        
        // Clear input
        messageInput.value = '';
        messageInput.style.height = 'auto'; // Reset height
        
        // Focus input
        messageInput.focus();
    };
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Initialize
    initConversation();
});
