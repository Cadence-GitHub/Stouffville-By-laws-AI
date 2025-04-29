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
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Initial setup
    handleBylawLinks();
    console.log('Bylaw sidebar initialized');
}); 