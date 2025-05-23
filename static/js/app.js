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
    let typingIndicator = null; // To hold the typing indicator element
    
    // Auto-resize text area
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = (messageInput.scrollHeight) + 'px';
    });
    
    // Simple markdown parser for basic formatting
    const parseMarkdown = (text) => {
        // Escape HTML first to prevent XSS
        text = text.replace(/&/g, '&amp;')
                   .replace(/</g, '&lt;')
                   .replace(/>/g, '&gt;');
        
        // Handle URLs in square brackets like [text](url) - do this first to avoid conflicts
        text = text.replace(
            /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
            '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
        );
        
        // Handle URLs in parentheses like (https://example.com) 
        text = text.replace(
            /\((https?:\/\/[^\s)]+)\)/g,
            '(<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>)'
        );
        
        // Handle standalone URLs (not already in links)
        text = text.replace(
            /(^|[^"=])(https?:\/\/[^\s<>&"]+)/g,
            '$1<a href="$2" target="_blank" rel="noopener noreferrer">$2</a>'
        );
        
        // Handle headers (must come before other formatting)
        text = text.replace(/^(#{1,6})\s+(.+)$/gm, function(match, hashes, content) {
            const level = hashes.length;
            return `<h${level}>${content}</h${level}>`;
        });
        
        // Handle bold text **text** (must come before italic to avoid conflicts)
        text = text.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
        
        // Handle italic text *text* - only single asterisks not part of bold
        text = text.replace(/(^|[^*])\*([^*\s][^*]*?[^*\s])\*([^*]|$)/g, '$1<em>$2</em>$3');
        
        // Handle line breaks
        text = text.replace(/\n/g, '<br>');
        
        return text;
    };
    
    // Scroll to bottom functionality
    const scrollToBottom = () => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    };
    
    // Typing indicator functions
    const showTypingIndicator = (message = "Thinking", isToolUse = false) => {
        // Remove existing typing indicator
        hideTypingIndicator();
        
        // Create typing indicator element
        typingIndicator = document.createElement('div');
        typingIndicator.className = `message assistant typing-indicator ${isToolUse ? 'tool-indicator' : ''}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = `
            ${message}
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        
        typingIndicator.appendChild(messageContent);
        messagesContainer.appendChild(typingIndicator);
        
        scrollToBottom();
    };
    
    const hideTypingIndicator = () => {
        if (typingIndicator) {
            typingIndicator.remove();
            typingIndicator = null;
        }
    };
    
    const updateTypingIndicator = (message, isToolUse = false) => {
        if (typingIndicator) {
            const messageContent = typingIndicator.querySelector('.message-content');
            messageContent.innerHTML = `
                ${message}
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            `;
            
            // Update styling for tool use
            if (isToolUse) {
                typingIndicator.classList.add('tool-indicator');
            } else {
                typingIndicator.classList.remove('tool-indicator');
            }
        }
    };
    
    // Thinking content display functions
    let currentThinkingDiv = null;
    let thinkingToggleState = localStorage.getItem('thinkingToggle') === 'true';
    
    const displayThinkingContent = (thinkingContent) => {
        // Only display if thinking toggle is enabled
        if (!thinkingToggleState) {
            return;
        }
        
        // Hide typing indicator
        hideTypingIndicator();
        
        // Create or update thinking display
        if (!currentThinkingDiv) {
            currentThinkingDiv = document.createElement('div');
            currentThinkingDiv.className = 'message assistant thinking-display';
            
            const messageContent = document.createElement('div');
            messageContent.className = 'message-content thinking-content';
            
            // Add thinking header with toggle
            const thinkingHeader = document.createElement('div');
            thinkingHeader.className = 'thinking-header';
            thinkingHeader.innerHTML = `
                <span class="thinking-icon">🤔</span>
                <span class="thinking-title">Claude's Thinking</span>
                <button class="thinking-toggle" onclick="toggleThinkingExpanded(this)">▼</button>
            `;
            
            const thinkingText = document.createElement('div');
            thinkingText.className = 'thinking-text';
            thinkingText.textContent = thinkingContent;
            
            messageContent.appendChild(thinkingHeader);
            messageContent.appendChild(thinkingText);
            currentThinkingDiv.appendChild(messageContent);
            messagesContainer.appendChild(currentThinkingDiv);
        } else {
            // Update existing thinking content
            const thinkingText = currentThinkingDiv.querySelector('.thinking-text');
            thinkingText.textContent = thinkingContent;
        }
        
        scrollToBottom();
    };
    
    // Global function for thinking toggle (called from button)
    window.toggleThinkingExpanded = (button) => {
        const thinkingText = button.closest('.message-content').querySelector('.thinking-text');
        const isExpanded = thinkingText.style.display !== 'none';
        
        if (isExpanded) {
            thinkingText.style.display = 'none';
            button.textContent = '▶';
        } else {
            thinkingText.style.display = 'block';
            button.textContent = '▼';
        }
    };
    
    // Initialize conversation
    const initConversation = async () => {
        try {
            // Clear any existing messages first
            messagesContainer.innerHTML = '';
            
            // Add proper welcome message
            addMessageToUI("Hi! I'm your AI by Design Agent. I can answer questions by searching Wikipedia and the Web. I can also write and execute code securely. How can I help you today?", 'assistant');
            
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
                // Hide typing indicator when first content arrives
                hideTypingIndicator();
                
                // Conservative content validation - only block obvious issues
                if (typeof data.content === 'string' && 
                    !data.content.includes('[object Object]') && 
                    data.content.trim().length > 0 &&
                    // Only block if it looks like obvious JSON with lots of structure
                    !(data.content.trim().startsWith('{') && data.content.includes('","') && data.content.includes('":"'))) {
                    appendToAssistantMessage(data.content);
                } else {
                    console.warn("Skipping message_chunk due to invalid content:", data.content);
                }
            } else if (data.type === 'thinking') {
                // Handle thinking content
                if (data.content && data.content.trim()) {
                    displayThinkingContent(data.content);
                } else {
                    // Show thinking indicator if no content
                    showTypingIndicator("Thinking");
                }
            } else if (data.type === 'tool_start') {
                // Show tool-specific typing indicator
                const toolName = data.tool_name || 'tool';
                let toolMessage = 'Using tool';
                
                // Customize message based on tool
                if (toolName.includes('wikipedia')) {
                    toolMessage = 'Searching Wikipedia';
                } else if (toolName.includes('search') || toolName.includes('tavily')) {
                    toolMessage = 'Searching the web';
                } else if (toolName.includes('python') || toolName.includes('code')) {
                    toolMessage = 'Running code';
                }
                
                updateTypingIndicator(toolMessage, true);
            } else if (data.type === 'tool_end') {
                // Show processing indicator after tool completes
                updateTypingIndicator("Processing results");
            } else if (data.type === 'retry_attempt') {
                // Show retry indicator
                const retryMessage = `Retrying (${data.attempt}/${data.max_attempts})`;
                updateTypingIndicator(retryMessage, false);
            } else if (data.type === 'retry_delay') {
                // Show delay indicator
                const delayMessage = `Waiting ${Math.ceil(data.delay)}s before retry`;
                updateTypingIndicator(delayMessage, false);
            } else if (data.type === 'retry_success') {
                // Show success after retry
                updateTypingIndicator("Retry successful, processing");
            } else if (data.type === 'retry_exhausted') {
                // Hide indicator when retries are exhausted
                hideTypingIndicator();
            } else if (data.type === 'message_complete') {
                // Hide typing indicator and ensure message is complete
                hideTypingIndicator();
                currentAssistantMessageDiv = null; // Reset for the next message
                currentThinkingDiv = null; // Reset thinking display for next message
                setTimeout(scrollToBottom, 100);
            } else if (data.type === 'error') {
                hideTypingIndicator();
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
        
        // Sanitize and set content (simple textContent for user, parsed markdown for assistant)
        if (role === 'user') {
            messageContentDiv.textContent = content;
        } else {
            // For assistant, parse markdown for proper formatting
            messageContentDiv.innerHTML = parseMarkdown(content); 
        }
        
        messageDiv.appendChild(messageContentDiv);
        messagesContainer.appendChild(messageDiv);
        
        scrollToBottom();
        return messageDiv;
    };

    // Append content to the current assistant message (for streaming)
    const appendToAssistantMessage = (chunk) => {
        // Conservative validation - only reject obvious problems
        if (typeof chunk !== 'string' || chunk.includes('[object Object]') || !chunk.trim()) {
            console.warn("Skipping appendToAssistantMessage due to invalid chunk:", chunk);
            return;
        }

        // If there's no current assistant message div, create one ONLY when we have valid content
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
            // Parse markdown and append the chunk
            const parsedChunk = parseMarkdown(chunk);
            messageContent.innerHTML += parsedChunk; 
            
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
        
        // Show initial typing indicator
        showTypingIndicator("Thinking");
        
        // Send via WebSocket
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'message',
                content: content,
                id: Date.now().toString() // Unique ID for the message
            }));
        } else {
            hideTypingIndicator();
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
    
    // Initialize thinking toggle
    const thinkingToggle = document.getElementById('thinking-toggle');
    thinkingToggle.checked = thinkingToggleState;
    
    thinkingToggle.addEventListener('change', (e) => {
        thinkingToggleState = e.target.checked;
        localStorage.setItem('thinkingToggle', thinkingToggleState);
        
        // Hide/show existing thinking displays
        const thinkingDisplays = document.querySelectorAll('.thinking-display');
        thinkingDisplays.forEach(display => {
            display.style.display = thinkingToggleState ? 'flex' : 'none';
        });
    });
    
    // Initialize
    initConversation();
});
