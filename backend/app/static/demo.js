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
}); 