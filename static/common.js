const MAX_HISTORY = 10;
let historyItems = [];
let currentView = null;

// View configuration
const VIEWS = [
    { name: 'voice_mimic', displayName: 'Voice Mimic', html: 'mimic_voice.html', js: 'mimic_voice.js' },
    { name: 'describe_photo', displayName: 'Describe Photo', html: 'describe_photo.html', js: 'describe_photo.js' }
];

// Default settings
const DEFAULT_GLOBAL_SETTINGS = {
    temperature: 0.3,
    max_new_tokens: 128
};

const DEFAULT_VIEW_SETTINGS = {
    voice_mimic: {
        repeats: 1,
        target_char_count: 500,
        keep_audio_file: false,
        keep_text: false,
        expert_panel_visible: false,
        mimick_prompt: "As a professional voice actor, mimic the voice style, pitch, tone, and speech patterns from reference file for the next message.",
        say_this_prompt: "Say this"
    },
    describe_photo: {
        repeats: 1,
        keep_image_file: false,
        keep_text: false,
        expert_panel_visible: false
    }
};

function initTabs() {
    const tabsContainer = document.getElementById('tabs');
    tabsContainer.innerHTML = '';
    VIEWS.forEach(view => {
        const tab = document.createElement('div');
        tab.className = 'tab';
        tab.dataset.view = view.name;
        tab.textContent = view.displayName;
        tab.addEventListener('click', () => loadView(view.name));
        tabsContainer.appendChild(tab);
    });
    // Default to voice_mimic
    loadView('voice_mimic');
}

async function loadView(viewName) {
    if (currentView === viewName) return;
    currentView = viewName;

    // Update tab active state
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.view === viewName);
    });

    // Load view HTML
    const view = VIEWS.find(v => v.name === viewName);
    if (!view) {
        console.error(`View ${viewName} not found`);
        return;
    }

    const viewContent = document.getElementById('view-content');
    try {
        const response = await fetch(`/static/${view.html}`);
        viewContent.innerHTML = await response.text();
        console.log(`Loaded ${view.html}, DOM state:`, {
            viewContentChildren: viewContent.childElementCount,
            fileInput: !!viewContent.querySelector('#file-input'),
            fileInputElement: !!viewContent.querySelector(`#${viewName === 'voice_mimic' ? 'audio-file' : 'image-file'}`)
        });
    } catch (error) {
        console.error(`Failed to load ${view.html}:`, error);
        viewContent.innerHTML = `<p>Error loading view</p>`;
        return;
    }

    // Load view-specific JS
    const existingScript = document.querySelector(`script[src="/static/${view.js}"]`);
    if (existingScript) {
        existingScript.remove();
    }
    const script = document.createElement('script');
    script.src = `/static/${view.js}`;
    script.onload = () => {
        if (window.initView) {
            window.initView(viewName);
        }
    };
    document.body.appendChild(script);
}

// Cookie management
function loadGlobalSettings() {
    const settings = Cookies.get('settings_global');
    return settings ? JSON.parse(settings) : { ...DEFAULT_GLOBAL_SETTINGS };
}

function saveGlobalSettings(settings) {
    Cookies.set('settings_global', JSON.stringify(settings), { expires: 365 });
}

function loadViewSettings(viewName) {
    const settings = Cookies.get(`settings_${viewName}`);
    return settings ? JSON.parse(settings) : { ...DEFAULT_VIEW_SETTINGS[viewName] };
}

function saveViewSettings(viewName, settings) {
    Cookies.set(`settings_${viewName}`, JSON.stringify(settings), { expires: 365 });
}

function loadHistory(viewName) {
    const history = Cookies.get(`history_${viewName}`);
    historyItems = history ? JSON.parse(history) : [];
    if (historyItems.length > MAX_HISTORY) {
        historyItems = historyItems.slice(-MAX_HISTORY);
    }
}

function saveHistory(viewName) {
    Cookies.set(`history_${viewName}`, JSON.stringify(historyItems), { expires: 365 });
}

function loadFile(viewName) {
    const file = Cookies.get(`file_${viewName}`);
    return file ? JSON.parse(file) : null;
}

function saveFile(viewName, file) {
    if (file) {
        Cookies.set(`file_${viewName}`, JSON.stringify({ name: file.name }), { expires: 365 });
    } else {
        Cookies.remove(`file_${viewName}`);
    }
}

// Text splitting logic (Voice Mimic only)
function splitText(text, targetCount) {
    const chunks = [];
    let currentChunk = '';
    const sentences = text.split(/(?<=[.!?])\s+/).filter(s => s.trim());
    
    for (const sentence of sentences) {
        if (currentChunk.length + sentence.length <= targetCount) {
            currentChunk += (currentChunk ? ' ' : '') + sentence;
        } else {
            if (currentChunk) chunks.push(currentChunk);
            currentChunk = sentence;
        }
    }
    if (currentChunk) chunks.push(currentChunk);
    
    // Handle paragraphs if no sentences exceed target
    if (chunks.length === 1 && chunks[0].length > targetCount) {
        chunks.length = 0;
        const paragraphs = text.split(/\n+/).filter(p => p.trim());
        for (const paragraph of paragraphs) {
            if (currentChunk.length + paragraph.length <= targetCount) {
                currentChunk += (currentChunk ? '\n' : '') + paragraph;
            } else {
                if (currentChunk) chunks.push(currentChunk);
                currentChunk = paragraph;
            }
        }
        if (currentChunk) chunks.push(currentChunk);
    }
    
    return chunks.length > 0 ? chunks : [text];
}

function initializeCommon(textAreasDivId, fileInputId, fileInputElementId, sendButtonId, fileAccept, viewName) {
    const textAreasDiv = document.getElementById(textAreasDivId);
    const fileInput = document.getElementById(fileInputId);
    const fileInputElement = document.getElementById(fileInputElementId);
    const sendButton = document.getElementById(sendButtonId);
    const expertButton = document.getElementById('expert-button');
    const expertPanel = document.getElementById('expert-panel');
    const clearFileButton = document.getElementById('clear-file');
    const resetButton = document.getElementById('reset-settings');

    // Load settings and history
    const globalSettings = loadGlobalSettings();
    const viewSettings = loadViewSettings(viewName);
    loadHistory(viewName);

    // Load saved file if keep_audio_file or keep_image_file is true
    const savedFile = loadFile(viewName);
    if (savedFile && viewSettings[viewName === 'voice_mimic' ? 'keep_audio_file' : 'keep_image_file']) {
        let fileNameSpan = fileInput.querySelector('.file-name');
        if (!fileNameSpan) {
            fileNameSpan = document.createElement('span');
            fileNameSpan.className = 'file-name';
            fileInput.insertBefore(fileNameSpan, fileInput.firstChild);
        }
        fileNameSpan.textContent = `Selected: ${savedFile.name}`;
        let reselectSpan = fileInput.querySelector('.file-reselect');
        if (!reselectSpan) {
            reselectSpan = document.createElement('span');
            reselectSpan.className = 'file-reselect';
            reselectSpan.textContent = 'Please re-select the file to send';
            fileInput.appendChild(reselectSpan);
        }
    }

    // Restore expert panel visibility
    if (viewSettings.expert_panel_visible) {
        expertPanel.classList.add('active');
    }

    // Log initial DOM state
    console.log('initializeCommon called, DOM state:', {
        textAreasDiv: !!textAreasDiv,
        fileInput: !!fileInput,
        fileInputElement: !!fileInputElement,
        sendButton: !!sendButton,
        expertButton: !!expertButton,
        expertPanel: !!expertPanel,
        clearFileButton: !!clearFileButton,
        resetButton: !!resetButton
    });

    // Expert panel toggle
    expertButton.addEventListener('click', () => {
        expertPanel.classList.toggle('active');
        viewSettings.expert_panel_visible = expertPanel.classList.contains('active');
        saveViewSettings(viewName, viewSettings);
    });

    // Initialize global settings
    document.getElementById('temperature').value = globalSettings.temperature;
    document.getElementById('max_new_tokens').value = globalSettings.max_new_tokens;

    // Initialize view-specific settings
    document.getElementById('repeats').value = viewSettings.repeats;
    document.getElementById('keep_text').checked = viewSettings.keep_text;
    if (viewName === 'voice_mimic') {
        document.getElementById('target_char_count').value = viewSettings.target_char_count;
        document.getElementById('keep_audio_file').checked = viewSettings.keep_audio_file;
        document.getElementById('mimick_prompt').value = viewSettings.mimick_prompt;
        document.getElementById('say_this_prompt').value = viewSettings.say_this_prompt;
        document.getElementById('split-text-button').addEventListener('click', () => {
            const textarea = textAreasDiv.querySelector('.text-area');
            const text = textarea.value;
            const chunks = splitText(text, viewSettings.target_char_count);
            if (chunks.length > 1) {
                textarea.value = chunks[0];
                chunks.slice(1).forEach(chunk => {
                    window.addTextArea();
                    textAreasDiv.lastChild.querySelector('.text-area').value = chunk;
                });
            }
        });
    } else {
        document.getElementById('keep_image_file').checked = viewSettings.keep_image_file;
    }

    // Reset settings
    resetButton.addEventListener('click', () => {
        const defaultGlobal = { ...DEFAULT_GLOBAL_SETTINGS };
        const defaultView = { ...DEFAULT_VIEW_SETTINGS[viewName] };
        saveGlobalSettings(defaultGlobal);
        saveViewSettings(viewName, defaultView);
        document.getElementById('temperature').value = defaultGlobal.temperature;
        document.getElementById('max_new_tokens').value = defaultGlobal.max_new_tokens;
        document.getElementById('repeats').value = defaultView.repeats;
        document.getElementById('keep_text').checked = defaultView.keep_text;
        if (viewName === 'voice_mimic') {
            document.getElementById('target_char_count').value = defaultView.target_char_count;
            document.getElementById('keep_audio_file').checked = defaultView.keep_audio_file;
            document.getElementById('mimick_prompt').value = defaultView.mimick_prompt;
            document.getElementById('say_this_prompt').value = defaultView.say_this_prompt;
        } else {
            document.getElementById('keep_image_file').checked = defaultView.keep_image_file;
        }
        if (!defaultView.expert_panel_visible) {
            expertPanel.classList.remove('active');
        }
    });

    // Save global settings on change
    ['temperature', 'max_new_tokens'].forEach(id => {
        document.getElementById(id).addEventListener('input', () => {
            globalSettings[id] = parseFloat(document.getElementById(id).value) || DEFAULT_GLOBAL_SETTINGS[id];
            saveGlobalSettings(globalSettings);
        });
    });

    // Save view-specific settings on change
    document.getElementById('repeats').addEventListener('input', () => {
        viewSettings.repeats = parseInt(document.getElementById('repeats').value) || DEFAULT_VIEW_SETTINGS[viewName].repeats;
        saveViewSettings(viewName, viewSettings);
    });
    document.getElementById('keep_text').addEventListener('change', () => {
        viewSettings.keep_text = document.getElementById('keep_text').checked;
        saveViewSettings(viewName, viewSettings);
    });
    if (viewName === 'voice_mimic') {
        document.getElementById('target_char_count').addEventListener('input', () => {
            viewSettings.target_char_count = parseInt(document.getElementById('target_char_count').value) || DEFAULT_VIEW_SETTINGS.voice_mimic.target_char_count;
            saveViewSettings(viewName, viewSettings);
        });
        document.getElementById('keep_audio_file').addEventListener('change', () => {
            viewSettings.keep_audio_file = document.getElementById('keep_audio_file').checked;
            saveViewSettings(viewName, viewSettings);
            if (!viewSettings.keep_audio_file) {
                saveFile(viewName, null);
                let fileNameSpan = fileInput.querySelector('.file-name');
                if (fileNameSpan) {
                    fileNameSpan.textContent = `Click or drag an audio file here`;
                }
                let reselectSpan = fileInput.querySelector('.file-reselect');
                if (reselectSpan) {
                    reselectSpan.remove();
                }
            }
        });
        document.getElementById('mimick_prompt').addEventListener('input', () => {
            viewSettings.mimick_prompt = document.getElementById('mimick_prompt').value || DEFAULT_VIEW_SETTINGS.voice_mimic.mimick_prompt;
            saveViewSettings(viewName, viewSettings);
        });
        document.getElementById('say_this_prompt').addEventListener('input', () => {
            viewSettings.say_this_prompt = document.getElementById('say_this_prompt').value || DEFAULT_VIEW_SETTINGS.voice_mimic.say_this_prompt;
            saveViewSettings(viewName, viewSettings);
        });
    } else {
        document.getElementById('keep_image_file').addEventListener('change', () => {
            viewSettings.keep_image_file = document.getElementById('keep_image_file').checked;
            saveViewSettings(viewName, viewSettings);
            if (!viewSettings.keep_image_file) {
                saveFile(viewName, null);
                let fileNameSpan = fileInput.querySelector('.file-name');
                if (fileNameSpan) {
                    fileNameSpan.textContent = `Click or drag an image file here`;
                }
                let reselectSpan = fileInput.querySelector('.file-reselect');
                if (reselectSpan) {
                    reselectSpan.remove();
                }
            }
        });
    }

    // Add text area
    window.addTextArea = () => {
        const container = document.createElement('div');
        container.className = 'text-area-container';
        const textarea = document.createElement('textarea');
        textarea.className = 'text-area';
        textarea.placeholder = 'Enter prompt';
        const removeButton = document.createElement('button');
        removeButton.className = 'remove-text';
        removeButton.textContent = '×';
        removeButton.addEventListener('click', () => container.remove());
        container.appendChild(textarea);
        container.appendChild(removeButton);
        textAreasDiv.appendChild(container);
        attachTextAreaEvents(textarea);
    };

    // Attach key events to text areas
    function attachTextAreaEvents(textarea) {
        textarea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.shiftKey) {
                e.preventDefault();
                window.addTextArea();
            } else if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                window.sendRequest();
            }
        });
    }

    // Initialize existing text areas
    textAreasDiv.querySelectorAll('.text-area').forEach(attachTextAreaEvents);

    // File input click
    fileInput.addEventListener('click', () => {
        if (fileInputElement) {
            fileInputElement.click();
        } else {
            console.error('File input element not found for click event');
        }
    });

    // File input change
    fileInputElement.addEventListener('change', () => {
        console.log('File input changed, DOM state:', {
            fileInputElementExists: !!fileInputElement,
            filesCount: fileInputElement ? fileInputElement.files.length : 0
        });
        if (fileInputElement.files.length) {
            let fileNameSpan = fileInput.querySelector('.file-name');
            if (!fileNameSpan) {
                fileNameSpan = document.createElement('span');
                fileNameSpan.className = 'file-name';
                fileInput.insertBefore(fileNameSpan, fileInput.firstChild);
            }
            fileNameSpan.textContent = `Selected: ${fileInputElement.files[0].name}`;
            let reselectSpan = fileInput.querySelector('.file-reselect');
            if (reselectSpan) {
                reselectSpan.remove();
            }
            if (viewSettings[viewName === 'voice_mimic' ? 'keep_audio_file' : 'keep_image_file']) {
                saveFile(viewName, fileInputElement.files[0]);
            }
            if (window.onFileChange) {
                window.onFileChange(fileInputElement.files[0]);
            }
        } else {
            let fileNameSpan = fileInput.querySelector('.file-name');
            if (fileNameSpan) {
                fileNameSpan.textContent = `Click or drag a ${viewName === 'voice_mimic' ? 'audio' : 'image'} file here`;
            }
            let reselectSpan = fileInput.querySelector('.file-reselect');
            if (reselectSpan) {
                reselectSpan.remove();
            }
            saveFile(viewName, null);
            if (window.onFileClear) {
                window.onFileClear();
            }
        }
    });

    // Drag and drop
    fileInput.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileInput.classList.add('dragover');
    });
    fileInput.addEventListener('dragleave', () => {
        fileInput.classList.remove('dragover');
    });
    fileInput.addEventListener('drop', (e) => {
        e.preventDefault();
        fileInput.classList.remove('dragover');
        if (fileInputElement) {
            fileInputElement.files = e.dataTransfer.files;
            console.log('Drag and drop, DOM state:', {
                fileInputElementExists: !!fileInputElement,
                filesCount: fileInputElement.files.length,
                inputElement: !!fileInput.querySelector(`#${fileInputElementId}`)
            });
            if (fileInputElement.files.length) {
                let fileNameSpan = fileInput.querySelector('.file-name');
                if (!fileNameSpan) {
                    fileNameSpan = document.createElement('span');
                    fileNameSpan.className = 'file-name';
                    fileInput.insertBefore(fileNameSpan, fileInput.firstChild);
                }
                fileNameSpan.textContent = `Selected: ${fileInputElement.files[0].name}`;
                let reselectSpan = fileInput.querySelector('.file-reselect');
                if (reselectSpan) {
                    reselectSpan.remove();
                }
                if (viewSettings[viewName === 'voice_mimic' ? 'keep_audio_file' : 'keep_image_file']) {
                    saveFile(viewName, fileInputElement.files[0]);
                }
                if (window.onFileChange) {
                    window.onFileChange(fileInputElement.files[0]);
                }
            }
        } else {
            console.error('File input element not found for drop event');
        }
    });

    // Clear file
    clearFileButton.addEventListener('click', () => {
        if (fileInputElement) {
            fileInputElement.value = '';
            let fileNameSpan = fileInput.querySelector('.file-name');
            if (fileNameSpan) {
                fileNameSpan.textContent = `Click or drag a ${viewName === 'voice_mimic' ? 'audio' : 'image'} file here`;
            }
            let reselectSpan = fileInput.querySelector('.file-reselect');
            if (reselectSpan) {
                reselectSpan.remove();
            }
            saveFile(viewName, null);
            if (window.onFileClear) {
                window.onFileClear();
            }
        }
    });

    // Clean up text fields after send
    window.cleanupTextFields = () => {
        const containers = textAreasDiv.querySelectorAll('.text-area-container');
        if (containers.length > 1) {
            Array.from(containers).slice(1).forEach(container => container.remove());
        }
        const firstTextarea = textAreasDiv.querySelector('.text-area');
        if (firstTextarea) {
            firstTextarea.value = '';
        }
    };

    // History management
    window.addHistoryItem = (item) => {
        historyItems.push(item);
        if (historyItems.length > MAX_HISTORY) {
            historyItems.shift();
        }
        window.updateHistory();
        saveHistory(viewName);
    };

    window.updateHistory = () => {
        const historyDiv = document.getElementById('history');
        if (!historyDiv) return;
        historyDiv.innerHTML = '';
        historyItems.forEach(item => {
            const div = document.createElement('div');
            div.className = `history-item ${item.type} ${item.pending ? 'pending' : ''}`;
            div.dataset.id = item.id;
            div.innerHTML = window.renderHistoryItem ? window.renderHistoryItem(item) : '';
            historyDiv.prepend(div);
        });
    };

    window.updatePendingStatus = (id, data) => {
        const item = historyItems.find(i => i.id === id);
        if (item) {
            item.pending = false;
            Object.assign(item, data);
            window.updateHistory();
            saveHistory(viewName);
        }
    };
}

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
});