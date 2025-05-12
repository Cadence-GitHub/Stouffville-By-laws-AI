// Function to handle form submission
function submitQuestion(event) {
    event.preventDefault();
    
    const query = document.getElementById('question').value.trim();
    if (!query) {
        showInputError('Please enter a question');
        return;
    }
    
    // Clear any previous errors on the input
    clearInputError();
    
    // Disable the submit button and show loading state
    const submitButton = document.getElementById('submitButton');
    submitButton.disabled = true;
    submitButton.innerHTML = '<span>Processing...</span>';
    
    // Clear previous answers and show loading indicator
    const loadingIndicator = document.getElementById('loadingIndicator');
    const answerContainer = document.getElementById('answerContainer');
    
    answerContainer.innerHTML = '';
    answerContainer.style.display = 'none';
    loadingIndicator.classList.add('show');
    
    fetch('/api/ask', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            query: query,
            bylaw_status: 'active'
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        // Hide loading indicator with a small delay for smoother transitions
        setTimeout(() => {
            loadingIndicator.classList.remove('show');
            
            if (data.error) {
                displayError(data.error);
            } else {
                displayAnswer(data);
            }
            
            // Reset button state
            resetButton(submitButton);
        }, 300);
    })
    .catch(error => {
        console.error('Error:', error);
        
        setTimeout(() => {
            loadingIndicator.classList.remove('show');
            displayError('An error occurred while processing your request. Please try again later.');
            resetButton(submitButton);
        }, 300);
    });
}

// Function to reset the button state
function resetButton(button) {
    button.disabled = false;
    button.innerHTML = '<span>Get Answer</span>';
}

// Handler for bylaw links
function handleBylawLinks() {
    document.querySelectorAll('a[href*="bylawViewer.html"]').forEach(link => {
        // Remove existing event listeners to prevent duplicates
        link.removeEventListener('click', bylawLinkClickHandler);
        // Add our click handler
        link.addEventListener('click', bylawLinkClickHandler);
    });
}

// Click handler for bylaw links
function bylawLinkClickHandler(e) {
    const href = this.getAttribute('href');
    const isMobile = window.innerWidth <= 768;
    
    // Extract bylaw ID
    const bylawMatch = href.match(/[?&]bylaw=([^&]+)/);
    if (!bylawMatch) return true;
    
    const bylawId = bylawMatch[1];
    
    if (isMobile) {
        // On mobile, let it open in new tab
        return true;
    } else {
        // Open in panel
        e.preventDefault();
        openBylawPanel(bylawId);
        return false;
    }
}
// Function to open the bylaw panel
function openBylawPanel(bylawId) {
    const panel = document.getElementById('bylaw-panel');
    const content = document.getElementById('bylaw-content');
    const bylawTitle = document.getElementById('bylaw-title');
    
    // Check if elements exist
    if (!panel || !content || !bylawTitle) {
        console.error('Required panel elements not found');
        return;
    }
    
    // Show loading indicator
    content.innerHTML = `
        <div class="loading-spinner">
            <div class="spinner"></div>
            <p>Loading bylaw information...</p>
        </div>
    `;
    
    // Activate panel
    panel.classList.add('active');
    document.body.classList.add('panel-open');

    const container = document.querySelector('.container');
    const body = document.body;
    if (container && body) {
        body.style.maxWidth = 'none';
        body.style.margin = '0';
        body.style.marginRight = '50%';
        
        container.style.width = 'calc(100% - 2rem)';
        container.style.maxWidth = 'none';
    }
    
    // Fetch bylaw data
    fetch(`/api/bylaw/${bylawId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to fetch bylaw: ${response.statusText}`);
            }
            return response.json();
        })
        .then(bylaw => {
            renderBylaw(bylaw, content, bylawTitle);
        })
        .catch(error => {
            content.innerHTML = `
                <div class="error-message">
                    <h3>Error loading bylaw</h3>
                    <p>${error.message}</p>
                </div>
            `;
        });
}

// Function to render bylaw content
function renderBylaw(bylaw, contentElement, titleElement) {
    // Set bylaw title
    let displayTitle = bylaw.bylawNumber;
    if (bylaw.bylawFileName) {
        displayTitle = bylaw.bylawFileName;
        if (displayTitle.endsWith('.json')) {
            displayTitle = displayTitle.slice(0, -5);
        }
    }
    
    titleElement.textContent = displayTitle;
    
    // Helper function to determine if a field should be displayed
    function shouldDisplay(field) {
        if (field === undefined || field === null) return false;
        if (field === false) return false;
        if (typeof field === 'string' && (field.trim() === '' || field.toLowerCase() === 'none')) return false;
        if (Array.isArray(field) && field.length === 0) return false;
        if (Array.isArray(field) && field.length === 1 && field[0].toLowerCase() === 'none') return false;
        return true;
    }
    
    // Helper to format text
    function formatText(text) {
        if (!text) return '';
        
        // Handle newlines
        let formattedText = text.replace(/\n/g, '<br>');
        
        // Handle multiple dashes as separators (4 or more)
        formattedText = formattedText.replace(/----+/g, '<hr>');
        
        // Handle percentage signs as separators
        formattedText = formattedText.replace(/%%%/g, ', ');
        
        // Handle triple pipe as separators
        formattedText = formattedText.replace(/\|\|\|/g, ', ');
        
        // Handle pipe separators in non-table content
        if (!formattedText.includes('<table>')) {
            formattedText = formattedText.replace(/\|/g, ' | ');
        }
        
        return formattedText;
    }
    
    // Helper to create a section
    function createSection(title, content, hideInPublicDemo = false) {
        // Skip if content shouldn't be displayed or section should be hidden in public demo
        if (!shouldDisplay(content) || hideInPublicDemo) return '';
        
        let formattedContent;
        if (Array.isArray(content)) {
            // Format as list
            formattedContent = '<ul>';
            content.forEach(item => {
                formattedContent += `<li>${formatText(item)}</li>`;
            });
            formattedContent += '</ul>';
        } else {
            formattedContent = `<p>${formatText(content)}</p>`;
        }
        
        return `
            <div class="bylaw-section">
                <h4 class="section-title">${title}</h4>
                <div class="section-content">${formattedContent}</div>
            </div>
        `;
    }
    
    // Build HTML for sections
    let html = '';

    // URL Original Document section
    if (shouldDisplay(bylaw.urlOriginalDocument)) {
        let pdfName = "document";
        if (bylaw.urlOriginalDocument && typeof bylaw.urlOriginalDocument === 'string') {
            const urlParts = bylaw.urlOriginalDocument.split('/');
            if (urlParts.length > 0) {
                const lastPart = urlParts[urlParts.length - 1];
                if (lastPart.includes('?')) {
                    pdfName = lastPart.split('?')[0];
                } else {
                    pdfName = lastPart;
                }
            }
        }
        
        html += `
            <div class="bylaw-section">
                <h4 class="section-title">Original Town Document</h4>
                <div class="section-content">
                    <p><a href="${bylaw.urlOriginalDocument}" target="_blank" rel="noopener noreferrer">${pdfName}</a></p>
                </div>
            </div>
        `;
    }
    
    // Layman's explanation section
    html += createSection('Summary', bylaw.laymanExplanation);
    
    // Key dates and info section
    html += createSection('Key Dates', bylaw.keyDatesAndInfo);
    
    // Entity and designation section
    html += createSection('Entity and Designation', bylaw.entityAndDesignation);
    
    // Conditions and clauses section
    html += createSection('Conditions and Clauses', bylaw.condtionsAndClauses);
    
    // Other Bylaws section
    html += createSection('Other Bylaws', bylaw.otherBylaws);
    
    // Why Other Bylaws section
    html += createSection('Why Other Bylaws', bylaw.whyOtherBylaws);
    
    // Legislation section
    html += createSection('Legislation', bylaw.legislation);
    
    // Why Legislation section
    html += createSection('Why Legislation', bylaw.whyLegislation);
    
    // Location Addresses section (special handling)
    if (shouldDisplay(bylaw.locationAddresses)) {
        let locationContent = '';
        let locations = [];
        
        if (typeof bylaw.locationAddresses === 'string') {
            locations = bylaw.locationAddresses
                .split(/\|\|\||%%%|\n/)
                .map(loc => loc.trim())
                .filter(loc => loc && loc.toLowerCase() !== 'none');
        } else if (Array.isArray(bylaw.locationAddresses)) {
            locations = bylaw.locationAddresses.filter(loc => loc && loc.toLowerCase() !== 'none');
        }
        
        if (locations.length > 0) {
            locationContent = '<ul>';
            locations.forEach(location => {
                const encodedLocation = encodeURIComponent(location + ', Ontario, Canada');
                const googleMapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodedLocation}`;
                
                locationContent += `<li><a href="${googleMapsUrl}" target="_blank" rel="noopener noreferrer">${location}</a></li>`;
            });
            locationContent += '</ul>';
        } else {
            locationContent = `<p>${formatText(bylaw.locationAddresses)}</p>`;
        }
        
        html += `
            <div class="bylaw-section">
                <h4 class="section-title">Location Addresses</h4>
                <div class="section-content">${locationContent}</div>
            </div>
        `;
    }
    
    // Money and Categories section
    html += createSection('Money and Categories', bylaw.moneyAndCategories);
    
    // Other Details section - hidden in public demo
    html += createSection('Other Details', bylaw.otherDetails, true);
    
    // Image Description section
    if (bylaw.hasEmbeddedImages && shouldDisplay(bylaw.imageDesciption)) {
        html += createSection('Image Description', bylaw.imageDesciption);
    }
    
    // Map Description section
    if (bylaw.hasEmbeddedMaps && shouldDisplay(bylaw.mapDescription)) {
        html += createSection('Map Description', bylaw.mapDescription);
    }
    
    // Full text section
    if (shouldDisplay(bylaw.content)) {
        const textContent = Array.isArray(bylaw.content) ? bylaw.content.join('\n') : bylaw.content;
        
        html += `
            <div class="bylaw-section">
                <h4 class="section-title">Full Text</h4>
                <div class="section-content">
                    <div class="bylaw-section full-width">${formatText(textContent)}</div>
                </div>
            </div>
        `;
    }
    
    // Add content to panel
    contentElement.innerHTML = html;
}

// Function to setup bylaw panel
function setupBylawPanel() {
    const panel = document.getElementById('bylaw-panel');
    const closeBtn = document.getElementById('close-panel');
    const resizer = document.getElementById('panel-resizer');
    
    if (!panel || !closeBtn || !resizer) {
        console.error('Required panel elements not found');
        return;
    }
    
    // Close button click handler
    closeBtn.addEventListener('click', function() {
        panel.classList.remove('active');
        document.body.classList.remove('panel-open');
        
        // Reset container margin and width
        const container = document.querySelector('.container');
        const body = document.body;
        if (container && body) {
            body.style.maxWidth = '';
            body.style.margin = '';
            body.style.marginRight = '';
            
            container.style.width = '';
            container.style.maxWidth = '';
        }
        
        setTimeout(() => {
            document.getElementById('bylaw-content').innerHTML = '';
            document.getElementById('bylaw-title').textContent = 'Bylaw Details';
        }, 300);
    });
    
    // Set up resize functionality
    let isResizing = false;
    
    resizer.addEventListener('mousedown', function(e) {
        isResizing = true;
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', stopResize);
        document.body.style.cursor = 'ew-resize';
        e.preventDefault();
    });
    
    function handleMouseMove(e) {
        if (!isResizing) return;
        
        const windowWidth = window.innerWidth;
        const panelWidth = windowWidth - e.clientX;
        const percentage = Math.min(Math.max((panelWidth / windowWidth) * 100, 30), 70);
        
        // Update panel width
        panel.style.width = `${percentage}%`;
        
        // Get container and body
        const container = document.querySelector('.container');
        const body = document.body;
        
        if (container && body) {
            // Adjust body to move content left
            body.style.maxWidth = 'none';
            body.style.margin = '0';
            body.style.marginRight = `${percentage}%`;
            
            // Adjust container
            container.style.width = `calc(100% - 2rem)`;
            container.style.maxWidth = 'none';
        }
    }
    
    function stopResize() {
        isResizing = false;
        document.removeEventListener('mousemove', handleMouseMove);
        document.body.style.cursor = '';
    }
    
    // Initial call to set up links
    handleBylawLinks();
    
    // Setup mutation observer to handle dynamically added bylaw links
    const observer = new MutationObserver(function() {
        handleBylawLinks();
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}

// Function to display the answer
function displayAnswer(data) {
    const answerContainer = document.getElementById('answerContainer');
    
    // Store both answer types for toggling
    const laymansAnswer = data.laymans_answer || '';
    const filteredAnswer = data.filtered_answer || '';
    
    // Create toggle button only if we have both answers
    const toggleButton = (laymansAnswer && filteredAnswer) 
        ? `<div class="answer-toggle">
             <button type="button" id="toggleAnswerDetail" class="toggle-button">
               <span>Show Detailed Answer</span>
             </button>
           </div>`
        : '';
    
    answerContainer.innerHTML = `
        <div class="answer">
            <div id="answerContent">${laymansAnswer}</div>
            ${toggleButton}
        </div>
    `;
    
    answerContainer.style.display = 'block';
    
    // Process bylaw links in the answer
    setTimeout(handleBylawLinks, 100);
    
    // Set up toggle functionality if both answers exist
    if (laymansAnswer && filteredAnswer) {
        const toggleBtn = document.getElementById('toggleAnswerDetail');
        let showingDetailed = false;
        
        toggleBtn.addEventListener('click', function() {
            const answerContent = document.getElementById('answerContent');
            showingDetailed = !showingDetailed;
            
            // Add fade-out class for transition
            answerContent.classList.add('fade-out');
            
            // Change content after a short delay for the transition
            setTimeout(() => {
                if (showingDetailed) {
                    answerContent.innerHTML = filteredAnswer;
                    toggleBtn.querySelector('span').textContent = 'Show Simple Answer';
                    toggleBtn.classList.add('active');
                } else {
                    answerContent.innerHTML = laymansAnswer;
                    toggleBtn.querySelector('span').textContent = 'Show Detailed Answer';
                    toggleBtn.classList.remove('active');
                }
                
                // Process bylaw links in the toggled content
                handleBylawLinks();
                
                // Add fade-in class
                answerContent.classList.remove('fade-out');
                answerContent.classList.add('fade-in');
                
                // Remove fade-in class after animation completes
                setTimeout(() => {
                    answerContent.classList.remove('fade-in');
                }, 300);
                
                // Smooth scroll to top of answer if needed
                const rect = answerContainer.getBoundingClientRect();
                if (rect.top < 0) {
                    answerContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 200);
        });
    }
    
    // Scroll to the answer if it's below the viewport
    setTimeout(() => {
        const rect = answerContainer.getBoundingClientRect();
        if (rect.top > window.innerHeight - 100) {
            answerContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }, 100);
}

// Function to display an error
function displayError(message) {
    const answerContainer = document.getElementById('answerContainer');
    
    answerContainer.innerHTML = `
        <div class="error">
            <p>${message}</p>
        </div>
    `;
    
    answerContainer.style.display = 'block';
}

// Function to show an input error
function showInputError(message) {
    const questionInput = document.getElementById('question');
    questionInput.classList.add('error-input');
    
    // Add error message below input if not already present
    let errorElement = document.querySelector('.input-error-message');
    if (!errorElement) {
        errorElement = document.createElement('div');
        errorElement.className = 'input-error-message';
        questionInput.insertAdjacentElement('afterend', errorElement);
    }
    
    errorElement.textContent = message;
}

// Function to clear input error
function clearInputError() {
    const questionInput = document.getElementById('question');
    questionInput.classList.remove('error-input');
    
    const errorElement = document.querySelector('.input-error-message');
    if (errorElement) {
        errorElement.remove();
    }
}

// Dark mode toggle functionality
function setupThemeToggle() {
    const toggleSwitch = document.querySelector('#checkbox');
    const currentTheme = localStorage.getItem('theme');
    
    // Check for saved theme preference or use system preference
    if (currentTheme) {
        document.documentElement.setAttribute('data-theme', currentTheme);
        if (currentTheme === 'dark') {
            toggleSwitch.checked = true;
        }
    } else {
        // If no theme is saved, check system preference
        const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
        if (prefersDarkScheme.matches) {
            document.documentElement.setAttribute('data-theme', 'dark');
            toggleSwitch.checked = true;
            localStorage.setItem('theme', 'dark');
        }
    }
    
    // Listen for toggle changes
    toggleSwitch.addEventListener('change', switchTheme);
    
    // Listen for system preference changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        // Only update if user hasn't manually set a preference
        if (!localStorage.getItem('theme')) {
            if (e.matches) {
                document.documentElement.setAttribute('data-theme', 'dark');
                toggleSwitch.checked = true;
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                toggleSwitch.checked = false;
            }
        }
    });
    
    // Function to switch themes
    function switchTheme(e) {
        if (e.target.checked) {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        }
    }
}

// Autocomplete functionality
function setupAutocomplete() {
    // Get the query input element
    const queryInput = document.getElementById('question');
    
    // Create autocomplete container
    const autocompleteContainer = document.createElement('div');
    autocompleteContainer.className = 'autocomplete-container';
    autocompleteContainer.style.display = 'none';
    
    // Create a wrapper div if it doesn't exist
    let inputWrapper = queryInput.parentElement;
    if (inputWrapper === document.getElementById('questionForm')) {
        // Create a wrapper for the input to handle positioning correctly
        inputWrapper = document.createElement('div');
        inputWrapper.style.position = 'relative';
        inputWrapper.style.marginBottom = '1rem'; // Move margin to wrapper instead of input
        
        // Replace the input with the wrapper containing the input
        queryInput.parentNode.insertBefore(inputWrapper, queryInput);
        inputWrapper.appendChild(queryInput);
        
        // Remove margin from input since it's now on the wrapper
        queryInput.style.marginBottom = '0';
    }
    
    // Insert the autocomplete container as a child of the input wrapper
    inputWrapper.appendChild(autocompleteContainer);
    
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
            displaySuggestions();
        })
        .catch(error => {
            console.error('Error fetching autocomplete suggestions:', error);
        });
    }
    
    // Display suggestions in the DOM
    function displaySuggestions() {
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
            suggestionElement.textContent = suggestion;
            
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
        
        // Position is now handled by CSS with top: 100%
        // Just set the width to match the input
        autocompleteContainer.style.width = '100%';
        
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
}

// Provincial law functionality
function setupProvincialLawSection() {
    const lawButtons = document.querySelectorAll('.law-type-button');
    const contentContainer = document.getElementById('provincialLawContent');
    
    // Load the default (general) info on page load
    fetchProvincialLawInfo('general');
    
    // Add click handlers to buttons
    lawButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Update active button
            lawButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            
            // Fetch information for the selected type
            const bylawType = this.getAttribute('data-type');
            fetchProvincialLawInfo(bylawType);
        });
    });
    
    // Function to fetch provincial law information
    function fetchProvincialLawInfo(bylawType) {
        const contentContainer = document.getElementById('provincialLawContent');
        
        contentContainer.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner"></div>
                <p>Loading provincial law information...</p>
            </div>
        `;
        
        fetch('/api/provincial_laws', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                bylaw_type: bylawType,
                model: 'gemini-2.0-flash'
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                contentContainer.innerHTML = `
                    <div class="error-message">
                        <h3>Error loading information</h3>
                        <p>${data.error}</p>
                    </div>
                `;
            } else {
                // Create the content with the provincial info
                let htmlContent = `<div class="provincial-info">${data.provincial_info}</div>`;
                
                // Add sources if available
                if (data.sources && data.sources.length > 0) {
                    htmlContent += `
                        <div class="source-section">
                            <h4>Sources</h4>
                            <div class="source-list">
                    `;
                    
                    data.sources.forEach(source => {
                        htmlContent += `
                            <div class="source-item">
                                <a href="${source.url}" target="_blank" rel="noopener noreferrer">
                                    ${source.title || 'Source'}
                                </a>
                                <p class="source-snippet">${source.snippet || ''}</p>
                            </div>
                        `;
                    });
                    
                    htmlContent += `
                            </div>
                        </div>
                    `;
                }
                
                contentContainer.innerHTML = htmlContent;
                handleBylawLinks();
            }
        })
        .catch(error => {
            contentContainer.innerHTML = `
                <div class="error-message">
                    <h3>Error loading information</h3>
                    <p>${error.message}</p>
                </div>
            `;
        });
    }
}

// Ensure everything is set up properly when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Ensure loading indicator is hidden when page loads
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.classList.remove('show');
    
    // Hide answer container initially
    const answerContainer = document.getElementById('answerContainer');
    answerContainer.style.display = 'none';
    
    // Attach the form submission handler
    const form = document.getElementById('questionForm');
    if (form) {
        form.addEventListener('submit', submitQuestion);
    }
    
    // Initialize dark mode toggle
    setupThemeToggle();
    
    // Initialize autocomplete
    setupAutocomplete();
    
    // Initialize bylaw panel
    setupBylawPanel();

    // Initialize provincial law section
    setupProvincialLawSection();
    
    // Focus the input field for immediate user interaction
    document.getElementById('question').focus();
});