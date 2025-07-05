document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const uploadContainer = document.getElementById('upload-container');
    const dashboardContent = document.getElementById('dashboard-content');
    const fileInput = document.getElementById('file-input');
    const messageArea = document.getElementById('message-area');
    const queryFilterStatus = document.getElementById('query-filter-status');
    const filterText = document.getElementById('filter-text');
    const resetFilterBtn = document.getElementById('reset-filter-btn');

    // App State
    let allEntries = [];
    let charts = {};
    let queryTable = null;

    function handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) {
            return;
        }

        const reader = new FileReader();

        reader.onload = function(e) {
            try {
                const data = JSON.parse(e.target.result);
                allEntries = data.analyzed_entries || [];

                if (allEntries.length === 0) {
                    throw new Error('No "analyzed_entries" found in the JSON file.');
                }
                
                // Hide upload UI and show dashboard
                uploadContainer.style.display = 'none';
                dashboardContent.style.display = 'block';

                initializeDashboard(allEntries);

            } catch (error) {
                messageArea.textContent = `Error: ${error.message}. Please upload a valid analysis JSON file.`;
                messageArea.className = 'alert alert-danger mt-3';
            }
        };

        reader.onerror = function() {
            messageArea.textContent = 'Error reading the file.';
            messageArea.className = 'alert alert-danger mt-3';
        };

        messageArea.textContent = `Reading ${file.name}...`;
        messageArea.className = 'alert alert-info mt-3';
        reader.readAsText(file);
    }

    function initializeDashboard(entries) {
        calculateAndRenderKPIs(entries);
        renderCharts(entries);
        initializeQueryTable(entries);
        setupModal();
    }
    
    function calculateAndRenderKPIs(entries) {
        document.getElementById('kpi-total-queries').textContent = entries.length;
        const correctnessScores = entries.map(e => e.analysis.answer_correctness_score).filter(s => s !== null);
        const avgCorrectness = correctnessScores.length > 0 ? (correctnessScores.reduce((a, b) => a + b, 0) / correctnessScores.length) : 0;
        document.getElementById('kpi-avg-correctness').textContent = avgCorrectness.toFixed(2);
        const hallucinations = entries.filter(e => e.analysis.hallucination_flag === true).length;
        document.getElementById('kpi-hallucinations').textContent = hallucinations;
        const processingTimes = entries.map(e => e.analysis.total_processing_time).filter(t => t !== null);
        const avgTime = processingTimes.length > 0 ? (processingTimes.reduce((a, b) => a + b, 0) / processingTimes.length) : 0;
        document.getElementById('kpi-avg-time').textContent = avgTime.toFixed(2) + 's';
        const langMismatches = entries.filter(e => e.analysis.query_and_response_language_match === false).length;
        document.getElementById('kpi-lang-mismatch').textContent = langMismatches;
        const uniqueTopics = new Set(entries.map(e => e.analysis.query_category).filter(c => c)).size;
        document.getElementById('kpi-unique-categories').textContent = uniqueTopics;
    }

    function destroyCharts() {
        Object.values(charts).forEach(chart => chart.destroy());
        charts = {};
    }

    function renderCharts(entries) {
        destroyCharts();

        const categoryCounts = entries.reduce((acc, e) => {
            const category = e.analysis.query_category || 'Uncategorized';
            if (!acc[category]) {
                acc[category] = { original: 0, duplicate: 0, total: 0 };
            }
            if (e.analysis.is_duplicate_of === null) {
                acc[category].original += 1;
            } else {
                acc[category].duplicate += 1;
            }
            acc[category].total += 1;
            return acc;
        }, {});

        const sortedCategories = Object.entries(categoryCounts).sort(([, a], [, b]) => b.total - a.total);
        const labels = sortedCategories.map(([label]) => label);
        const originalData = sortedCategories.map(([, counts]) => counts.original);
        const duplicateData = sortedCategories.map(([, counts]) => counts.duplicate);

        charts.category = new Chart(document.getElementById('category-chart').getContext('2d'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Original Queries',
                        data: originalData,
                        backgroundColor: 'rgba(54, 162, 235, 0.6)', // Blue
                    },
                    {
                        label: 'Duplicate Queries',
                        data: duplicateData,
                        backgroundColor: 'rgba(255, 99, 132, 0.6)', // Pink
                    }
                ]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { stacked: true },
                    y: { stacked: true }
                }
            }
        });

        const correctnessCounts = entries.reduce((acc, e) => {
            const score = e.analysis.answer_correctness_score || 'N/A';
            acc[score] = (acc[score] || 0) + 1;
            return acc;
        }, {});
        const sortedCorrectnessKeys = Object.keys(correctnessCounts).sort();
        charts.correctness = new Chart(document.getElementById('correctness-chart').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: sortedCorrectnessKeys,
                datasets: [{
                    label: 'Count',
                    data: sortedCorrectnessKeys.map(key => correctnessCounts[key]),
                    backgroundColor: ['#dc3545', '#fd7e14', '#ffc107', '#0dcaf0', '#20c997', '#adb5bd']
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });

        const bottleneckCounts = entries.reduce((acc, e) => {
            const bottleneck = e.analysis.bottleneck_component || 'Unknown';
            acc[bottleneck] = (acc[bottleneck] || 0) + 1;
            return acc;
        }, {});
        charts.bottleneck = new Chart(document.getElementById('bottleneck-chart').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: Object.keys(bottleneckCounts),
                datasets: [{ data: Object.values(bottleneckCounts), backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'] }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
        
        const impactCounts = entries.reduce((acc, e) => {
            const impact = e.analysis.transform_impact_on_cited_bylaws || 'N/A';
            acc[impact] = (acc[impact] || 0) + 1;
            return acc;
        }, {});
        charts.impact = new Chart(document.getElementById('transform-impact-chart').getContext('2d'), {
            type: 'pie',
            data: {
                labels: Object.keys(impactCounts),
                datasets: [{ data: Object.values(impactCounts), backgroundColor: ['#4BC0C0', '#FF6384', '#FFCE56'] }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        reverse: true
                    }
                }
            }
        });

        const perfectAnswers = entries.filter(e => {
            const analysis = e.analysis;
            return analysis.answer_correctness_score === 5 &&
                   analysis.answer_clarity_score === 5 &&
                   analysis.summary_quality_score === 5 &&
                   analysis.hallucination_flag === false &&
                   analysis.is_slow_query === false &&
                   analysis.query_and_response_language_match === true;
        }).length;
        const notPerfectAnswers = entries.length - perfectAnswers;

        charts.perfectAnswer = new Chart(document.getElementById('perfect-answer-chart').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Perfect', 'Not Perfect'],
                datasets: [{
                    data: [perfectAnswers, notPerfectAnswers],
                    backgroundColor: ['#28a745', '#dc3545']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        reverse: true
                    }
                },
                onClick: (evt) => {
                    const activePoints = charts.perfectAnswer.getElementsAtEventForMode(evt, 'nearest', { intersect: true }, true);
                    if (!activePoints.length) return;

                    const firstPoint = activePoints[0];
                    const label = charts.perfectAnswer.data.labels[firstPoint.index];

                    const isPerfect = e => {
                        const analysis = e.analysis;
                        return analysis.answer_correctness_score === 5 &&
                               analysis.answer_clarity_score === 5 &&
                               analysis.summary_quality_score === 5 &&
                               analysis.hallucination_flag === false &&
                               analysis.is_slow_query === false &&
                               analysis.query_and_response_language_match === true;
                    };

                    let filteredEntries;
                    let filterDescription;

                    if (label === 'Not Perfect') {
                        filteredEntries = allEntries.filter(e => !isPerfect(e));
                        filterDescription = `Showing ${filteredEntries.length} "Not Perfect" queries.`;
                    } else if (label === 'Perfect') {
                        filteredEntries = allEntries.filter(isPerfect);
                        filterDescription = `Showing ${filteredEntries.length} "Perfect" queries.`;
                    } else {
                        return;
                    }

                    queryTable.clear().rows.add(filteredEntries).draw();
                    filterText.textContent = filterDescription;
                    queryFilterStatus.style.display = 'block';
                }
            }
        });
    }

    function initializeQueryTable(entries) {
        if (queryTable) {
            queryTable.destroy();
        }
        queryTable = new DataTable('#query-table', {
            data: entries,
            responsive: true,
            pageLength: 25,
            lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
            columns: [
                { data: 'original_data.timestamp' },
                { data: 'original_data.query', render: (data) => data.length > 70 ? `${data.substring(0, 70)}...` : data },
                { data: 'analysis.query_category' },
                { data: 'analysis.answer_correctness_score' },
                {
                    data: 'analysis.total_processing_time',
                    render: (data, type) => {
                        if (type === 'display' && data !== null) {
                            return `${data.toFixed(2)}s`;
                        }
                        if (type === 'display' && data === null) {
                            return 'N/A';
                        }
                        return data;
                    }
                },
                { data: 'analysis.transform_impact_on_cited_bylaws' },
                { data: 'analysis.query_language' },
                {
                    data: null,
                    orderable: true,
                    render: (data, type, row) => {
                        if (type === 'sort') {
                            // Assign weights for sorting: Hallucination > Mismatch > Slow
                            return (row.analysis.hallucination_flag ? 4 : 0) +
                                   (row.analysis.query_and_response_language_match === false ? 2 : 0) +
                                   (row.analysis.is_slow_query ? 1 : 0);
                        }
                        let flags = '';
                        if (row.analysis.hallucination_flag) flags += '<i class="fas fa-brain flag-icon hallucination" title="Hallucination Flag"></i> ';
                        if (row.analysis.is_slow_query) flags += '<i class="fas fa-hourglass-half flag-icon slow-query" title="Slow Query"></i> ';
                        if (row.analysis.query_and_response_language_match === false) flags += '<i class="fas fa-language flag-icon lang-mismatch" title="Language Mismatch"></i>';
                        return flags;
                    }
                }
            ]
        });
    }
    
    function setupModal() {
        const detailModal = new bootstrap.Modal(document.getElementById('detail-modal'));
        $('#query-table tbody').on('click', 'tr', function () {
            const rowData = queryTable.row(this).data();
            if (rowData) {
                populateModal(rowData);
                detailModal.show();
            }
        });
    }

    function populateModal(entry) {
        const { original_data, analysis } = entry;
        document.getElementById('modal-original-query').textContent = original_data.query;
        document.getElementById('modal-transformed-query').textContent = original_data.transformed_query;
        document.getElementById('modal-filtered-answer').innerHTML = original_data.filtered_answer;
        document.getElementById('modal-laymans-answer').innerHTML = original_data.laymans_answer;
        const renderBylawList = (elementId, bylawList, citedList) => {
            const listEl = document.getElementById(elementId);
            listEl.innerHTML = '';
            (bylawList || []).forEach(bylaw => {
                const li = document.createElement('li');
                li.textContent = bylaw;
                if (citedList && citedList.includes(bylaw)) li.classList.add('cited');
                listEl.appendChild(li);
            });
        };
        const citedBylaws = analysis.cited_bylaws_in_answer || [];
        renderBylawList('modal-original-bylaws', original_data.original_bylaws, citedBylaws);
        renderBylawList('modal-additional-bylaws', original_data.additional_bylaws, citedBylaws);
        renderBylawList('modal-cited-bylaws', citedBylaws, null);
        const vitalsContainer = document.getElementById('modal-vitals');
        vitalsContainer.innerHTML = '';
        const vitals = {
            "Query Group ID": analysis.query_group_id, "Query Complexity": analysis.query_complexity,
            "Query Language": analysis.query_language, "Language Match": analysis.query_and_response_language_match,
            "<hr/>": "", "Correctness Score": analysis.answer_correctness_score,
            "Clarity Score": analysis.answer_clarity_score, "Summary Quality": analysis.summary_quality_score,
            "Hallucination Flag": analysis.hallucination_flag, "<hr/>": "",
            "Total Time": `${analysis.total_processing_time}s`, "Bottleneck": analysis.bottleneck_component,
            "Slow Query": analysis.is_slow_query,
        };
        for (const [key, value] of Object.entries(vitals)) {
            if (key.startsWith('<hr')) {
                vitalsContainer.innerHTML += '<div class="col-12"><hr/></div>'; continue;
            }
            const col = document.createElement('div');
            col.className = 'col-md-4 mb-2';
            col.innerHTML = `<span class="vitals-key">${key}:</span> ${value !== null ? value : 'N/A'}`;
            vitalsContainer.appendChild(col);
        }
    }

    // --- Main execution ---
    fileInput.addEventListener('change', handleFileSelect);

    resetFilterBtn.addEventListener('click', () => {
        queryFilterStatus.style.display = 'none';
        queryTable.clear().rows.add(allEntries).draw();
    });
});