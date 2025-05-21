// static/js/app.js
document.addEventListener('DOMContentLoaded', () => {
    // DOM elements
    const messagesContainer = document.getElementById('messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const scrollButton = document.getElementById('scroll-button');
    
    // State
    let conversationId = null;
    let ws = null;
    
    // Auto-resize text area
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = (messageInput.scrollHeight) + 'px';
    });
    
    // Scroll to bottom functionality
    const scrollToBottom = () => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    };
    
    scrollButton.addEventListener('click', scrollToBottom);
    
    // Show/hide scroll button based on scroll position
    messagesContainer.addEventListener('scroll', () => {
        const scrollPosition = messagesContainer.scrollTop + messagesContainer.clientHeight;
        const scrollHeight = messagesContainer.scrollHeight;
        
        if (scrollHeight - scrollPosition > 100) {
            scrollButton.classList.add('visible');
        } else {
            scrollButton.classList.remove('visible');
        }
    });
    
    // Initialize conversation
    const initConversation = async () => {
        try {
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
            addErrorMessage('Failed to initialize conversation. Please refresh the page.');
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
                appendToLastMessage(data.content);
            } else if (data.type === 'message_complete') {
                // Ensure message is complete and scroll
                setTimeout(scrollToBottom, 100);
            } else if (data.type === 'error') {
                addErrorMessage(data.content);
            }
        };
        
        ws.onclose = () => {
            console.log('WebSocket connection closed');
            // Try to reconnect after a short delay
            setTimeout(initWebSocket, 3000);
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    };
    
    // Add a message to the UI
    const addMessage = (content, isUser = false) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        if (isUser) {
            messageContent.textContent = content;
        } else {
            // For the assistant, we'll start with an empty message that can be updated
            messageContent.innerHTML = content || '';
        }
        
        messageDiv.appendChild(messageContent);
        messagesContainer.appendChild(messageDiv);
        
        // Scroll to the new message
        scrollToBottom();
        
        return messageDiv;
    };
    
    // Append content to the last message (for streaming)
    const appendToLastMessage = (content) => {
        const messages = messagesContainer.querySelectorAll('.message');
        const lastMessage = messages[messages.length - 1];
        
        if (lastMessage && lastMessage.classList.contains('assistant')) {
            const messageContent = lastMessage.querySelector('.message-content');
            messageContent.innerHTML += content;
            
            // Auto-scroll if near bottom
            const scrollPosition = messagesContainer.scrollTop + messagesContainer.clientHeight;
            const scrollThreshold = messagesContainer.scrollHeight - 100;
            
            if (scrollPosition >= scrollThreshold) {
                scrollToBottom();
            }
        }
    };
    
    // Add an error message
    const addErrorMessage = (content) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content error';
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
        addMessage(content, true);
        
        // Create placeholder for assistant response
        addMessage('', false);
        
        // Send via WebSocket
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'message',
                content: content,
                id: Date.now().toString()
            }));
        } else {
            addErrorMessage('Connection lost. Please refresh the page.');
        }
        
        // Clear input
        messageInput.value = '';
        messageInput.style.height = 'auto';
        
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