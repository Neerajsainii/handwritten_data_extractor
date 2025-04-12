document.addEventListener('DOMContentLoaded', function() {
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const processBtn = document.getElementById('processBtn');
    const copyBtn = document.getElementById('copyBtn');
    const result = document.getElementById('result');
    const loader = document.getElementById('loader');
    const status = document.getElementById('status');
    
    // Get CSRF token for AJAX requests
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // Reset UI state
    function resetUI() {
        result.innerHTML = 'Your extracted text will appear here';
        copyBtn.style.display = 'none';
        status.textContent = '';
        status.className = '';
    }
    
    // Handle file selection via button
    uploadBtn.addEventListener('click', () => {
        fileInput.click();
    });
    
    // Handle file selection change
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            processBtn.disabled = false;
            
            // Show file info
            const fileSize = (file.size / 1024).toFixed(2);
            const fileInfo = `${file.name} (${fileSize} KB)`;
            dropArea.innerHTML = `<i class="fa-solid fa-file-lines upload-icon"></i><p>${fileInfo}</p>`;
            
            // Reset previous results
            resetUI();
        }
    });
    
    // Handle drag and drop
    dropArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropArea.style.background = 'rgba(67, 97, 238, 0.1)';
        dropArea.classList.add('active');
    });
    
    dropArea.addEventListener('dragleave', () => {
        dropArea.style.background = 'rgba(67, 97, 238, 0.05)';
        dropArea.classList.remove('active');
    });
    
    dropArea.addEventListener('drop', (e) => {
        e.preventDefault();
        dropArea.style.background = 'rgba(67, 97, 238, 0.05)';
        dropArea.classList.remove('active');
        
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            const file = fileInput.files[0];
            processBtn.disabled = false;
            
            // Show file info
            const fileSize = (file.size / 1024).toFixed(2);
            const fileInfo = `${file.name} (${fileSize} KB)`;
            dropArea.innerHTML = `<i class="fa-solid fa-file-lines upload-icon"></i><p>${fileInfo}</p>`;
            
            // Reset previous results
            resetUI();
        }
    });
    
    // Handle click on drop area
    dropArea.addEventListener('click', () => {
        fileInput.click();
    });
    
    // Handle process button click
    processBtn.addEventListener('click', () => {
        if (fileInput.files.length === 0) return;
        
        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('csrfmiddlewaretoken', csrfToken);
        
        // Show loader and status
        loader.style.display = 'block';
        result.innerHTML = '<div class="processing-message"><i class="fa-solid fa-gear fa-spin"></i> Processing your document...</div>';
        status.textContent = 'Processing...';
        status.className = 'status-processing';
        
        // Disable process button during processing
        processBtn.disabled = true;
        
        // Send request to server
        fetch('/process/', {
            method: 'POST',
            body: formData,
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with status ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Hide loader
            loader.style.display = 'none';
            processBtn.disabled = false;
            
            if (data.error) {
                result.innerHTML = `<div class="error-message"><i class="fa-solid fa-circle-exclamation"></i> ${data.error}</div>`;
                copyBtn.style.display = 'none';
                status.textContent = 'Error';
                status.className = 'status-error';
            } else {
                // Display formatted text
                displayFormattedText(data.text || 'No text found.');
                copyBtn.style.display = 'inline-block';
                status.textContent = 'Completed';
                status.className = 'status-success';
                
                // Add success animation to the result container
                document.querySelector('.result-container').classList.add('success-flash');
                setTimeout(() => {
                    document.querySelector('.result-container').classList.remove('success-flash');
                }, 1000);
            }
        })
        .catch(error => {
            // Hide loader
            loader.style.display = 'none';
            processBtn.disabled = false;
            
            result.innerHTML = `<div class="error-message"><i class="fa-solid fa-circle-exclamation"></i> ${error.message}</div>`;
            copyBtn.style.display = 'none';
            status.textContent = 'Error';
            status.className = 'status-error';
        });
    });
    
    // Function to display text with formatting preserved
    function displayFormattedText(text) {
        // Check if the text is empty
        if (!text.trim()) {
            result.innerHTML = '<div class="notice-message"><i class="fa-solid fa-info-circle"></i> No text was found in the document.</div>';
            return;
        }
        
        // Check if the text contains tabs (likely a table)
        if (text.includes('\t')) {
            // Convert to HTML table
            const rows = text.split('\n');
            let tableHtml = '<table class="ocr-table">';
            
            for (const row of rows) {
                if (!row.trim()) continue; // Skip empty lines
                
                tableHtml += '<tr>';
                const cells = row.split('\t');
                
                for (const cell of cells) {
                    tableHtml += `<td>${cell.trim()}</td>`;
                }
                
                tableHtml += '</tr>';
            }
            
            tableHtml += '</table>';
            result.innerHTML = tableHtml;
        } else {
            // Regular text formatting
            const formattedText = text
                .replace(/\n/g, '<br>')
                .replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;')
                .replace(/ {2}/g, '&nbsp;&nbsp;');
                
            result.innerHTML = formattedText;
        }
        
        // Store the original text for copying
        result.setAttribute('data-original-text', text);
    }
    
    // Handle copy button click
    copyBtn.addEventListener('click', () => {
        // Get the original text without HTML formatting
        const textToCopy = result.getAttribute('data-original-text') || result.textContent;
        
        navigator.clipboard.writeText(textToCopy)
            .then(() => {
                const originalText = copyBtn.textContent;
                copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
                copyBtn.classList.add('copied');
                
                setTimeout(() => {
                    copyBtn.innerHTML = '<i class="fa-solid fa-copy"></i> Copy Text';
                    copyBtn.classList.remove('copied');
                }, 2000);
            })
            .catch(err => {
                console.error('Could not copy text: ', err);
                status.textContent = 'Copy failed';
                status.className = 'status-error';
            });
    });
}); 