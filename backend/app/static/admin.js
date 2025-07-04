// Admin Dashboard JS
let allData = [];
let filteredData = [];
let progressData = [];
let currentPage = 1;
const pageSize = 10;
let currentSort = { col: null, dir: 1 };
let currentSME = '';

async function fetchProgress() {
    const res = await fetch('/api/eval-admin/progress');
    progressData = await res.json();
    renderSMEProgress();
    renderSMEFilter();
}

async function fetchAllData() {
    const res = await fetch('/api/eval-admin/all');
    allData = await res.json();
    filteredData = allData;
    renderTable();
    renderPagination();
}

function renderSMEProgress() {
    const list = document.getElementById('sme-progress-list');
    list.innerHTML = '';
    progressData.forEach(sme => {
        const percent = Math.round((sme.completed / (sme.total || 1)) * 100);
        const evaluatorEscaped = sme.evaluator.replace(/'/g, "\\'").replace(/"/g, '\\"');
        list.innerHTML += `
        <div class="sme-progress-item">
            <div class="sme-progress-label">${sme.evaluator}</div>
            <div class="sme-progress-bar">
                <div class="sme-progress-bar-inner" style="width:${percent}%;"></div>
            </div>
            <div class="sme-progress-count">${sme.completed} / ${sme.total} complete</div>
            <button class="sme-delete-btn" onclick="showDeleteUserModal('${evaluatorEscaped}')">Delete</button>
        </div>`;
    });
}

function renderSMEFilter() {
    const select = document.getElementById('admin-filter-sme');
    const options = ['<option value="">All SMEs</option>'];
    progressData.forEach(sme => {
        options.push(`<option value="${sme.evaluator}">${sme.evaluator}</option>`);
    });
    select.innerHTML = options.join('');
}

document.getElementById('admin-filter-sme').onchange = function(e) {
    currentSME = e.target.value;
    filterAndRender();
};

document.getElementById('admin-search').oninput = function(e) {
    filterAndRender();
};

function filterAndRender() {
    const search = document.getElementById('admin-search').value.toLowerCase();
    filteredData = allData.filter(row => {
        const matchSME = !currentSME || row.evaluations.some(ev => ev.evaluator === currentSME);
        const matchSearch = row.question.toLowerCase().includes(search) || 
                           row.evaluations.some(ev => ev.ai_response && ev.ai_response.toLowerCase().includes(search));
        return matchSME && matchSearch;
    });
    currentPage = 1;
    renderTable();
    renderPagination();
}

function renderTable() {
    const tbody = document.getElementById('admin-table-body');
    tbody.innerHTML = '';
    let data = filteredData;
    // Sorting
    if (currentSort.col) {
        data = [...data].sort((a, b) => {
            let va = a[currentSort.col], vb = b[currentSort.col];
            if (typeof va === 'string') va = va.toLowerCase();
            if (typeof vb === 'string') vb = vb.toLowerCase();
            if (va < vb) return -1 * currentSort.dir;
            if (va > vb) return 1 * currentSort.dir;
            return 0;
        });
    }
    // Pagination
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    data.slice(start, end).forEach((row, i) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${row.question}</td>
            <td>${row.count}</td>
            <td>${row.avg_accuracy ?? ''}</td>
            <td>${row.avg_hallucination ?? ''}</td>
            <td>${row.avg_completeness ?? ''}</td>
            <td>${row.avg_authoritative ?? ''}</td>
            <td>${row.avg_usefulness ?? ''}</td>
            <td>${row.pass_rate}% (${row.pass_count}/${row.count})</td>
            <td><button class="admin-expand-btn" data-idx="${start + i}">Expand</button></td>
        `;
        tbody.appendChild(tr);
        // Expanded row
        const expTr = document.createElement('tr');
        expTr.className = 'admin-expanded-row';
        expTr.style.display = 'none';
        expTr.innerHTML = `<td colspan="9"><div class="admin-expanded-content"></div></td>`;
        tbody.appendChild(expTr);
    });
    // Add expand/collapse logic
    Array.from(document.getElementsByClassName('admin-expand-btn')).forEach(btn => {
        btn.onclick = function() {
            const idx = parseInt(btn.getAttribute('data-idx'));
            const expTr = btn.parentElement.parentElement.nextSibling;
            if (expTr.style.display === 'none') {
                renderExpandedRow(expTr, filteredData[idx]);
                expTr.style.display = '';
                btn.innerText = 'Collapse';
            } else {
                expTr.style.display = 'none';
                btn.innerText = 'Expand';
            }
        };
    });
}

// Utility to strip HTML tags for preview
function stripHTML(html) {
    const div = document.createElement('div');
    div.innerHTML = html;
    return div.textContent || div.innerText || '';
}

function renderExpandedRow(tr, row) {
    const div = tr.querySelector('.admin-expanded-content');
    let html = `<table class="admin-individual-table"><thead><tr>
        <th>Evaluator</th><th>AI Response</th><th>Accuracy</th><th>Hallucination</th><th>Completeness</th><th>Authoritative</th><th>Usefulness</th><th>Pass/Fail</th><th>Comments</th><th>Timestamp</th><th>Actions</th>
    </tr></thead><tbody>`;
    
    // Add individual evaluations
    row.evaluations.forEach((ev, index) => {
        const questionPreview = row.question.substring(0, 50).replace(/'/g, "\\'").replace(/"/g, '\\"') + '...';
        const evaluatorEscaped = ev.evaluator.replace(/'/g, "\\'").replace(/"/g, '\\"');
        // Use plain text preview
        const aiResponsePreview = ev.ai_response ? stripHTML(ev.ai_response).substring(0, 100) + (stripHTML(ev.ai_response).length > 100 ? '...' : '') : '';
        const aiResponseRaw = ev.ai_response || '';
        html += `<tr>
            <td>${ev.evaluator}</td>
            <td>
                <div class="ai-response-cell">
                    <div class="ai-response-preview">${aiResponsePreview}</div>
                    <button class="view-full-btn" data-ai-response="${encodeURIComponent(aiResponseRaw)}" data-evaluator="${encodeURIComponent(ev.evaluator)}" data-question="${encodeURIComponent(row.question)}">View Full</button>
                </div>
            </td>
            <td>${ev.accuracy ?? ''}</td>
            <td>${ev.hallucination ?? ''}</td>
            <td>${ev.completeness ?? ''}</td>
            <td>${ev.authoritative ?? ''}</td>
            <td>${ev.usefulness ?? ''}</td>
            <td>${ev.pass_fail ?? ''}</td>
            <td>${ev.comments ? ev.comments.replace(/</g, '&lt;').replace(/>/g, '&gt;') : ''}</td>
            <td>${ev.timestamp ? new Date(ev.timestamp).toLocaleString() : ''}</td>
            <td><button class="eval-delete-btn" onclick="showDeleteEvalModal(${ev.id}, '${evaluatorEscaped}', '${questionPreview}')">Delete</button></td>
        </tr>`;
    });
    
    // Add average summary row
    html += `<tr class="admin-summary-row">
        <td><strong>AVERAGE (${row.count} evaluators)</strong></td>
        <td><em>N/A</em></td>
        <td><strong>${row.avg_accuracy ?? 'N/A'}</strong></td>
        <td><strong>${row.avg_hallucination ?? 'N/A'}</strong></td>
        <td><strong>${row.avg_completeness ?? 'N/A'}</strong></td>
        <td><strong>${row.avg_authoritative ?? 'N/A'}</strong></td>
        <td><strong>${row.avg_usefulness ?? 'N/A'}</strong></td>
        <td><strong>${row.pass_rate}% (${row.pass_count}/${row.count})</strong></td>
        <td><em>N/A</em></td>
        <td><em>N/A</em></td>
        <td><em>N/A</em></td>
    </tr>`;
    
    html += '</tbody></table>';
    div.innerHTML = html;
}

function renderPagination() {
    const pag = document.getElementById('admin-pagination');
    pag.innerHTML = '';
    const totalPages = Math.ceil(filteredData.length / pageSize);
    for (let i = 1; i <= totalPages; i++) {
        const btn = document.createElement('button');
        btn.className = 'admin-pagination-btn' + (i === currentPage ? ' active' : '');
        btn.innerText = i;
        btn.onclick = function() {
            currentPage = i;
            renderTable();
            renderPagination();
        };
        pag.appendChild(btn);
    }
}

// Sorting
Array.from(document.querySelectorAll('#admin-table th')).forEach((th, idx) => {
    if (idx < 1 || idx > 6) return; // Only sort on metric columns (skip question and expand)
    const cols = ['count','avg_accuracy','avg_hallucination','avg_completeness','avg_authoritative','avg_usefulness','pass_rate'];
    th.style.cursor = 'pointer';
    th.onclick = function() {
        const col = cols[idx-1];
        if (currentSort.col === col) currentSort.dir *= -1;
        else currentSort = { col, dir: 1 };
        renderTable();
    };
});

// Export
function downloadCSV(rows, filename) {
    const csv = rows.map(r => r.map(x => {
        if (x === null || x === undefined) return '""';
        const str = x.toString();
        // Escape quotes and newlines for CSV
        return '"' + str.replace(/"/g, '""').replace(/\n/g, ' ').replace(/\r/g, ' ') + '"';
    }).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

document.getElementById('export-cumulative').onclick = function() {
    const rows = [[
        'Question','Count','Avg Accuracy','Avg Hallucination','Avg Completeness','Avg Authoritative','Avg Usefulness','Pass Count','Fail Count','Pass Rate (%)'
    ]];
    allData.forEach(row => {
        rows.push([
            row.question, row.count, row.avg_accuracy, row.avg_hallucination, row.avg_completeness, row.avg_authoritative, row.avg_usefulness, row.pass_count, row.fail_count, row.pass_rate
        ]);
    });
    downloadCSV(rows, 'cumulative_scores.csv');
};

document.getElementById('export-individual').onclick = function() {
    const rows = [[
        'Question','AI Response','Evaluator','Accuracy','Hallucination','Completeness','Authoritative','Usefulness','Pass/Fail','Comments','Timestamp'
    ]];
    allData.forEach(row => {
        row.evaluations.forEach(ev => {
            rows.push([
                row.question, ev.ai_response, ev.evaluator, ev.accuracy, ev.hallucination, ev.completeness, ev.authoritative, ev.usefulness, ev.pass_fail, ev.comments, ev.timestamp
            ]);
        });
    });
    downloadCSV(rows, 'individual_scores.csv');
};

document.getElementById('export-full-responses').onclick = function() {
    const rows = [[
        'Question','Evaluator','AI Response (Full)','Response Generated','Accuracy','Hallucination','Completeness','Authoritative','Usefulness','Pass/Fail','Comments','Timestamp'
    ]];
    allData.forEach(row => {
        row.evaluations.forEach(ev => {
            rows.push([
                row.question, 
                ev.evaluator, 
                ev.ai_response || '', 
                ev.response_generated ? 'Yes' : 'No',
                ev.accuracy || '', 
                ev.hallucination || '', 
                ev.completeness || '', 
                ev.authoritative || '', 
                ev.usefulness || '', 
                ev.pass_fail || '', 
                ev.comments || '', 
                ev.timestamp || ''
            ]);
        });
    });
    downloadCSV(rows, 'full_ai_responses.csv');
};

// Initial load
fetchProgress();
fetchAllData();

// Delete functionality
let currentDeleteEvalId = null;
let currentDeleteUserName = null;

function showDeleteEvalModal(evalId, evaluator, question) {
    currentDeleteEvalId = evalId;
    document.getElementById('delete-eval-details').innerHTML = `
        <strong>Evaluator:</strong> ${evaluator}<br>
        <strong>Question:</strong> ${question}
    `;
    document.getElementById('delete-eval-modal').style.display = 'block';
}

function showDeleteUserModal(userName) {
    currentDeleteUserName = userName;
    document.getElementById('delete-user-name').textContent = userName;
    document.getElementById('delete-user-modal').style.display = 'block';
}

async function deleteEvaluation(evalId) {
    try {
        const response = await fetch(`/api/eval/${evalId}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            const result = await response.json();
            alert(result.message);
            // Refresh data
            await fetchAllData();
            await fetchProgress();
        } else {
            const error = await response.json();
            alert('Error: ' + error.error);
        }
    } catch (error) {
        alert('Error deleting evaluation: ' + error.message);
    }
}

async function deleteUser(userName, deleteEvals) {
    try {
        const response = await fetch(`/api/evaluators/${encodeURIComponent(userName)}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ delete_evals: deleteEvals })
        });
        
        if (response.ok) {
            const result = await response.json();
            alert(result.message);
            // Refresh data
            await fetchAllData();
            await fetchProgress();
        } else {
            const error = await response.json();
            alert('Error: ' + error.error);
        }
    } catch (error) {
        alert('Error deleting user: ' + error.message);
    }
}

// Modal event handlers
document.getElementById('close-delete-eval-modal').onclick = function() {
    document.getElementById('delete-eval-modal').style.display = 'none';
    currentDeleteEvalId = null;
};

document.getElementById('close-delete-user-modal').onclick = function() {
    document.getElementById('delete-user-modal').style.display = 'none';
    currentDeleteUserName = null;
};

document.getElementById('cancel-delete-eval').onclick = function() {
    document.getElementById('delete-eval-modal').style.display = 'none';
    currentDeleteEvalId = null;
};

document.getElementById('cancel-delete-user').onclick = function() {
    document.getElementById('delete-user-modal').style.display = 'none';
    currentDeleteUserName = null;
};

document.getElementById('confirm-delete-eval').onclick = async function() {
    if (currentDeleteEvalId) {
        await deleteEvaluation(currentDeleteEvalId);
        document.getElementById('delete-eval-modal').style.display = 'none';
        currentDeleteEvalId = null;
    }
};

document.getElementById('confirm-delete-user').onclick = async function() {
    if (currentDeleteUserName) {
        const deleteOption = document.querySelector('input[name="delete-option"]:checked').value;
        const deleteEvals = deleteOption === 'user-and-evals';
        await deleteUser(currentDeleteUserName, deleteEvals);
        document.getElementById('delete-user-modal').style.display = 'none';
        currentDeleteUserName = null;
    }
};

// AI Response Modal event handlers
document.getElementById('close-ai-response-modal').onclick = function() {
    document.getElementById('ai-response-modal').style.display = 'none';
};

document.getElementById('close-ai-response-btn').onclick = function() {
    document.getElementById('ai-response-modal').style.display = 'none';
};

document.getElementById('copy-ai-response-btn').onclick = function() {
    const aiResponseText = document.getElementById('ai-response-text').textContent;
    navigator.clipboard.writeText(aiResponseText).then(function() {
        // Temporarily change button text to show success
        const btn = document.getElementById('copy-ai-response-btn');
        const originalText = btn.textContent;
        btn.textContent = 'Copied!';
        btn.style.background = '#28a745';
        setTimeout(() => {
            btn.textContent = originalText;
            btn.style.background = '';
        }, 2000);
    }).catch(function(err) {
        console.error('Could not copy text: ', err);
        alert('Failed to copy to clipboard');
    });
};

// AI Response Modal functionality
function showAIResponseModal(aiResponse, evaluator, question) {
    document.getElementById('ai-response-question').textContent = question;
    document.getElementById('ai-response-evaluator').textContent = evaluator;
    // Render as HTML (not textContent)
    document.getElementById('ai-response-text').innerHTML = aiResponse;
    document.getElementById('ai-response-modal').style.display = 'block';
}

// Delegated event handler for View Full buttons
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('view-full-btn')) {
        const aiResponse = decodeURIComponent(e.target.getAttribute('data-ai-response'));
        const evaluator = decodeURIComponent(e.target.getAttribute('data-evaluator'));
        const question = decodeURIComponent(e.target.getAttribute('data-question'));
        showAIResponseModal(aiResponse, evaluator, question);
    }
});

// Close modals when clicking outside
window.onclick = function(event) {
    const evalModal = document.getElementById('delete-eval-modal');
    const userModal = document.getElementById('delete-user-modal');
    const aiResponseModal = document.getElementById('ai-response-modal');
    
    if (event.target === evalModal) {
        evalModal.style.display = 'none';
        currentDeleteEvalId = null;
    }
    
    if (event.target === userModal) {
        userModal.style.display = 'none';
        currentDeleteUserName = null;
    }
    
    if (event.target === aiResponseModal) {
        aiResponseModal.style.display = 'none';
    }
}; 