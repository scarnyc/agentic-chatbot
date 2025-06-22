// Working batch upload functionality
console.log('=== APP.JS LOADING ===');

document.addEventListener('DOMContentLoaded', () => {
    console.log('=== DOM READY ===');
    
    // Get batch upload elements
    const batchUploadButton = document.getElementById('batch-upload-button');
    const batchUploadModal = document.getElementById('batch-upload-modal');
    const closeBatchModal = document.getElementById('close-batch-modal');
    const cancelBatch = document.getElementById('cancel-batch');
    const startBatch = document.getElementById('start-batch');
    const directoryPath = document.getElementById('directory-path');
    
    console.log('Elements found:');
    console.log('- batchUploadButton:', batchUploadButton);
    console.log('- batchUploadModal:', batchUploadModal);
    
    // Show/hide modal functions
    const showBatchModal = () => {
        console.log('=== SHOWING MODAL ===');
        if (batchUploadModal) {
            batchUploadModal.style.display = 'flex';
            if (directoryPath) {
                directoryPath.focus();
            }
        }
    };
    
    const hideBatchModal = () => {
        console.log('=== HIDING MODAL ===');
        if (batchUploadModal) {
            batchUploadModal.style.display = 'none';
        }
        if (directoryPath) {
            directoryPath.value = '';
        }
    };
    
    // Add click handlers
    if (batchUploadButton) {
        console.log('=== ADDING CLICK HANDLER ===');
        batchUploadButton.style.border = '2px solid green';
        batchUploadButton.addEventListener('click', function(e) {
            console.log('=== BATCH BUTTON CLICKED ===');
            e.preventDefault();
            e.stopPropagation();
            showBatchModal();
        });
        console.log('Click handler added successfully');
    } else {
        console.error('Batch upload button not found!');
    }
    
    // Get or create conversation ID
    let conversationId = null;
    
    const getConversationId = async () => {
        if (conversationId) return conversationId;
        
        try {
            const response = await fetch('/api/conversations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            conversationId = data.conversation_id;
            return conversationId;
        } catch (error) {
            console.error('Failed to create conversation:', error);
            throw error;
        }
    };

    // Batch upload processing function
    const handleBatchUpload = async () => {
        const path = directoryPath.value.trim();
        
        if (!path) {
            alert('Please enter a directory path.');
            return;
        }
        
        try {
            console.log('=== STARTING BATCH UPLOAD ===', path);
            
            // Disable button during processing
            if (startBatch) {
                startBatch.disabled = true;
                startBatch.textContent = 'Processing...';
            }
            
            // Hide modal
            hideBatchModal();
            
            // Get conversation ID
            const convId = await getConversationId();
            console.log('Using conversation ID:', convId);
            
            // Create FormData for batch upload
            const formData = new FormData();
            formData.append('directory_path', path);
            formData.append('conversation_id', convId);
            
            console.log('Sending batch upload request...');
            console.log('FormData contents:', {
                directory_path: formData.get('directory_path'),
                conversation_id: formData.get('conversation_id')
            });
            
            // Send batch upload request with timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
            
            try {
                const response = await fetch('/api/batch-upload', {
                    method: 'POST',
                    body: formData,
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                console.log('Response received:', response.status, response.statusText);
                
                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('Error response:', errorText);
                    throw new Error(`Batch upload failed: ${response.statusText} - ${errorText}`);
                }
                
                const result = await response.json();
                console.log('Batch upload result:', result);
            } catch (fetchError) {
                clearTimeout(timeoutId);
                if (fetchError.name === 'AbortError') {
                    throw new Error('Request timed out after 30 seconds');
                }
                throw fetchError;
            }
            
            // Show success message
            alert(`SUCCESS! Processed ${result.processed_count} out of ${result.total_files} files.\n\nOutput directory: ${result.output_directory}\n\nProcessed files: ${result.processed_files ? result.processed_files.join(', ') : 'None'}\n\nExample analysis preview available in chat.`);
            
        } catch (error) {
            console.error('Batch upload error:', error);
            alert(`Failed to process batch upload: ${error.message}`);
        } finally {
            // Re-enable button
            if (startBatch) {
                startBatch.disabled = false;
                startBatch.textContent = 'Start Batch Processing';
            }
        }
    };
    
    // Modal close handlers
    if (closeBatchModal) {
        closeBatchModal.addEventListener('click', hideBatchModal);
    }
    
    if (cancelBatch) {
        cancelBatch.addEventListener('click', hideBatchModal);
    }
    
    // Start batch processing handler
    if (startBatch) {
        startBatch.addEventListener('click', handleBatchUpload);
        console.log('Start batch handler added');
    }
    
    // Enter key in directory input
    if (directoryPath) {
        directoryPath.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleBatchUpload();
            }
        });
    }
    
    // Click outside to close
    if (batchUploadModal) {
        batchUploadModal.addEventListener('click', function(e) {
            if (e.target === batchUploadModal) {
                hideBatchModal();
            }
        });
    }
    
    console.log('=== SETUP COMPLETE ===');
});