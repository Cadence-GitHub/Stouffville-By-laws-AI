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
}); 