window.initView = function(viewName) {
    if (viewName !== 'describe_photo') return;

    initializeCommon('text-areas', 'file-input', 'image-file', 'send-button', 'image/*', 'describe_photo');

    // Log DOM state for debugging
    console.log('DOM state:', {
        textAreas: document.querySelectorAll('.text-area').length,
        fileInput: !!document.getElementById('file-input'),
        imageFileInput: !!document.getElementById('image-file'),
        sendButton: !!document.getElementById('send-button')
    });

    window.renderHistoryItem = (item) => {
        if (item.type === 'user') {
            let settingsHtml = '';
            if (item.settings) {
                const global = item.settings.global || {};
                const view = item.settings.view || {};
                settingsHtml = `
                    <div class="settings-display">
                        Settings: Temperature=${global.temperature || '0.3'}, Max Tokens=${global.max_new_tokens || '128'}, 
                        Repeats=${view.repeats || '1'}, Keep Image=${view.keep_image_file ? 'Yes' : 'No'}, 
                        Keep Text=${view.keep_text ? 'Yes' : 'No'}
                    </div>
                `;
            }
            return `
                <strong>User:</strong>
                <p>Prompts: ${item.prompts.join(', ')}</p>
                <p>Image: ${item.imageFile}</p>
                ${settingsHtml}
            `;
        } else {
            return `
                <strong>Response:</strong>
                <p class="response-text">${item.description || ''}</p>
            `;
        }
    };

    window.sendRequest = async () => {
        const textAreas = document.querySelectorAll('.text-area');
        const imageFileInput = document.getElementById('image-file');
        const sendButton = document.getElementById('send-button');
        const fileInput = document.getElementById('file-input');

        console.log('sendRequest called, input state:', {
            textAreasCount: textAreas.length,
            imageFileInputExists: !!imageFileInput,
            imageFileSelected: imageFileInput ? imageFileInput.files.length : 0
        });

        const prompts = Array.from(textAreas)
            .map(ta => ta.value.trim())
            .filter(t => t);
        if (!prompts.length) {
            alert('Please enter at least one description prompt.');
            return;
        }
        if (!imageFileInput) {
            console.error('Image file input element not found');
            alert('Error: Image file input not found. Please check the page structure.');
            return;
        }
        if (!imageFileInput.files.length) {
            console.error('No image file selected');
            alert('Please select an image file.');
            return;
        }

        sendButton.disabled = true;

        const messageId = Date.now();
        // Include settings in history item
        const globalSettings = loadGlobalSettings();
        const viewSettings = loadViewSettings('describe_photo');
        window.addHistoryItem({
            id: messageId,
            type: 'user',
            prompts: prompts,
            imageFile: imageFileInput.files[0].name,
            settings: {
                global: { temperature: globalSettings.temperature, max_new_tokens: globalSettings.max_new_tokens },
                view: {
                    repeats: viewSettings.repeats,
                    keep_image_file: viewSettings.keep_image_file,
                    keep_text: viewSettings.keep_text
                }
            }
        });

        const formData = new FormData();
        formData.append('image_file', imageFileInput.files[0]);
        const payload = JSON.stringify({
            prompts: prompts,
            temperature: globalSettings.temperature,
            max_new_tokens: globalSettings.max_new_tokens,
            repeats: viewSettings.repeats
        });
        formData.append('payload', payload);

        console.log('Sending request to:', '/describe-photo/process_photo');
        console.log('FormData contents:', {
            image_file: imageFileInput.files[0].name,
            payload: payload
        });

        try {
            const response = await fetch('/describe-photo/process_photo', {
                method: 'POST',
                body: formData
            });
            console.log('Response status:', response.status, response.statusText);
            if (!response.ok) {
                const text = await response.text();
                console.log('Raw response:', text);
                throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
            }
            let data;
            try {
                data = await response.json();
            } catch (e) {
                const text = await response.text();
                console.log('Failed to parse JSON, raw response:', text);
                throw new Error('Failed to parse server response as JSON');
            }
            console.log('Response from /describe-photo/process_photo:', data);

            if (!data || data.status !== 'success') {
                throw new Error(data?.error || 'Server processing failed');
            }
            if (!data.descriptions) {
                throw new Error('No descriptions in response');
            }

            data.descriptions.forEach((desc, index) => {
                window.addHistoryItem({
                    id: `${messageId}-${index}`,
                    type: 'response',
                    description: desc.description
                });
            });
        } catch (error) {
            console.error('Fetch error:', error);
            console.log('Error details:', {
                message: error.message,
                stack: error.stack
            });
            alert(`Error: ${error.message}`);
            window.updatePendingStatus(messageId, { text: `Error: ${error.message}` });
        } finally {
            sendButton.disabled = false;
            if (!viewSettings.keep_text) {
                window.cleanupTextFields();
            }
            if (imageFileInput && !viewSettings.keep_image_file) {
                imageFileInput.value = '';
                let fileNameSpan = fileInput.querySelector('.file-name');
                if (fileNameSpan) {
                    fileNameSpan.textContent = 'Click or drag an image file here';
                }
                let reselectSpan = fileInput.querySelector('.file-reselect');
                if (reselectSpan) {
                    reselectSpan.remove();
                }
            }
        }
    };
};