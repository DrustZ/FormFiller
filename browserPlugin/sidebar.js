function toggleSpinner(button, show) {
  const spinner = button.querySelector('.fa-spinner');
  const text = button.querySelector('span');
  if (show) {
      spinner.classList.remove('hidden');
      text.classList.add('hidden');
      button.disabled = true;
  } else {
      spinner.classList.add('hidden');
      text.classList.remove('hidden');
      button.disabled = false;
  }
}

function showStatus(message, isError = false) {
  const statusElement = document.getElementById('status');
  statusElement.textContent = message;
  statusElement.className = isError ? 'text-sm text-red-500' : 'text-sm text-green-500';
  setTimeout(() => {
      statusElement.textContent = '';
      statusElement.className = 'text-sm text-gray-600';
  }, 3000);
}

document.getElementById('fillForms').addEventListener('click', () => {
  chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
    chrome.tabs.sendMessage(tabs[0].id, {action: "fillForms"});
  });
});

document.getElementById('uploadDocuments').addEventListener('click', () => {
  const comment = document.getElementById('uploadComment').value;
  document.getElementById('fileInput').click();
  document.getElementById('fileInput').dataset.comment = comment;
});
  
document.getElementById('fileInput').addEventListener('change', (event) => {
  const files = event.target.files;
  const comment = event.target.dataset.comment || '';
  if (files.length > 0) {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('documents', files[i]);
    }
    formData.append('comment', comment);
    
    const uploadButton = document.getElementById('uploadDocuments');
    toggleSpinner(uploadButton, true);

    fetch('http://localhost:8888/upload', {
      method: 'POST',
      body: formData
    })
    .then(response => response.json())
    .then(data => {
      document.getElementById('status').textContent = 'Documents uploaded successfully!';
    })
    .catch(error => {
      document.getElementById('status').textContent = 'Error uploading documents.';
      console.error('Error:', error);
    })
    .finally(() => {
        const uploadButton = document.getElementById('uploadDocuments');
        toggleSpinner(uploadButton, false);
    });
  }
});
  
  // Chat functionality
  const chatMessages = document.getElementById('chatMessages');
  const messageInput = document.getElementById('messageInput');
  const sendMessage = document.getElementById('sendMessage');

  function displayChatMessage(message, isUser) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', isUser ? 'user-message' : 'assistant-message');
    
    if (typeof message === 'object') {
        if (Array.isArray(message)) {
            // Create a table for array data
            const table = document.createElement('table');
            table.className = 'data-table';
            
            // Create header row
            const headerRow = table.insertRow();
            Object.keys(message[0]).forEach(key => {
                const th = document.createElement('th');
                th.textContent = key;
                headerRow.appendChild(th);
            });
            
            // Create data rows
            message.forEach(row => {
                const dataRow = table.insertRow();
                Object.values(row).forEach(value => {
                    const cell = dataRow.insertCell();
                    if (typeof value === 'object') {
                        cell.textContent = JSON.stringify(value);
                    } else {
                        cell.textContent = value;
                    }
                });
            });
            
            messageElement.appendChild(table);
        } else {
            // Format JSON with syntax highlighting
            const pre = document.createElement('pre');
            pre.innerHTML = syntaxHighlight(JSON.stringify(message, null, 2));
            messageElement.appendChild(pre);
        }
    } else {
        messageElement.textContent = message;
    }
    
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function syntaxHighlight(json) {
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        var cls = 'color: #bdc3c7;'; // default
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'color: #e74c3c;'; // key
            } else {
                cls = 'color: #2ecc71;'; // string
            }
        } else if (/true|false/.test(match)) {
            cls = 'color: #3498db;'; // boolean
        } else if (/null/.test(match)) {
            cls = 'color: #9b59b6;'; // null
        }
        return '<span style="' + cls + '">' + match + '</span>';
    });
}
  
  sendMessage.addEventListener('click', () => {
    const message = messageInput.value.trim();
    if (message) {
      displayChatMessage(message, true);
      messageInput.value = '';
      
      fetch('http://localhost:8888/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: message })
      })
      .then(response => response.json())
      .then(data => {
        displayChatMessage(data.response, false);
      })
      .catch(error => {
        console.error('Error:', error);
        displayChatMessage('Sorry, there was an error processing your message.', false);
      });
    }
  });
  
  messageInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
      sendMessage.click();
    }
  });

  // form filling message communication

  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'postData') {
        const { data } = request;
        if (data.formFields.length === 0) {
            sendResponse({ fieldValues: null });
            return false;
        }

        const fillFormsButton = document.getElementById('fillForms');
        toggleSpinner(fillFormsButton, true);
        const comment = document.getElementById('fillFormsComment').value;
        data['comment'] = comment;
        console.log('Data to send:', data);
        fetch('http://localhost:8888/analyze-form', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            sendResponse({ fieldValues: data.fieldValues });
            showStatus('Forms filled successfully!');
        })
        .catch(error => {
            console.error('Error:', error);
            sendResponse({ fieldValues: null });
            showStatus('Error filling forms.', true);
        })
        .finally(() => {
            const fillFormsButton = document.getElementById('fillForms');
            toggleSpinner(fillFormsButton, false);
        });
        return true;  // Indicates that the response will be sent asynchronously
    }
});