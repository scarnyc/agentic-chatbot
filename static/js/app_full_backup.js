// static/js/app.js
console.log('=== APP.JS LOADING ===');
console.log('DOMContentLoaded event starting...');

document.addEventListener('DOMContentLoaded', () => {
    console.log('=== DOMContentLoaded FIRED ===');
    // DOM elements
    const messagesContainer = document.getElementById('messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const uploadButton = document.getElementById('upload-button');
    const batchUploadButton = document.getElementById('batch-upload-button');
    const fileInput = document.getElementById('file-input');
    const filePreview = document.getElementById('file-preview');
    const fileName = document.getElementById('file-name');
    const fileThumbnail = document.getElementById('file-thumbnail');
    const removeFileButton = document.getElementById('remove-file');
    
    // Batch upload elements
    const batchUploadModal = document.getElementById('batch-upload-modal');
    const closeBatchModal = document.getElementById('close-batch-modal');
    const cancelBatch = document.getElementById('cancel-batch');
    const startBatch = document.getElementById('start-batch');
    const directoryPath = document.getElementById('directory-path');
    
    // Debug logging (can be removed in production)
    console.log('=== BATCH UPLOAD DEBUG ===');
    console.log('batchUploadButton:', batchUploadButton);
    console.log('batchUploadModal:', batchUploadModal);
    console.log('uploadButton:', uploadButton);
    console.log('sendButton:', sendButton);
    
    // Test if we can access the button at all
    if (batchUploadButton) {
        console.log('Button found! innerHTML:', batchUploadButton.innerHTML);
        console.log('Button styles:', window.getComputedStyle(batchUploadButton));
        console.log('Button parent:', batchUploadButton.parentElement);
    }
    
    // State
    let conversationId = null;
    let ws = null;
    let currentAssistantMessageDiv = null; // To hold the current assistant message div for streaming
    let typingIndicator = null; // To hold the typing indicator element
    let currentFile = null; // Current uploaded file
    
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
    
    // Removed thinking display functionality - keeping backend thinking enabled for quality
    
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
            // Thinking content handling removed - keeping backend thinking for quality
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
    const sendMessage = async () => {
        const content = messageInput.value.trim();
        
        if (!content && !currentFile) return;
        
        // If there's a file, handle file upload first
        if (currentFile) {
            await handleFileUpload(content);
        } else {
            // Regular text message
            sendTextMessage(content);
        }
    };
    
    // Send regular text message
    const sendTextMessage = (content) => {
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
    
    // Handle file upload and analysis
    const handleFileUpload = async (userMessage) => {
        if (!currentFile) return;
        
        try {
            // Show file upload in UI
            const fileName = currentFile.name;
            const fileType = currentFile.type.startsWith('image/') ? 'image' : 'PDF';
            const displayMessage = userMessage || `Please analyze this ${fileType}: ${fileName}`;
            
            addMessageToUI(displayMessage, 'user');
            
            // Reset current assistant message div for the new response
            currentAssistantMessageDiv = null;
            
            // Show typing indicator
            showTypingIndicator("Processing file");
            
            // Create FormData for file upload
            const formData = new FormData();
            formData.append('file', currentFile);
            if (userMessage) {
                formData.append('message', userMessage);
            }
            formData.append('conversation_id', conversationId);
            
            // Upload file and get analysis
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // Hide typing indicator and show response
            hideTypingIndicator();
            addMessageToUI(result.analysis, 'assistant');
            
        } catch (error) {
            console.error('File upload error:', error);
            hideTypingIndicator();
            addErrorMessageToUI(`Failed to process file: ${error.message}`);
        } finally {
            // Clear file and input
            clearFile();
            messageInput.value = '';
            messageInput.style.height = 'auto';
            messageInput.focus();
        }
    };
    
    // File handling functions
    const handleFileSelect = (event) => {
        const file = event.target.files[0];
        if (!file) return;
        
        // Validate file type
        const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'application/pdf'];
        if (!validTypes.includes(file.type)) {
            alert('Please select an image file (JPEG, PNG, GIF, WebP) or PDF.');
            return;
        }
        
        // Validate file size (10MB limit)
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            alert('File size must be less than 10MB.');
            return;
        }
        
        currentFile = file;
        showFilePreview(file);
    };
    
    const showFilePreview = (file) => {
        fileName.textContent = file.name;
        
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                fileThumbnail.innerHTML = `<img src="${e.target.result}" alt="Preview">`;
            };
            reader.readAsDataURL(file);
        } else if (file.type === 'application/pdf') {
            fileThumbnail.innerHTML = `<div class="pdf-icon"><i class="fas fa-file-pdf"></i></div>`;
        }
        
        filePreview.style.display = 'block';
    };
    
    const clearFile = () => {
        currentFile = null;
        fileInput.value = '';
        filePreview.style.display = 'none';
        fileThumbnail.innerHTML = '';
        fileName.textContent = '';
    };
    
    // Batch upload functions
    const showBatchModal = () => {
        console.log('showBatchModal called');
        if (batchUploadModal) {
            batchUploadModal.style.display = 'flex';
            if (directoryPath) {
                directoryPath.focus();
            }
        } else {
            console.error('batchUploadModal not found in showBatchModal');
        }
    };
    
    const hideBatchModal = () => {
        batchUploadModal.style.display = 'none';
        directoryPath.value = '';
    };
    
    const handleBatchUpload = async () => {
        const path = directoryPath.value.trim();
        
        if (!path) {
            alert('Please enter a directory path.');
            return;
        }
        
        try {
            // Disable button during processing
            startBatch.disabled = true;
            startBatch.textContent = 'Processing...';
            
            // Hide modal
            hideBatchModal();
            
            // Show processing message in chat
            addMessageToUI(`Starting batch processing of files in: ${path}`, 'user');
            
            // Reset current assistant message div for the new response
            currentAssistantMessageDiv = null;
            
            // Show typing indicator
            showTypingIndicator("Processing batch upload");
            
            // Create FormData for batch upload
            const formData = new FormData();
            formData.append('directory_path', path);
            formData.append('conversation_id', conversationId);
            
            // Send batch upload request
            const response = await fetch('/api/batch-upload', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Batch upload failed: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // Hide typing indicator and show response
            hideTypingIndicator();
            
            // Create detailed response message
            let responseMessage = `SUCCESS! Processed ${result.processed_count} out of ${result.total_files} files.\n\n`;
            responseMessage += `Output directory: ${result.output_directory}\n\n`;
            
            if (result.processed_files && result.processed_files.length > 0) {
                responseMessage += `Processed files: ${result.processed_files.join(', ')}\n\n`;
            }
            
            if (result.errors && result.errors.length > 0) {
                responseMessage += `Errors encountered:\n${result.errors.join('\n')}\n\n`;
            }
            
            if (result.example_analysis) {
                responseMessage += `Example analysis:\n${result.example_analysis}`;
            }
            
            addMessageToUI(responseMessage, 'assistant');
            
        } catch (error) {
            console.error('Batch upload error:', error);
            hideTypingIndicator();
            addErrorMessageToUI(`Failed to process batch upload: ${error.message}`);
        } finally {
            // Re-enable button
            startBatch.disabled = false;
            startBatch.textContent = 'Start Batch Processing';
        }
    };
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // File upload functionality
    uploadButton.addEventListener('click', () => {
        fileInput.click();
    });
    
    fileInput.addEventListener('change', handleFileSelect);
    removeFileButton.addEventListener('click', clearFile);
    
    // Batch upload functionality
    if (batchUploadButton) {
        // Try multiple ways to add the event listener
        batchUploadButton.addEventListener('click', function(e) {
            console.log('=== BUTTON CLICKED ===', e);
            e.preventDefault();
            e.stopPropagation();
            showBatchModal();
        });
        
        // Also try onclick as backup
        batchUploadButton.onclick = function(e) {
            console.log('=== ONCLICK TRIGGERED ===', e);
            showBatchModal();
        };
        
        console.log('Batch upload button event listeners added');
        
        // Add visible indicator that JavaScript is working
        batchUploadButton.style.border = '2px solid green';
        batchUploadButton.title = 'Batch upload - JS loaded';
        
    } else {
        console.error('Batch upload button not found!');
    }
    
    if (closeBatchModal) {
        closeBatchModal.addEventListener('click', hideBatchModal);
    }
    
    if (cancelBatch) {
        cancelBatch.addEventListener('click', hideBatchModal);
    }
    
    if (startBatch) {
        startBatch.addEventListener('click', handleBatchUpload);
    }
    
    // Close modal when clicking outside
    if (batchUploadModal) {
        batchUploadModal.addEventListener('click', (e) => {
            if (e.target === batchUploadModal) {
                hideBatchModal();
            }
        });
    }
    
    // Handle Enter key in directory input
    if (directoryPath) {
        directoryPath.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleBatchUpload();
            }
        });
    }
    
    // Thinking toggle removed - backend thinking still enabled for quality
    
    // Initialize
    initConversation();
});
