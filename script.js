document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('file-input');
    const browseFilesBtn = document.querySelector('.browse-files-btn');
    const uploadArea = document.querySelector('.upload-area');
    const uploadedFilesList = document.querySelector('.uploaded-files-list');
    const messageInput = document.querySelector('.message-input');
    const sendMessageBtn = document.querySelector('.send-message-btn');
    const chatMessages = document.querySelector('.chat-messages');

    // Flag to track if a PDF has been successfully processed
    let isPdfProcessed = false;

    // Function to add a message to the chat window
    function addMessageToChat(message, sender = 'bot') {
        const messageDiv = document.createElement('p');
        messageDiv.classList.add(sender === 'user' ? 'user-message' : 'bot-message');
        messageDiv.textContent = message;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Handle "Browse Files" button click
    browseFilesBtn.addEventListener('click', () => {
        fileInput.click();
    });

    // Handle file input change (when files are selected) — fixed to only trigger once
    fileInput.addEventListener('change', (event) => {
        const files = event.target.files;
        uploadedFilesList.innerHTML = ''; // Clear existing list

        if (files.length > 0) {
            const file = files[0];

            // Show file name
            const li = document.createElement('li');
            li.textContent = file.name;
            uploadedFilesList.appendChild(li);

            // Handle the file upload
            handleFileUpload(file);
        }
    });

    // Handle drag and drop
    uploadArea.addEventListener('dragover', (event) => {
        event.preventDefault();
        uploadArea.style.borderColor = '#6366F1';
        uploadArea.style.backgroundColor = '#f3f4f6';
    });

    uploadArea.addEventListener('dragleave', (event) => {
        event.preventDefault();
        uploadArea.style.borderColor = '#d1d5db';
        uploadArea.style.backgroundColor = 'transparent';
    });

    uploadArea.addEventListener('drop', (event) => {
        event.preventDefault();
        uploadArea.style.borderColor = '#d1d5db';
        uploadArea.style.backgroundColor = 'transparent';

        const files = event.dataTransfer.files;
        if (files.length > 0) {
            uploadedFilesList.innerHTML = ''; // Clear existing list

            const file = files[0];

            // Show file name
            const li = document.createElement('li');
            li.textContent = file.name;
            uploadedFilesList.appendChild(li);

            handleFileUpload(file);
        }
    });

    async function handleFileUpload(file) {
        if (file.type !== 'application/pdf') {
            addMessageToChat("❌ Please upload a PDF file.", 'bot');
            return;
        }

        if (file.size > 10 * 1024 * 1024) { // 10MB limit
            addMessageToChat("❌ File size exceeds 10MB limit. Please upload a smaller PDF.", 'bot');
            return;
        }

        // Clear list and show "Uploading..." status
        uploadedFilesList.innerHTML = '';
        const listItem = document.createElement('li');
        listItem.textContent = `Uploading "${file.name}"...`;
        listItem.style.color = '#555';
        uploadedFilesList.appendChild(listItem);

        addMessageToChat("Please wait while I process your PDF. This might take a moment.", 'bot');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload_pdf', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (data.status === 'success') {
                uploadedFilesList.innerHTML = '';
                const successItem = document.createElement('li');
                successItem.textContent = `✅ ${file.name} processed.`;
                successItem.style.color = 'green';
                uploadedFilesList.appendChild(successItem);
                addMessageToChat(data.message, 'bot');
                isPdfProcessed = true;
            } else {
                uploadedFilesList.innerHTML = '';
                const errorItem = document.createElement('li');
                errorItem.textContent = `❌ ${data.message}`;
                errorItem.style.color = 'red';
                uploadedFilesList.appendChild(errorItem);
                addMessageToChat(`Error processing PDF: ${data.message}`, 'bot');
                isPdfProcessed = false;
            }
        } catch (error) {
            uploadedFilesList.innerHTML = '';
            const networkErrorItem = document.createElement('li');
            networkErrorItem.textContent = "⚠️ Network error during upload.";
            networkErrorItem.style.color = 'orange';
            uploadedFilesList.appendChild(networkErrorItem);
            addMessageToChat("There was a network error uploading the PDF. Please check your connection and try again.", 'bot');
            isPdfProcessed = false;
            console.error('Error uploading file:', error);
        }
    }

    // Handle sending messages
    sendMessageBtn.addEventListener('click', () => {
        sendMessage();
    });

    messageInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    async function sendMessage() {
        const messageText = messageInput.value.trim();
        if (messageText === '') return;

        addMessageToChat(messageText, 'user');
        messageInput.value = '';

        if (!isPdfProcessed) {
            addMessageToChat("⚠️ Please upload and process a PDF first before asking questions.", 'bot');
            return;
        }

        const thinkingMessage = document.createElement('p');
        thinkingMessage.classList.add('bot-message', 'thinking');
        thinkingMessage.textContent = "PreciseBot is thinking...";
        chatMessages.appendChild(thinkingMessage);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: messageText }),
            });

            const data = await response.json();

            if (chatMessages.contains(thinkingMessage)) {
                chatMessages.removeChild(thinkingMessage);
            }

            addMessageToChat(data.response, 'bot');

        } catch (error) {
            if (chatMessages.contains(thinkingMessage)) {
                chatMessages.removeChild(thinkingMessage);
            }
            addMessageToChat("Sorry, I couldn't get a response. There might be an issue with the server or the PDF was not processed correctly.", 'bot');
            console.error('Error sending message:', error);
        }
    }
});
