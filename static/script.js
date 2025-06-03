document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('file-input');
    const browseFilesBtn = document.querySelector('.browse-files-btn');
    const uploadArea = document.querySelector('.upload-area');
    const uploadedFilesList = document.querySelector('.uploaded-files-list');
    const messageInput = document.querySelector('.message-input');
    const sendMessageBtn = document.querySelector('.send-message-btn');
    const chatMessages = document.querySelector('.chat-messages');
    const uploadStatusText = document.createElement('li'); // For upload status messages
    uploadedFilesList.appendChild(uploadStatusText); // Add it to the list

    // Function to add a message to the chat window
    function addMessageToChat(message, sender = 'bot') {
        const messageDiv = document.createElement('p');
        messageDiv.classList.add(sender === 'user' ? 'user-message' : 'bot-message');
        messageDiv.textContent = message;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to bottom
    }



    // Handle "Browse Files" button click
    browseFilesBtn.addEventListener('click', () => {
        fileInput.click();
    });

    // Handle file input change (when files are selected)
    fileInput.addEventListener('change', (event) => {
        const files = event.target.files;
        if (files.length > 0) {
            handleFileUpload(files[0]); // We only expect one PDF for now
        }
    });

    // Handle drag and drop
    uploadArea.addEventListener('dragover', (event) => {
        event.preventDefault();
        uploadArea.style.borderColor = '#6366F1'; // Highlight on drag over
        uploadArea.style.backgroundColor = '#f3f4f6';
    });

    uploadArea.addEventListener('dragleave', (event) => {
        event.preventDefault();
        uploadArea.style.borderColor = '#d1d5db'; // Reset on drag leave
        uploadArea.style.backgroundColor = 'transparent';
    });

    uploadArea.addEventListener('drop', (event) => {
        event.preventDefault();
        uploadArea.style.borderColor = '#d1d5db'; // Reset on drop
        uploadArea.style.backgroundColor = 'transparent';
        const files = event.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]); // We only expect one PDF for now
        }
    });

    async function handleFileUpload(file) {
        if (file.type !== 'application/pdf') {
            uploadStatusText.textContent = "❌ Please upload a PDF file.";
            uploadStatusText.style.color = 'red';
            return;
        }

        uploadedFilesList.innerHTML = ''; // Clear previous files
        const listItem = document.createElement('li');
        listItem.textContent = `Uploading: ${file.name}...`;
        listItem.style.color = '#555';
        uploadedFilesList.appendChild(listItem);
        uploadStatusText.textContent = ""; // Clear old status

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload_pdf', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (data.status === 'success') {
                uploadedFilesList.innerHTML = ''; // Clear "Uploading..."
                const successItem = document.createElement('li');
                successItem.textContent = `✅ ${file.name} processed.`;
                successItem.style.color = 'green';
                uploadedFilesList.appendChild(successItem);
                addMessageToChat(data.message);
            } else {
                uploadedFilesList.innerHTML = '';
                const errorItem = document.createElement('li');
                errorItem.textContent = `❌ ${data.message}`;
                errorItem.style.color = 'red';
                uploadedFilesList.appendChild(errorItem);
                addMessageToChat(`Error processing PDF: ${data.message}`, 'bot');
            }
        } catch (error) {
            uploadedFilesList.innerHTML = '';
            const networkErrorItem = document.createElement('li');
            networkErrorItem.textContent = "⚠️ Network error during upload.";
            networkErrorItem.style.color = 'orange';
            uploadedFilesList.appendChild(networkErrorItem);
            addMessageToChat("There was a network error uploading the PDF. Please check your connection and try again.", 'bot');
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
        if (messageText) {
            addMessageToChat(messageText, 'user');
            messageInput.value = ''; // Clear input

            // Add a temporary "typing" or "thinking" message from bot
            const thinkingMessage = document.createElement('p');
            thinkingMessage.classList.add('bot-message', 'thinking');
            thinkingMessage.textContent = "PreciseBot is thinking...";
            chatMessages.appendChild(thinkingMessage);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            try {
                // THIS IS THE CRUCIAL PART: Actually send the fetch request to your Flask backend
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: messageText }),
                });

                const data = await response.json();

                // Remove the thinking message
                chatMessages.removeChild(thinkingMessage);

                // Display the actual response from your Python model
                addMessageToChat(data.response, 'bot');

            } catch (error) {
                // Remove the thinking message if an error occurs
                chatMessages.removeChild(thinkingMessage);
                addMessageToChat("Sorry, I couldn't get a response. There might be an issue with the server or the PDF is not processed.", 'bot');
                console.error('Error sending message:', error);
            }
        }
    }
});