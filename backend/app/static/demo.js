document.addEventListener('DOMContentLoaded', function() {
    // Form submission loading
    document.getElementById('queryForm').addEventListener('submit', function(event) {
        // Prevent multiple form submissions
        var form = this;
        
        if (form.classList.contains('submitting')) {
            event.preventDefault();
            return false;
        }
        
        // Mark form as submitting
        form.classList.add('submitting');
        
        // Show loading message
        document.getElementById('loadingMessage').style.display = 'block';
        
        //Let's also clear out previous responses and statuses
        var answerBlock = document.getElementsByClassName('answers-wrapper');
        var transformBlock = document.getElementsByClassName('transformed-query');

        if(answerBlock != null)
        {
            answerBlock[0].style.display = 'none';
        }

        if(transformBlock != null)
        {
            transformBlock[0].style.display = 'none';
        }

    });
    
    // Toggle comparison option
    function toggleComparisonOption() {
        var filterCheckbox = document.getElementById('filter_expired');
        var comparisonOption = document.getElementById('comparisonOption');
        
        if (filterCheckbox.checked) {
            comparisonOption.style.display = 'inline';
        } else {
            comparisonOption.style.display = 'none';
        }
    }
    
    // Update bylaws limit options
    function updateBylawsLimitOptions() {
        var enhancedSearch = document.getElementById('enhanced_search');
        var bylawsLimit = document.getElementById('bylaws_limit');
        var options = bylawsLimit.options;
        
        for (var i = 0; i < options.length; i++) {
            var value = options[i].value;
            if (enhancedSearch.checked) {
                var enhancedValue = parseInt(value) + 10;
                options[i].text = value + "-" + enhancedValue;
            } else {
                options[i].text = value;
            }
        }
    }
    
    // Initialize bug report buttons
    function initBugReportButtons() {
        // Get all bug report buttons
        const bugButtons = document.querySelectorAll('.bug-report-btn');
        
        // Add click event listeners to each button
        bugButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const answerType = this.getAttribute('data-answer-type');
                console.log('Bug report clicked for:', answerType);
                
                try {
                    const url = createBugReportUrl(answerType);
                    console.log('Opening URL:', url);
                    window.open(url, '_blank');
                } catch (error) {
                    console.error('Error creating bug report URL:', error);
                    alert('Error creating bug report: ' + error.message);
                }
            });
        });
        
        console.log('Bug report buttons initialized:', bugButtons.length);
    }
    
    // Bug report function - Create GitHub issue URL with context data
    function createBugReportUrl(answerType) {
        console.log('Creating bug report for answer type:', answerType);
        
        // Get query and settings
        const query = document.getElementById('query').value;
        const model = document.getElementById('model').value;
        const bylawsLimit = document.getElementById('bylaws_limit').value;
        const enhancedSearch = document.getElementById('enhanced_search').checked;
        const bylawStatus = document.getElementById('bylaw_status').value;
        
        // Get transformed query if available
        let transformedQuery = '';
        const transformedQuerySection = document.querySelector('.transformed-query');
        if (transformedQuerySection) {
            const transformedQueryParagraph = transformedQuerySection.querySelector('p:last-child');
            if (transformedQueryParagraph) {
                transformedQuery = transformedQueryParagraph.textContent.replace('Transformed for Legal Search:', '').trim();
            }
        }
        
        // Get bylaw IDs and enhanced search bylaws
        let bylawIds = '';
        let enhancedBylaws = '';
        
        const footerElement = document.querySelector('.answer-container small i');
        if (footerElement) {
            // Get all lines from the footer
            const footerLines = footerElement.innerHTML.split('<br>');
            
            // Find bylaw IDs
            const bylawInfoLine = footerLines.find(line => line.startsWith('Retrieved By-laws:'));
            if (bylawInfoLine) {
                bylawIds = bylawInfoLine.replace('Retrieved By-laws:', '').trim();
            }
            
            // Find enhanced search bylaws if applicable
            if (enhancedSearch) {
                const enhancedBylawsLine = footerLines.find(line => line.includes('Bylaws found by Enhanced Search:'));
                if (enhancedBylawsLine) {
                    enhancedBylaws = enhancedBylawsLine.replace('Bylaws found by Enhanced Search:', '').trim();
                }
            }
        }
        
        // Get timing info
        let timingInfo = '';
        if (footerElement) {
            const timingInfoLine = Array.from(footerElement.innerHTML.split('<br>')).find(line => line.startsWith('Timings:'));
            if (timingInfoLine) {
                timingInfo = timingInfoLine.replace('Timings:', '').trim();
            }
        }
        
        // Get the specific answer content
        let answerContent = '';
        
        if (answerType === 'complete') {
            // Handle complete answer (first container in compare mode)
            const completeContainer = document.querySelector('.answers-wrapper.side-by-side .answer-container:nth-child(1) div:nth-child(3), .answer-container:nth-child(1) div:nth-child(3)');
            if (completeContainer) {
                answerContent = completeContainer.innerHTML;
            } else {
                console.warn('Complete answer container not found');
            }
        } else if (answerType === 'filtered') {
            // Handle filtered answer (second container in compare mode)
            const filteredContainer = document.querySelector('.answers-wrapper.side-by-side .answer-container:nth-child(2) div:nth-child(3), .answer-container:nth-child(2) div:nth-child(3)');
            if (filteredContainer) {
                answerContent = filteredContainer.innerHTML;
            } else {
                console.warn('Filtered answer container not found');
            }
        } else if (answerType === 'simplified') {
            // For simplified, we need to check if we're in compare mode or regular mode
            const isCompareMode = document.querySelector('.answer-container:nth-child(3)') !== null;
            
            let simplifiedContainer = null;
            if (isCompareMode) {
                // Third container in compare mode
                simplifiedContainer = document.querySelector('.answer-container:nth-child(3) div:nth-child(3)');
            } else {
                // Only container in regular mode
                simplifiedContainer = document.querySelector('.answer-container div:nth-child(2)');
            }
            
            if (simplifiedContainer) {
                // Copy the HTML but exclude the hr and everything after it
                answerContent = simplifiedContainer.innerHTML.split('<hr>')[0];
            } else {
                console.warn('Simplified answer container not found');
            }
        }
        
        // Format the context data as Markdown
        const markdownContext = `## Bug Report Details

### Query Information
- **User Query:** ${query}
- **Gemini Model:** ${model}
- **Bylaws Limit:** ${bylawsLimit}
- **Enhanced Search:** ${enhancedSearch ? 'On' : 'Off'}
- **Bylaw Status Filter:** ${bylawStatus}
${transformedQuery ? `- **Transformed Query:** ${transformedQuery}` : ''}

### System Information
- **Retrieved By-laws:** ${bylawIds}
${enhancedBylaws ? `- **Bylaws found by Enhanced Search:** ${enhancedBylaws}` : ''}
- **Timing:** ${timingInfo}
- **Answer Type:** ${answerType}

### Response Content
\`\`\`html
${answerContent}
\`\`\`
`;

        // Log the formatted markdown for debugging
        console.log('Bug report markdown:', markdownContext);
        
        // Encode the markdown as a URL-safe string
        const encodedContext = encodeURIComponent(markdownContext);
        
        // Create the GitHub issue URL
        return `https://github.com/Cadence-GitHub/Stouffville-By-laws-AI/issues/new?template=bug_report.yml&additional_context=${encodedContext}`;
    }
    
    // Initialize form controls
    if (document.getElementById('filter_expired')) {
        document.getElementById('filter_expired').addEventListener('change', toggleComparisonOption);
        toggleComparisonOption();
    }
    
    if (document.getElementById('enhanced_search')) {
        document.getElementById('enhanced_search').addEventListener('change', updateBylawsLimitOptions);
        updateBylawsLimitOptions();
    }

    /* Auto Suggest begins*/

    // Get the query input element
    const queryInput = document.getElementById('query');
    
    // Create autocomplete container
    const autocompleteContainer = document.createElement('div');
    autocompleteContainer.className = 'autocomplete-container';
    autocompleteContainer.style.display = 'none';
    
    // Insert the autocomplete container after the query input
    queryInput.parentNode.insertBefore(autocompleteContainer, queryInput.nextSibling);
    
    // Track current autocomplete state
    let currentSuggestions = [];
    let selectedIndex = -1;
    let typingTimer;
    const doneTypingInterval = 300; // Wait 300ms after user stops typing
    
    // Handle input changes
    queryInput.addEventListener('input', function() {
        // Clear any existing timer
        clearTimeout(typingTimer);
        
        // Hide suggestions if input is empty or too short
        if (!this.value.trim() || this.value.trim().length < 3) {
            hideAutocomplete();
            return;
        }
        
        // Set a timer to fetch suggestions
        typingTimer = setTimeout(() => fetchSuggestions(this.value), doneTypingInterval);
    });
    
    // Handle keydown events for navigation
    queryInput.addEventListener('keydown', function(e) {
        if (!autocompleteContainer.children.length || autocompleteContainer.style.display === 'none') {
            return;
        }
        
        // Down arrow
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            selectedIndex = Math.min(selectedIndex + 1, autocompleteContainer.children.length - 1);
            updateSelectedSuggestion();
        } 
        // Up arrow
        else if (e.key === 'ArrowUp') {
            e.preventDefault();
            selectedIndex = Math.max(selectedIndex - 1, -1);
            updateSelectedSuggestion();
        }
        // Enter
        else if (e.key === 'Enter' && selectedIndex >= 0) {
            e.preventDefault();
            selectSuggestion(selectedIndex);
        }
        // Escape
        else if (e.key === 'Escape') {
            hideAutocomplete();
        }
    });
    
    // Hide autocomplete when clicking outside
    document.addEventListener('click', function(e) {
        if (!queryInput.contains(e.target) && !autocompleteContainer.contains(e.target)) {
            hideAutocomplete();
        }
    });
    
    // Fetch suggestions from the API
    function fetchSuggestions(query) {
        fetch('/api/autocomplete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: query })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Autocomplete error:', data.error);
                return;
            }
            
            // Update suggestions
            currentSuggestions = data.suggestions || [];
            // Store retrieval time if available
            retrievalTime = data.retrieval_time || 0;
            displaySuggestions(retrievalTime);
        })
        .catch(error => {
            console.error('Error fetching autocomplete suggestions:', error);
        });
    }
    
    // Display suggestions in the DOM
    function displaySuggestions(retrievalTime = 0) {
        // Clear previous suggestions
        autocompleteContainer.innerHTML = '';
        selectedIndex = -1;
        
        // If no suggestions, hide the container
        if (!currentSuggestions.length) {
            hideAutocomplete();
            return;
        }
        
        // Add each suggestion to the container
        currentSuggestions.forEach((suggestion, index) => {
            const suggestionElement = document.createElement('div');
            suggestionElement.className = 'autocomplete-suggestion';
            
            // Add timing info to the first suggestion
            if (index === 0 && retrievalTime) {
                const formattedTime = (retrievalTime * 1000).toFixed(2);
                suggestionElement.innerHTML = `${suggestion} <span class="timing-info">(${formattedTime}ms)</span>`;
            } else {
                suggestionElement.textContent = suggestion;
            }
            
            // Handle click on suggestion
            suggestionElement.addEventListener('click', () => {
                selectSuggestion(index);
            });
            
            // Handle mouseover
            suggestionElement.addEventListener('mouseover', () => {
                selectedIndex = index;
                updateSelectedSuggestion();
            });
            
            autocompleteContainer.appendChild(suggestionElement);
        });
        
        // Calculate position relative to the input field
        const inputRect = queryInput.getBoundingClientRect();
        const formRect = queryInput.parentNode.getBoundingClientRect();
        const leftOffset = inputRect.left - formRect.left;
        
        // Position the container below the input field
        autocompleteContainer.style.position = 'absolute';
        autocompleteContainer.style.top = `${inputRect.height}px`;
        autocompleteContainer.style.left = `${leftOffset}px`;
        autocompleteContainer.style.width = `${inputRect.width}px`;
        
        // Show the container
        autocompleteContainer.style.display = 'block';
    }
    
    // Update the selected suggestion in the UI
    function updateSelectedSuggestion() {
        Array.from(autocompleteContainer.children).forEach((element, index) => {
            if (index === selectedIndex) {
                element.classList.add('selected');
            } else {
                element.classList.remove('selected');
            }
        });
    }
    
    // Select a suggestion and fill the input
    function selectSuggestion(index) {
        if (index >= 0 && index < currentSuggestions.length) {
            queryInput.value = currentSuggestions[index];
            hideAutocomplete();
            queryInput.focus();
        }
    }
    
    // Hide the autocomplete container
    function hideAutocomplete() {
        autocompleteContainer.style.display = 'none';
        selectedIndex = -1;
    }

    /*Auto Suggest ends*/
    
    // Bylaw sidebar functionality
    console.log('DOM loaded, initializing bylaw sidebar');
    
    // Get elements
    const sidebar = document.getElementById('bylaw-sidebar');
    const resizer = document.getElementById('sidebar-resizer');
    const frame = document.getElementById('bylaw-frame');
    
    // Debug check to see if elements exist
    console.log('Sidebar element:', sidebar);
    console.log('Resizer element:', resizer);
    console.log('Frame element:', frame);
    
    // Only proceed if all elements exist
    if (!sidebar || !resizer || !frame) {
        console.error('Required sidebar elements not found');
        return;
    }
    
    let isResizing = false;
    
    // Handle bylaw links
    function handleBylawLinks() {
        document.querySelectorAll('a[href*="bylawViewer.html"]').forEach(link => {
            link.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                const isMobile = window.innerWidth <= 768;
                
                // Extract bylaw ID
                const bylawMatch = href.match(/[?&]bylaw=([^&]+)/);
                if (!bylawMatch) return true;
                
                const bylawId = bylawMatch[1];
                console.log('Bylaw link clicked:', bylawId);
                
                if (isMobile) {
                    // On mobile, let it open in new tab
                    return true;
                } else {
                    // On desktop, open in sidebar
                    e.preventDefault();
                    openBylawSidebar(bylawId);
                    return false;
                }
            });
        });
    }
    
    function openBylawSidebar(bylawId) {    
        // First clear the existing iframe content
        frame.src = 'about:blank';
        
        // Force a reflow
        void frame.offsetWidth;
        
        // Add a unique timestamp as a fragment identifier (doesn't affect query params)
        const timestamp = new Date().getTime();
        frame.src = `/static/bylawViewer.html?bylaw=${bylawId}#${timestamp}`;
        sidebar.classList.add('active');
        document.body.classList.add('sidebar-open');
    }
    
    function closeBylawSidebar() {
        sidebar.classList.remove('active');
        document.body.classList.remove('sidebar-open');
        setTimeout(() => { frame.src = 'about:blank'; }, 300);
    }
    
    // Set up resize functionality
    if (resizer) {
        resizer.addEventListener('mousedown', function(e) {
            isResizing = true;
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', stopResize);
            e.preventDefault();
        });
    }
    
    function handleMouseMove(e) {
        if (!isResizing) return;
        
        const windowWidth = window.innerWidth;
        const sidebarWidth = windowWidth - e.clientX;
        const percentage = Math.min(Math.max((sidebarWidth / windowWidth) * 100, 30), 70);
        
        sidebar.style.width = `${percentage}%`;
        document.querySelector('.container').style.marginRight = `${percentage}%`;
    }
    
    function stopResize() {
        isResizing = false;
        document.removeEventListener('mousemove', handleMouseMove);
    }
    
    // Handle messages from iframe
    window.addEventListener('message', function(event) {
        if (event.data === 'close-bylaw-sidebar') {
            closeBylawSidebar();
        }
    });
    
    // Watch for new content
    const observer = new MutationObserver(function() {
        handleBylawLinks();
        initBugReportButtons(); // Initialize bug report buttons when content changes
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Initial setup
    handleBylawLinks();
    initBugReportButtons(); // Initialize bug report buttons on page load
    console.log('Bylaw sidebar initialized');
    
    // Provincial Laws functionality
    const provincialLawsBtn = document.getElementById('provincialLawsBtn');
    const provincialLawsForm = document.getElementById('provincialLawsForm');
    const fetchProvincialLawsBtn = document.getElementById('fetchProvincialLaws');
    const provincialLawsResult = document.getElementById('provincialLawsResult');
    const provincialContent = document.getElementById('provincialContent');
    const sourcesList = document.getElementById('sourcesList');
    const provincialLoading = document.getElementById('provincialLoading');
    
    // Toggle the provincial laws form when button is clicked
    if (provincialLawsBtn) {
        provincialLawsBtn.addEventListener('click', function() {
            if (provincialLawsForm.style.display === 'none') {
                provincialLawsForm.style.display = 'block';
            } else {
                provincialLawsForm.style.display = 'none';
            }
        });
    }
    
    // Fetch provincial laws when the fetch button is clicked
    if (fetchProvincialLawsBtn) {
        fetchProvincialLawsBtn.addEventListener('click', function() {
            const bylawType = document.getElementById('bylaw_type').value.trim();
            const provincialModel = document.getElementById('provincial_model').value;
            
            if (bylawType === '') {
                alert('Please enter a bylaw type');
                return;
            }
            
            // Show loading indicator
            provincialLoading.style.display = 'block';
            provincialContent.innerHTML = '';
            sourcesList.innerHTML = '';
            provincialLawsResult.style.display = 'block';
            
            // Fetch provincial laws data
            fetch('/api/provincial_laws', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    bylaw_type: bylawType,
                    model: provincialModel
                })
            })
            .then(response => response.json())
            .then(data => {
                // Hide loading indicator
                provincialLoading.style.display = 'none';
                
                if (data.error) {
                    provincialContent.innerHTML = `<div class="error">${data.error}</div>`;
                    return;
                }
                
                // Display the provincial information
                provincialContent.innerHTML = data.provincial_info;
                
                // Display sources if available
                if (data.sources && data.sources.length > 0) {
                    sourcesList.innerHTML = '';
                    data.sources.forEach(source => {
                        const li = document.createElement('li');
                        li.innerHTML = `<a href="${source.url}" target="_blank">${source.title}</a>`;
                        sourcesList.appendChild(li);
                    });
                } else {
                    sourcesList.innerHTML = '<li>No sources available</li>';
                }
                
                // Add timing information if available
                if (data.timings && data.timings.processing_time) {
                    const processingTime = (data.timings.processing_time).toFixed(2);
                    const timingInfo = document.createElement('div');
                    timingInfo.className = 'timing-info';
                    timingInfo.textContent = `Processing time: ${processingTime} seconds`;
                    provincialContent.appendChild(document.createElement('hr'));
                    provincialContent.appendChild(timingInfo);
                }
            })
            .catch(error => {
                provincialLoading.style.display = 'none';
                provincialContent.innerHTML = `<div class="error">Error: ${error.message}</div>`;
                console.error('Error fetching provincial laws:', error);
            });
        });
    }

    // Voice query functionality
    const voiceBtn = document.getElementById('voiceBtn');
    const voiceForm = document.getElementById('voiceForm');
    const startRecordingBtn = document.getElementById('startRecording');
    const stopRecordingBtn = document.getElementById('stopRecording');
    const recordingIndicator = document.getElementById('recordingIndicator');

    let mediaRecorder;
    let audioChunks = [];
    let recordingTimeout;

    // Toggle the voice form when button is clicked
    if (voiceBtn) {
        voiceBtn.addEventListener('click', function() {
            if (voiceForm.style.display === 'none') {
                voiceForm.style.display = 'block';
            } else {
                voiceForm.style.display = 'none';
            }
        });
    }

    // Start recording audio
    if (startRecordingBtn) {
        startRecordingBtn.addEventListener('click', function() {
            // Unified getUserMedia across browsers and secure context check
            let getUserMediaFunc;
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                getUserMediaFunc = (constraints) => navigator.mediaDevices.getUserMedia(constraints);
            } else if (navigator.getUserMedia) {
                getUserMediaFunc = (constraints) => new Promise((resolve, reject) => navigator.getUserMedia(constraints, resolve, reject));
            } else if (navigator.webkitGetUserMedia) {
                getUserMediaFunc = (constraints) => new Promise((resolve, reject) => navigator.webkitGetUserMedia(constraints, resolve, reject));
            } else if (navigator.mozGetUserMedia) {
                getUserMediaFunc = (constraints) => new Promise((resolve, reject) => navigator.mozGetUserMedia(constraints, resolve, reject));
            } else {
                // Voice recording not available: prompt user to use HTTPS demo page
                const secureUrl = `https://${window.location.hostname}:5443/api/demo`;
                alert(`Voice recording requires a secure connection. Please open the demo over HTTPS at ${secureUrl}`);
                return;
            }

            getUserMediaFunc({ audio: true })
                .then(stream => {
                    mediaRecorder = new MediaRecorder(stream);
                    mediaRecorder.ondataavailable = function(e) {
                        audioChunks.push(e.data);
                    };
                    mediaRecorder.onstart = function() {
                        recordingIndicator.style.display = 'inline';
                        stopRecordingBtn.style.display = 'inline';
                        startRecordingBtn.style.display = 'none';
                    };
                    mediaRecorder.onstop = function() {
                        recordingIndicator.style.display = 'none';
                        stopRecordingBtn.style.display = 'none';
                        startRecordingBtn.style.display = 'inline';

                        const audioBlob = new Blob(audioChunks, { type: audioChunks[0].type });
                        const reader = new FileReader();
                        reader.onloadend = function() {
                            const base64data = reader.result.split(',')[1];
                            fetch('/api/voice_query', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ audio_data: base64data, mime_type: audioBlob.type })
                            })
                            .then(response => response.json())
                            .then(data => {
                                if (data.transcript === 'NO_BYLAW_QUESTION_DETECTED') {
                                    alert('No bylaw question detected');
                                } else if (data.error) {
                                    alert(data.error);
                                } else {
                                    document.getElementById('query').value = data.transcript;
                                }
                                audioChunks = [];
                            })
                            .catch(error => {
                                console.error('Voice query error:', error);
                                alert('Voice query failed');
                                audioChunks = [];
                            });
                        };
                        reader.readAsDataURL(audioBlob);
                        clearTimeout(recordingTimeout);
                    };
                    mediaRecorder.start();
                    recordingTimeout = setTimeout(function() {
                        if (mediaRecorder.state === 'recording') mediaRecorder.stop();
                    }, 30000);
                })
                .catch(err => {
                    console.error('Microphone access denied:', err);
                    alert('Could not access microphone');
                });
        });
    }

    // Stop recording audio
    if (stopRecordingBtn) {
        stopRecordingBtn.addEventListener('click', function() {
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
            }
        });
    }

    // TTS functionality for Speak aloud buttons
    const ttsButtons = document.querySelectorAll('.tts-button');
    ttsButtons.forEach(button => {
        button.addEventListener('click', function() {
            const answerContainer = this.closest('.answer-container');
            const contentDiv = answerContainer.querySelector('div');
            // Extract only the actual answer text (everything before "Source: ChromaDB")
            let text = contentDiv.textContent.trim();
            const sourceIndex = text.indexOf('Source: ChromaDB');
            if (sourceIndex > -1) {
                text = text.substring(0, sourceIndex).trim();
            }
            
            // Stop any currently playing audio in this container
            if (answerContainer.currentTTS) {
                answerContainer.currentTTS.stop();
            }
            
            // Start TTS playback
            playTTSWebAudio(text, answerContainer);
        });
    });

    // Web Audio API based TTS player for smooth streaming
    async function playTTSWebAudio(text, answerContainer) {
        try {
            // Initialize Web Audio Context
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            // Ensure context is running - handle autoplay policy
            if (audioContext.state === 'suspended') {
                await audioContext.resume();
            }
            
            const sourceSampleRate = 24000; // Gemini's sample rate
            const targetSampleRate = audioContext.sampleRate; // Usually 44100
            
            let headerParsed = false;
            let audioQueue = [];
            let isPlaying = false;
            let processingNode = null;
            let gainNode = null;
            let currentSampleIndex = 0;
            
            // Create a controller to manage the TTS session
            const ttsController = {
                stop: () => {
                    isPlaying = false;
                    if (processingNode) {
                        try {
                            processingNode.disconnect();
                        } catch (e) {
                            // Ignore disconnect errors
                        }
                        processingNode = null;
                    }
                    if (gainNode) {
                        try {
                            gainNode.disconnect();
                        } catch (e) {
                            // Ignore disconnect errors
                        }
                        gainNode = null;
                    }
                    audioQueue = [];
                }
            };
            
            // Store the controller for later cleanup
            answerContainer.currentTTS = ttsController;
            
            // Create gain node for volume control
            gainNode = audioContext.createGain();
            gainNode.gain.value = 0.8;
            gainNode.connect(audioContext.destination);
            
            // Use ScriptProcessorNode for audio processing
            const bufferSize = 4096;
            processingNode = audioContext.createScriptProcessor(bufferSize, 0, 1);
            processingNode.connect(gainNode);
            
            processingNode.onaudioprocess = function(event) {
                const outputData = event.outputBuffer.getChannelData(0);
                
                if (!isPlaying) {
                    outputData.fill(0);
                    return;
                }
                
                // Fill output buffer with queued audio data
                for (let i = 0; i < bufferSize; i++) {
                    if (currentSampleIndex < audioQueue.length) {
                        outputData[i] = audioQueue[currentSampleIndex];
                        currentSampleIndex++;
                    } else {
                        outputData[i] = 0;
                    }
                }
                
                // Clean up old audio data to prevent memory growth
                if (currentSampleIndex > targetSampleRate * 3) {
                    const keepSamples = targetSampleRate;
                    const removeCount = currentSampleIndex - keepSamples;
                    audioQueue.splice(0, removeCount);
                    currentSampleIndex = keepSamples;
                }
            };
            
            // Simple linear interpolation resampler
            function resampleAudio(inputSamples, inputRate, outputRate) {
                if (inputRate === outputRate) {
                    return inputSamples;
                }
                
                const ratio = inputRate / outputRate;
                const outputLength = Math.floor(inputSamples.length / ratio);
                const output = new Float32Array(outputLength);
                
                for (let i = 0; i < outputLength; i++) {
                    const sourceIndex = i * ratio;
                    const index = Math.floor(sourceIndex);
                    const fraction = sourceIndex - index;
                    
                    if (index + 1 < inputSamples.length) {
                        output[i] = inputSamples[index] * (1 - fraction) + inputSamples[index + 1] * fraction;
                    } else if (index < inputSamples.length) {
                        output[i] = inputSamples[index];
                    } else {
                        output[i] = 0;
                    }
                }
                
                return output;
            }
            
            // Fetch the audio stream
            const response = await fetch(`/tts-stream?text=${encodeURIComponent(text)}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const reader = response.body.getReader();
            let bytesBuffer = new Uint8Array(0);
            
            // Read stream chunks
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;
                if (!isPlaying && !processingNode) break;
                
                // Append new data to buffer
                const newBuffer = new Uint8Array(bytesBuffer.length + value.length);
                newBuffer.set(bytesBuffer);
                newBuffer.set(value, bytesBuffer.length);
                bytesBuffer = newBuffer;
                
                // Parse header if not done yet
                if (!headerParsed) {
                    const headerEnd = bytesBuffer.indexOf(10);
                    if (headerEnd !== -1) {
                        const headerBytes = bytesBuffer.slice(0, headerEnd);
                        const headerText = new TextDecoder().decode(headerBytes);
                        try {
                            JSON.parse(headerText); // Validate header format
                            headerParsed = true;
                            bytesBuffer = bytesBuffer.slice(headerEnd + 1);
                        } catch (e) {
                            headerParsed = true;
                        }
                    } else {
                        continue;
                    }
                }
                
                // Convert bytes to audio samples and add to queue
                if (bytesBuffer.length >= 2) {
                    const samplesCount = Math.floor(bytesBuffer.length / 2);
                    
                    // Create Int16Array from the bytes
                    const int16Data = new Int16Array(samplesCount);
                    const dataView = new DataView(bytesBuffer.buffer, bytesBuffer.byteOffset, samplesCount * 2);
                    
                    for (let i = 0; i < samplesCount; i++) {
                        int16Data[i] = dataView.getInt16(i * 2, true);
                    }
                    
                    // Convert to Float32Array
                    const float32Samples = new Float32Array(int16Data.length);
                    for (let i = 0; i < int16Data.length; i++) {
                        float32Samples[i] = int16Data[i] / 32768.0;
                    }
                    
                    // Resample if necessary
                    const resampledSamples = resampleAudio(float32Samples, sourceSampleRate, targetSampleRate);
                    
                    // Add resampled samples to queue
                    for (let i = 0; i < resampledSamples.length; i++) {
                        audioQueue.push(resampledSamples[i]);
                    }
                    
                    // Start playback when we have enough data
                    if (!isPlaying && audioQueue.length >= targetSampleRate * 0.1) {
                        isPlaying = true;
                        
                        if (audioContext.state === 'suspended') {
                            await audioContext.resume();
                        }
                    }
                    
                    // Update buffer to remaining bytes
                    const remainingBytes = bytesBuffer.length % 2;
                    if (remainingBytes > 0) {
                        bytesBuffer = bytesBuffer.slice(samplesCount * 2);
                    } else {
                        bytesBuffer = new Uint8Array(0);
                    }
                }
            }
            
            // Start playback if we haven't already
            if (!isPlaying && audioQueue.length > 0) {
                isPlaying = true;
                
                if (audioContext.state === 'suspended') {
                    await audioContext.resume();
                }
            }
            
            // Wait for playback to finish
            const checkPlaybackFinished = () => {
                if (!isPlaying) return;
                
                if (currentSampleIndex >= audioQueue.length && audioQueue.length > 0) {
                    ttsController.stop();
                    answerContainer.currentTTS = null;
                } else {
                    setTimeout(checkPlaybackFinished, 500);
                }
            };
            
            setTimeout(checkPlaybackFinished, 500);
            
        } catch (error) {
            console.error('TTS playback failed:', error);
            alert('TTS playback failed. Please try again.');
        }
    }
}); 