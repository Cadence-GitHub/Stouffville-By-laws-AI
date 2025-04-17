// DOM Elements
const themeToggle = document.getElementById('theme-toggle');
const contentArea = document.getElementById('content');
const closeButton = document.getElementById('close-button');

// Theme toggle functionality
themeToggle.addEventListener('change', function() {
    if (this.checked) {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('theme', 'light');
    }
});

// Check for saved theme preference
const savedTheme = localStorage.getItem('theme');
if (savedTheme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
    themeToggle.checked = true;
}

// Close button functionality
closeButton.addEventListener('click', function() {
    // If opened in iframe (sidebar mode)
    if (window.parent !== window) {
        window.parent.postMessage('close-bylaw-sidebar', '*');
    } else {
        // If opened directly, go back or close
        if (window.history.length > 1) {
            window.history.back();
        } else {
            window.close();
        }
    }
});

// Function to format text with various separators
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
    
    // Handle pipe separators in non-table content for single pipes
    // We need to be careful not to affect table data
    if (!formattedText.includes('<table>')) {
        formattedText = formattedText.replace(/\|/g, ' | ');
    }
    
    return formattedText;
}

// Function to format tabular data
function formatTable(tableData) {
    if (!tableData || !tableData.length) return '';
    
    let html = '<table>';
    
    // Process header row
    const headerRow = tableData[0];
    const headers = headerRow.split('|');
    
    html += '<tr>';
    headers.forEach(header => {
        html += `<th>${header.trim()}</th>`;
    });
    html += '</tr>';
    
    // Process data rows
    for (let i = 1; i < tableData.length; i++) {
        const rowData = tableData[i].split('|');
        html += '<tr>';
        rowData.forEach(cell => {
            html += `<td>${cell.trim()}</td>`;
        });
        html += '</tr>';
    }
    
    html += '</table>';
    return html;
}

// Function to format lists
function formatList(listItems) {
    if (!listItems || !listItems.length) return '';
    
    let html = '<ul>';
    listItems.forEach(item => {
        html += `<li>${formatText(item)}</li>`;
    });
    html += '</ul>';
    
    return html;
}

// Function to display a bylaw
function displayBylaw(bylaw) {
    // Clear the content area
    contentArea.innerHTML = '';
    
    // Create the bylaw header
    const header = document.createElement('div');
    header.className = 'bylaw-header';
    header.innerHTML = `
        <h2 class="bylaw-title">${bylaw.bylawNumber}</h2>
        <h3 class="bylaw-subtitle">${bylaw.bylawType} (${bylaw.bylawYear})</h3>
    `;
    contentArea.appendChild(header);
    
    // Create the bylaw container
    const container = document.createElement('div');
    container.className = 'bylaw-container';
    
    // Determine if a field should be displayed - not empty, not "None", and not false
    function shouldDisplay(field) {
        if (field === undefined || field === null) return false;
        if (field === false) return false;
        if (typeof field === 'string' && (field.trim() === '' || field.toLowerCase() === 'none')) return false;
        if (Array.isArray(field) && field.length === 0) return false;
        if (Array.isArray(field) && field.length === 1 && field[0].toLowerCase() === 'none') return false;
        return true;
    }
    
    // Helper function to create a section
    function createSection(title, content, fullWidth = false, isHTML = false) {
        if (!shouldDisplay(content)) return null;
        
        const section = document.createElement('div');
        section.className = `bylaw-section ${fullWidth ? 'full-width' : ''}`;
        
        let formattedContent;
        if (isHTML) {
            formattedContent = content;
        } else if (Array.isArray(content)) {
            formattedContent = formatList(content);
        } else {
            formattedContent = `<p>${formatText(content)}</p>`;
        }
        
        section.innerHTML = `
            <h4 class="section-title">${title}</h4>
            <div class="section-content">
                ${formattedContent}
            </div>
        `;
        
        return section;
    }
    
    // Layman's explanation section
    const explanationSection = createSection('Summary', bylaw.laymanExplanation, true);
    if (explanationSection) container.appendChild(explanationSection);
    
    // Key dates and info section
    const datesSection = createSection('Key Dates', bylaw.keyDatesAndInfo);
    if (datesSection) container.appendChild(datesSection);
    
    // Conditions and clauses section
    const conditionsSection = createSection('Conditions and Clauses', bylaw.condtionsAndClauses);
    if (conditionsSection) container.appendChild(conditionsSection);
    
    // Legal Topics section
    const legalTopicsSection = createSection('Legal Topics', bylaw.legalTopics);
    if (legalTopicsSection) container.appendChild(legalTopicsSection);
    
    // Legislation section
    const legislationSection = createSection('Legislation', bylaw.legislation);
    if (legislationSection) container.appendChild(legislationSection);
    
    // Why Legislation section
    const whyLegislationSection = createSection('Why Legislation', bylaw.whyLegislation);
    if (whyLegislationSection) container.appendChild(whyLegislationSection);
    
    // Other Bylaws section
    const otherBylawsSection = createSection('Other Bylaws', bylaw.otherBylaws);
    if (otherBylawsSection) container.appendChild(otherBylawsSection);
    
    // Why Other Bylaws section
    const whyOtherBylawsSection = createSection('Why Other Bylaws', bylaw.whyOtherBylaws);
    if (whyOtherBylawsSection) container.appendChild(whyOtherBylawsSection);
    
    // Entity and designation section
    const entitySection = createSection('Entity and Designation', bylaw.entityAndDesignation);
    if (entitySection) container.appendChild(entitySection);
    
    // Other Entities Mentioned section
    const otherEntitiesSection = createSection('Other Entities Mentioned', bylaw.otherEntitiesMentioned);
    if (otherEntitiesSection) container.appendChild(otherEntitiesSection);
    
    // Location Addresses section
    if (shouldDisplay(bylaw.locationAddresses)) {
        const locationSection = document.createElement('div');
        locationSection.className = 'bylaw-section';
        locationSection.innerHTML = `<h4 class="section-title">Location Addresses</h4>`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'section-content';
        
        // Process locations - they might be separated by ||| or %%% or newlines
        let locations = [];
        if (typeof bylaw.locationAddresses === 'string') {
            // Split by various separators
            locations = bylaw.locationAddresses
                .split(/\|\|\||%%%|\n/)
                .map(loc => loc.trim())
                .filter(loc => loc && loc.toLowerCase() !== 'none');
        } else if (Array.isArray(bylaw.locationAddresses)) {
            locations = bylaw.locationAddresses.filter(loc => loc && loc.toLowerCase() !== 'none');
        }
        
        if (locations.length > 0) {
            const locationList = document.createElement('ul');
            locations.forEach(location => {
                const encodedLocation = encodeURIComponent(location + ', Ontario, Canada');
                const googleMapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodedLocation}`;
                
                const listItem = document.createElement('li');
                listItem.innerHTML = `<a href="${googleMapsUrl}" target="_blank" rel="noopener noreferrer">${location}</a>`;
                locationList.appendChild(listItem);
            });
            contentDiv.appendChild(locationList);
        } else {
            contentDiv.innerHTML = `<p>${formatText(bylaw.locationAddresses)}</p>`;
        }
        
        locationSection.appendChild(contentDiv);
        container.appendChild(locationSection);
    }
    
    // Money and Categories section
    const moneySection = createSection('Money and Categories', bylaw.moneyAndCategories);
    if (moneySection) container.appendChild(moneySection);
    
    // Keywords section
    const keywordsSection = createSection('Keywords', bylaw.keywords);
    if (keywordsSection) container.appendChild(keywordsSection);
    
    // Other Details section
    const otherDetailsSection = createSection('Other Details', bylaw.otherDetails);
    if (otherDetailsSection) container.appendChild(otherDetailsSection);
    
    // News Sources section
    const newsSourcesSection = createSection('News Sources', bylaw.newsSources);
    if (newsSourcesSection) container.appendChild(newsSourcesSection);
    
    // Image Description section
    if (bylaw.hasEmbeddedImages && shouldDisplay(bylaw.imageDesciption)) {
        const imageSection = createSection('Image Description', bylaw.imageDesciption);
        if (imageSection) container.appendChild(imageSection);
    }
    
    // Map Description section
    if (bylaw.hasEmbeddedMaps && shouldDisplay(bylaw.mapDescription)) {
        const mapSection = createSection('Map Description', bylaw.mapDescription);
        if (mapSection) container.appendChild(mapSection);
    }
    
    // URL Original Document section
    if (shouldDisplay(bylaw.urlOriginalDocument)) {
        const urlSection = document.createElement('div');
        urlSection.className = 'bylaw-section';
        
        // Extract the PDF filename from the URL
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
        
        urlSection.innerHTML = `
            <h4 class="section-title">Original Town Document</h4>
            <div class="section-content">
                <p><a href="${bylaw.urlOriginalDocument}" target="_blank" rel="noopener noreferrer">${pdfName}</a></p>
            </div>
        `;
        container.appendChild(urlSection);
    }
    
    // Table section
    if (shouldDisplay(bylaw.table)) {
        const tableContent = formatTable(bylaw.table);
        const tableSection = createSection('Table Data', tableContent, true, true);
        if (tableSection) container.appendChild(tableSection);
    }
    
    // Full text section
    if (shouldDisplay(bylaw.extractedText)) {
        const textContent = Array.isArray(bylaw.extractedText) 
            ? bylaw.extractedText.join('\n') 
            : bylaw.extractedText;
        
        const textSection = document.createElement('div');
        textSection.className = 'bylaw-section full-width';
        textSection.innerHTML = `
            <h4 class="section-title">Full Text</h4>
            <div class="section-content">
                <div class="bylaw-text">${formatText(textContent)}</div>
            </div>
        `;
        container.appendChild(textSection);
    }
    
    // Add the container to the content area
    contentArea.appendChild(container);
}

// Fetch and display bylaw on page load
document.addEventListener('DOMContentLoaded', function() {
    // Get bylaw ID from URL
    const urlParams = new URLSearchParams(window.location.search);
    const bylawId = urlParams.get('bylaw');
    
    if (!bylawId) {
        contentArea.innerHTML = `
            <div class="error-message">
                <h2>Error: No bylaw ID specified</h2>
                <p>Please provide a bylaw ID in the URL query parameter.</p>
            </div>
        `;
        return;
    }
    
    // Fetch the bylaw data
    fetch(`/api/bylaw/${bylawId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to fetch bylaw: ${response.statusText}`);
            }
            return response.json();
        })
        .then(bylaw => {
            // Display the bylaw
            displayBylaw(bylaw);
        })
        .catch(error => {
            contentArea.innerHTML = `
                <div class="error-message">
                    <h2>Error loading bylaw</h2>
                    <p>${error.message}</p>
                </div>
            `;
        });
}); 