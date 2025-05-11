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
    
    // Focus the input field for immediate user interaction
    document.getElementById('question').focus();
}); 