let evaluators = [];
let questions = [];
let aiResponses = [];
let currentIdx = 0;
let total = 0;
let evaluator = '';
let progress = {};
let isRendering = false;
let isFetchingAI = [];

// Populate the welcome user dropdown
async function populateWelcomeUserDropdown() {
    console.log('populateWelcomeUserDropdown called');
    const evalRes = await fetch('/api/evaluators');
    evaluators = await evalRes.json();
    const select = document.getElementById('welcome-user-select');
    console.log('select:', select);
    select.innerHTML = '<option value="">-- Select an existing user --</option>' +
        evaluators.map(e => `<option value="${e}">${e}</option>`).join('');
}

// Show welcome screen
function showWelcome() {
    document.getElementById('welcome-screen').style.display = '';
    document.getElementById('eval-ui').style.display = 'none';
    document.getElementById('welcome-name').value = '';
    document.getElementById('welcome-error').innerText = '';
    populateWelcomeUserDropdown();
}

// Show eval UI
function showEvalUI() {
    document.getElementById('welcome-screen').style.display = 'none';
    document.getElementById('eval-ui').style.display = '';
}

// Load evaluators and questions
async function loadData() {
    // Evaluators
    const evalRes = await fetch('/api/evaluators');
    evaluators = await evalRes.json();
    updateEvaluatorDropdown();
    // Golden questions
    const qRes = await fetch('/api/golden-questions');
    questions = await qRes.json();
    total = questions.length;
    aiResponses = new Array(total).fill(null);
    // Load progress from localStorage
    loadProgress();
    render();
}

function updateEvaluatorDropdown() {
    const evalSelect = document.getElementById('evaluator');
    evalSelect.innerHTML = evaluators.map(e => `<option value="${e}">${e}</option>`).join('');
    if (evaluator && evaluators.includes(evaluator)) {
        evalSelect.value = evaluator;
    } else if (evaluators.length > 0) {
        evalSelect.value = evaluators[0];
        evaluator = evaluators[0];
    }
}

function saveProgress() {
    if (!evaluator) return;
    localStorage.setItem(`eval_progress_${evaluator}`, JSON.stringify(progress));
}

function loadProgress() {
    if (!evaluator) return;
    const data = localStorage.getItem(`eval_progress_${evaluator}`);
    progress = data ? JSON.parse(data) : {};
}

async function fetchAIResponse(idx) {
    if (aiResponses[idx]) return;
    const q = questions[idx];
    // Try to get from progress cache first
    if (progress && progress[idx] && progress[idx].ai_response) {
        aiResponses[idx] = progress[idx].ai_response;
        return;
    }
    // POST to /api/ask
    const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, bylaw_status: 'active' })
    });
    const data = await res.json();
    aiResponses[idx] = data.filtered_answer || data.laymans_answer || data.answer || data.error || 'No response';
    render(); // Only call render once after fetch
}

// --- Begin: Answer rendering and bylaw panel logic (adapted from public_demo.js) ---
function handleBylawLinks() {
    document.querySelectorAll('a[href*="bylawViewer.html"]').forEach(link => {
        link.removeEventListener('click', bylawLinkClickHandler);
        link.addEventListener('click', bylawLinkClickHandler);
    });
}
function bylawLinkClickHandler(e) {
    const href = this.getAttribute('href');
    const isMobile = window.innerWidth <= 768;
    const bylawMatch = href.match(/[?&]bylaw=([^&]+)/);
    if (!bylawMatch) return true;
    const bylawId = bylawMatch[1];
    if (isMobile) {
        return true;
    } else {
        e.preventDefault();
        openBylawPanel(bylawId);
        return false;
    }
}
function openBylawPanel(bylawId) {
    const panel = document.getElementById('bylaw-panel');
    const content = document.getElementById('bylaw-content');
    const bylawTitle = document.getElementById('bylaw-title');
    if (!panel || !content || !bylawTitle) return;
    content.innerHTML = `<div class="loading-spinner"><div class="spinner"></div><p>Loading bylaw information...</p></div>`;
    panel.classList.add('active');
    document.body.classList.add('panel-open');
    // Fetch bylaw data
    fetch(`/api/bylaw/${bylawId}`)
        .then(response => response.json())
        .then(bylaw => {
            renderBylaw(bylaw, content, bylawTitle);
        })
        .catch(error => {
            content.innerHTML = `<div class="error-message"><h3>Error loading bylaw</h3><p>${error.message}</p></div>`;
        });
}
function renderBylaw(bylaw, contentElement, titleElement) {
    console.log('renderBylaw called with:', bylaw);
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
        let formattedText = text.replace(/\n/g, '<br>');
        formattedText = formattedText.replace(/----+/g, '<hr>');
        formattedText = formattedText.replace(/%%%/g, ', ');
        formattedText = formattedText.replace(/\|\|\|/g, ', ');
        // Handle pipe separators in non-table content
        if (!formattedText.includes('<table>')) {
            formattedText = formattedText.replace(/\|/g, ' | ');
        }
        return formattedText;
    }
    // Helper to create a section
    function createSection(title, content, hideInPublicDemo = false) {
        if (!shouldDisplay(content) || hideInPublicDemo) return '';
        let formattedContent;
        if (Array.isArray(content)) {
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
    console.log('renderBylaw HTML:', html);
    // Add content to panel
    contentElement.innerHTML = html;
}
document.getElementById('close-panel').onclick = function() {
    document.getElementById('bylaw-panel').classList.remove('active');
    document.body.classList.remove('panel-open');
};
// --- End: Answer rendering and bylaw panel logic ---

// --- Begin: Navigation, Bookmark, Skip, and Validation Logic ---
let bookmarks = [];
let skipped = [];

async function fetchEvalStatus() {
    if (!evaluator) return;
    const res = await fetch(`/api/eval-status?evaluator=${encodeURIComponent(evaluator)}`);
    const data = await res.json();
    bookmarks = data.filter(s => s.bookmarked).map(s => s.question_idx);
    skipped = data.filter(s => s.skipped).map(s => s.question_idx);
}
async function setEvalStatus(idx, {bookmarked, skipped: skipVal}) {
    if (!evaluator) return;
    await fetch('/api/eval-status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ evaluator, question_idx: idx, bookmarked, skipped: skipVal })
    });
}
function renderNavPane() {
    const nav = document.getElementById('question-nav');
    if (!nav) return;
    // Show nav only if eval-ui is visible
    const evalUI = document.getElementById('eval-ui');
    if (!evalUI || evalUI.style.display === 'none') {
        nav.style.display = 'none';
        return;
    } else {
        nav.style.display = '';
    }
    let collapsed = nav.classList.contains('collapsed');
    let html = nav.querySelector('.nav-toggle') ? nav.querySelector('.nav-toggle').outerHTML : '';
    html += '<ul class="question-nav-list">';
    for (let i = 0; i < total; i++) {
        let status = '';
        if (progress[i]) status = 'completed';
        else if (bookmarks.includes(i)) status = 'bookmarked';
        else if (skipped.includes(i)) status = 'skipped';
        let active = (i === currentIdx) ? 'active' : '';
        let icon = '';
        if (status === 'completed') icon = '✔️';
        else if (status === 'bookmarked') icon = '🔖';
        else if (status === 'skipped') icon = '⏭️';
        let questionText = questions[i] ? questions[i].slice(0, 80) : '';
        if (questionText.length === 80) questionText += '…';
        let fullText = questions[i] || '';
        html += `<li class="question-nav-item ${status} ${active}" data-idx="${i}" title="${fullText.replace(/&/g, '&amp;').replace(/"/g, '&quot;')}"><span class="nav-index">${i+1}</span> <span class="nav-question">${questionText}</span> <span class="nav-status">${icon}</span></li>`;
    }
    html += '</ul>';
    nav.innerHTML = html;
    document.querySelectorAll('.question-nav-item').forEach(item => {
        item.onclick = function() {
            const idx = parseInt(this.getAttribute('data-idx'));
            currentIdx = idx;
            render();
        };
    });
    // Toggle button logic
    const toggleBtn = document.getElementById('nav-toggle');
    if (toggleBtn) {
        // Hide toggle if nav is hidden
        if (nav.style.display === 'none') {
            toggleBtn.style.display = 'none';
        } else {
            toggleBtn.style.display = '';
        }
        toggleBtn.onclick = function() {
            nav.classList.toggle('collapsed');
            // Change arrow direction
            if (nav.classList.contains('collapsed')) {
                toggleBtn.innerText = '⮞';
            } else {
                toggleBtn.innerText = '⮜';
            }
        };
        // Set initial arrow
        if (nav.classList.contains('collapsed')) {
            toggleBtn.innerText = '⮞';
        } else {
            toggleBtn.innerText = '⮜';
        }
    }
}
async function skipCurrent() {
    if (!skipped.includes(currentIdx)) skipped.push(currentIdx);
    await setEvalStatus(currentIdx, {bookmarked: bookmarks.includes(currentIdx), skipped: true});
    // Move to next unanswered/skipped/bookmarked question, or next in order
    let next = (currentIdx + 1) % total;
    let tries = 0;
    while (progress[next] && tries < total) {
        next = (next + 1) % total;
        tries++;
    }
    currentIdx = next;
    render();
}
async function bookmarkCurrent() {
    if (!bookmarks.includes(currentIdx)) bookmarks.push(currentIdx);
    await setEvalStatus(currentIdx, {bookmarked: true, skipped: skipped.includes(currentIdx)});
    render();
}
async function unbookmarkCurrent() {
    bookmarks = bookmarks.filter(i => i !== currentIdx);
    await setEvalStatus(currentIdx, {bookmarked: false, skipped: skipped.includes(currentIdx)});
    render();
}
function isCompleted(idx) {
    return !!progress[idx];
}
function isBookmarked(idx) {
    return bookmarks.includes(idx);
}
function isSkipped(idx) {
    return skipped.includes(idx);
}
// --- End: Navigation, Bookmark, Skip, and Validation Logic ---

function render() {
    if (isRendering) return;
    isRendering = true;
    // Progress
    let completed = Object.keys(progress).length;
    document.getElementById('progress').innerText = `Progress: ${completed} / ${total}`;
    // Question
    document.getElementById('question-text').innerText = questions[currentIdx] || '';
    // AI Response
    const answerContainer = document.getElementById('answerContainer');
    const aiResp = aiResponses[currentIdx] || '<em>Loading...</em>';
    answerContainer.innerHTML = `<div class="answer">${aiResp}</div>`;
    handleBylawLinks();
    // Form
    const form = document.getElementById('eval-form');
    if (progress[currentIdx]) {
        form.response_generated.value = progress[currentIdx].response_generated ? 'true' : 'false';
        form.accuracy.value = progress[currentIdx].accuracy || '';
        form.hallucination.value = progress[currentIdx].hallucination || '';
        form.completeness.value = progress[currentIdx].completeness || '';
        form.authoritative.value = progress[currentIdx].authoritative || '';
        form.usefulness.value = progress[currentIdx].usefulness || '';
        form.comments.value = progress[currentIdx].comments || '';
    } else {
        form.reset();
    }
    // Disable rubric if response_generated is false
    form.response_generated.onchange = function() {
        const disabled = form.response_generated.value === 'false';
        ['accuracy','hallucination','completeness','authoritative','usefulness'].forEach(id => {
            form[id].disabled = disabled;
        });
    };
    form.response_generated.onchange();
    // Evaluator select
    updateEvaluatorDropdown();
    document.getElementById('evaluator').value = evaluator;
    document.getElementById('evaluator-label').innerText = evaluator;
    // Only fetch if not present and not already fetching
    if (!aiResponses[currentIdx] && !(isFetchingAI[currentIdx])) {
        isFetchingAI[currentIdx] = true;
        fetchAIResponse(currentIdx).finally(() => {
            isFetchingAI[currentIdx] = false;
        });
    }
    isRendering = false;
}

// Patch render() to update nav pane and action buttons
const origRender = render;
render = function() {
    origRender.apply(this, arguments);
    renderNavPane();
    // Update bookmark button state
    const bookmarkBtn = document.getElementById('bookmark-btn');
    if (bookmarkBtn) {
        if (isBookmarked(currentIdx)) {
            bookmarkBtn.innerText = 'Remove Bookmark';
            bookmarkBtn.onclick = unbookmarkCurrent;
        } else {
            bookmarkBtn.innerText = 'Bookmark';
            bookmarkBtn.onclick = bookmarkCurrent;
        }
    }
    // Update skip button
    const skipBtn = document.getElementById('skip-btn');
    if (skipBtn) {
        skipBtn.onclick = skipCurrent;
    }
};

// Extend showEvalUI to load bookmarks/skipped from backend
const origShowEvalUI = showEvalUI;
showEvalUI = async function() {
    await fetchEvalStatus();
    origShowEvalUI.apply(this, arguments);
};

// Extend loadData to load bookmarks/skipped from backend
const origLoadData = loadData;
loadData = async function() {
    await origLoadData.apply(this, arguments);
    await fetchEvalStatus();
};

// Patch fetchAIResponse to not call render (let render handle UI update)
async function fetchAIResponse(idx) {
    if (aiResponses[idx]) return;
    const q = questions[idx];
    // Try to get from progress cache first
    if (progress && progress[idx] && progress[idx].ai_response) {
        aiResponses[idx] = progress[idx].ai_response;
        return;
    }
    // POST to /api/ask
    const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, bylaw_status: 'active' })
    });
    const data = await res.json();
    aiResponses[idx] = data.filtered_answer || data.laymans_answer || data.answer || data.error || 'No response';
    render(); // Only call render once after fetch
}

// Patch form submission for validation and pass_fail
const origOnSubmit = document.getElementById('eval-form').onsubmit;
document.getElementById('eval-form').onsubmit = async function(e) {
    e.preventDefault();
    if (!evaluator) {
        alert('Please select an evaluator.');
        return;
    }
    const idx = currentIdx;
    const q = questions[idx];
    const ai = aiResponses[idx];
    const response_generated = document.getElementById('response_generated').value === 'true';
    const accuracy = parseInt(document.getElementById('accuracy').value) || null;
    const hallucination = parseInt(document.getElementById('hallucination').value) || null;
    const completeness = parseInt(document.getElementById('completeness').value) || null;
    const authoritative = parseInt(document.getElementById('authoritative').value) || null;
    const usefulness = parseInt(document.getElementById('usefulness').value) || null;
    const pass_fail = document.getElementById('pass_fail').value;
    const comments = document.getElementById('comments').value;
    // Validation: all fields required if response_generated
    if (response_generated) {
        if (!accuracy || !hallucination || !completeness || !authoritative || !usefulness || !pass_fail) {
            alert('All rubric fields and Pass/Fail are required when a response is generated.');
            return;
        }
    }
    // Save to backend
    const payload = {
        question: q,
        ai_response: ai,
        reference_answer: '',
        evaluator,
        response_generated,
        accuracy,
        hallucination,
        completeness,
        authoritative,
        usefulness,
        comments,
        pass_fail
    };
    const res = await fetch('/api/eval', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    if (res.ok) {
        document.getElementById('eval-status').innerText = 'Saved!';
        progress[idx] = payload;
        // Remove from skipped/bookmarks if completed
        skipped = skipped.filter(i => i !== idx);
        bookmarks = bookmarks.filter(i => i !== idx);
        saveProgress();
        render();
    } else {
        document.getElementById('eval-status').innerText = 'Error saving!';
    }
};

document.getElementById('prev-btn').onclick = function() {
    if (currentIdx > 0) {
        currentIdx--;
        render();
    }
};
document.getElementById('next-btn').onclick = function() {
    if (currentIdx < total - 1) {
        currentIdx++;
        render();
    }
};

document.getElementById('evaluator').onchange = function(e) {
    evaluator = e.target.value;
    loadProgress();
    render();
};

// Update label and show evaluator name
document.getElementById('welcome-proceed').onclick = async function() {
    const newName = document.getElementById('welcome-name').value.trim();
    const selectedName = document.getElementById('welcome-user-select').value;
    let name = '';
    if (newName) {
        name = newName;
    } else if (selectedName) {
        name = selectedName;
    } else {
        document.getElementById('welcome-error').innerText = 'Please select or enter your name.';
        return;
    }
    // Add to DB if not present
    const res = await fetch('/api/evaluators', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    });
    const data = await res.json();
    if (data.error) {
        document.getElementById('welcome-error').innerText = data.error;
        return;
    }
    evaluator = data.name;
    await loadData();
    // Pick a random question for this session
    currentIdx = Math.floor(Math.random() * total);
    showEvalUI();
    document.getElementById('evaluator-label').innerText = evaluator;
    render();
};

document.addEventListener('DOMContentLoaded', function() {
    showWelcome();
}); 