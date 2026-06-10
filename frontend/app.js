// State variables
let suggestions = [];
let selectedIndex = -1;
let latencyHistory = [0.004, 0.005, 0.003, 0.004, 0.003, 0.005, 0.004]; // Initial dummy data for look
const API_URL = ''; // Relative path since we serve from same origin
let recentSearches = [];

// DOM Elements
const searchInput = document.getElementById('search-input');
const suggestionsContainer = document.getElementById('suggestions-container');
const suggestionsList = document.getElementById('suggestions-list');
const welcomeState = document.getElementById('welcome-state');
const resultsCount = document.getElementById('results-count');
const queryTimeBadge = document.getElementById('query-time-badge');
const queryTimeVal = document.getElementById('query-time-val');

// Trie Path Elements
const triePathContainer = document.getElementById('trie-path-container');
const triePathNodes = document.getElementById('trie-path-nodes');
const triePathStatus = document.getElementById('trie-path-status');

// Recent Searches Elements
const recentSearchesContainer = document.getElementById('recent-searches-container');
const recentSearchesList = document.getElementById('recent-searches-list');

// Popular Leaderboard Elements
const popularSearchesList = document.getElementById('popular-searches-list');

// Stats Elements
const statTotalCities = document.getElementById('stat-total-cities');
const statTrieNodes = document.getElementById('stat-trie-nodes');
const statBuildTime = document.getElementById('stat-build-time');
const statQueriesRun = document.getElementById('stat-queries-run');
const avgLatencyVal = document.getElementById('avg-latency-val');

// Sparkline Elements
const sparklinePath = document.getElementById('sparkline-path');
const sparklineArea = document.getElementById('sparkline-area');
const sparklineYMax = document.getElementById('sparkline-y-max');
const sparklineYMin = document.getElementById('sparkline-y-min');

// Theme toggle
const themeToggleBtn = document.getElementById('theme-toggle');
const moonIcon = document.getElementById('moon-icon');
const sunIcon = document.getElementById('sun-icon');

// Drawer Elements
const dbManagerToggle = document.getElementById('db-manager-toggle');
const dbDrawer = document.getElementById('db-drawer');
const dbClose = document.getElementById('db-close');
const drawerOverlay = document.getElementById('drawer-overlay');
const addCityForm = document.getElementById('add-city-form');
const removeCityForm = document.getElementById('remove-city-form');

// Notification Container
const notificationContainer = document.getElementById('notification-container');

// Demo suggestions
const demoTags = document.querySelectorAll('.demo-tag');

// ------------------------------------------------------------------ //
//  INITIALIZATION                                                    //
// ------------------------------------------------------------------ //

document.addEventListener('DOMContentLoaded', () => {
    // Initial fetch of statistics
    fetchStats();
    drawSparkline();
    setupTheme();
    initRecentSearches();

    // Event listeners
    searchInput.addEventListener('input', handleSearchInput);
    searchInput.addEventListener('keydown', handleSearchKeyboard);
    
    // Theme toggle
    themeToggleBtn.addEventListener('click', toggleTheme);

    // Database drawer controls
    dbManagerToggle.addEventListener('click', openDrawer);
    dbClose.addEventListener('click', closeDrawer);
    drawerOverlay.addEventListener('click', closeDrawer);

    // Form handlers
    addCityForm.addEventListener('submit', handleAddCity);
    removeCityForm.addEventListener('submit', handleRemoveCity);

    // Demo Tags
    demoTags.forEach(tag => {
        tag.addEventListener('click', () => {
            const query = tag.getAttribute('data-search');
            searchInput.value = query;
            searchInput.focus();
            performSearch(query);
        });
    });
});

// ------------------------------------------------------------------ //
//  SEARCH LOGIC & RENDERING                                          //
// ------------------------------------------------------------------ //

function handleSearchInput(e) {
    const query = e.target.value;
    performSearch(query);
}

function performSearch(query) {
    if (!query || !query.trim()) {
        suggestionsContainer.classList.add('hidden');
        welcomeState.classList.remove('hidden');
        queryTimeBadge.classList.add('hidden');
        if (triePathContainer) triePathContainer.classList.add('hidden');
        selectedIndex = -1;
        return;
    }

    // Measure request duration client side as backup, but we will fetch stats from backend
    const startTime = performance.now();

    fetch(`${API_URL}/api/suggest?q=${encodeURIComponent(query)}&limit=8`)
        .then(res => res.json())
        .then(data => {
            suggestions = data;
            renderSuggestions(suggestions, query);
            
            // Instantly fetch stats to get exact Trie search execution time
            fetchStats().then(stats => {
                if (stats) {
                    const elapsed = stats.last_query_ms;
                    
                    // Show query execution speed inside the search bar in milliseconds (or microseconds if very low)
                    if (elapsed < 0.1) {
                        const micros = (elapsed * 1000).toFixed(0);
                        queryTimeVal.innerText = `${micros} μs`;
                    } else {
                        queryTimeVal.innerText = `${elapsed.toFixed(3)} ms`;
                    }
                    queryTimeBadge.classList.remove('hidden');

                    // Render Trie Traversal Path
                    renderTriePath(stats.last_query_path, stats.last_query_failed);

                    // Track latency in history (only add if greater than 0)
                    if (elapsed > 0) {
                        latencyHistory.push(elapsed);
                        if (latencyHistory.length > 15) {
                            latencyHistory.shift();
                        }
                        drawSparkline();
                    }
                }
            });
        })
        .catch(err => {
            console.error('Error fetching suggestions:', err);
            showToast('Failed to fetch search suggestions', 'error');
        });
}

function renderSuggestions(list, query) {
    suggestionsList.innerHTML = '';
    selectedIndex = -1;

    if (list.length === 0) {
        const li = document.createElement('li');
        li.style.color = 'var(--text-muted)';
        li.style.justifyContent = 'center';
        li.innerText = `No cities match "${query}"`;
        suggestionsList.appendChild(li);
        resultsCount.innerText = '0 results';
    } else {
        list.forEach((item, index) => {
            const li = document.createElement('li');
            li.setAttribute('data-index', index);
            
            const cityHtml = highlightMatch(item.city, query);
            const tierLabel = item.tier === 1 ? 'Metro' : item.tier === 2 ? 'Major' : 'Other';

            li.innerHTML = `
                <div class="city-info">
                    <span class="city-name">${cityHtml}</span>
                    <span class="state-name">${item.state}</span>
                </div>
                <span class="tier-badge tier-${item.tier}">${tierLabel}</span>
            `;

            li.addEventListener('click', () => {
                selectSuggestion(index);
            });

            suggestionsList.appendChild(li);
        });
        resultsCount.innerText = `${list.length} results`;
    }

    welcomeState.classList.add('hidden');
    suggestionsContainer.classList.remove('hidden');
}

// Regex match highlight
function highlightMatch(text, query) {
    if (!query) return text;
    const index = text.toLowerCase().indexOf(query.toLowerCase());
    if (index === -1) return text;
    
    return text.substring(0, index) + 
           `<span class="highlight">${text.substring(index, index + query.length)}</span>` + 
           text.substring(index + query.length);
}

function selectSuggestion(index) {
    if (index >= 0 && index < suggestions.length) {
        const item = suggestions[index];
        searchInput.value = item.city;
        suggestionsContainer.classList.add('hidden');
        welcomeState.classList.remove('hidden');
        queryTimeBadge.classList.add('hidden');
        if (triePathContainer) triePathContainer.classList.add('hidden');
        
        showToast(`Selected: ${item.city}, ${item.state} (${item.tier === 1 ? 'Metro' : item.tier === 2 ? 'Major' : 'Other'})`, 'info');
        selectedIndex = -1;

        // Record the selection to the backend
        recordSelection(item.city, item.state);

        // Add to local recent searches
        addRecentSearch(item);
    }
}

// Keyboard navigation
function handleSearchKeyboard(e) {
    const listItems = suggestionsList.querySelectorAll('li');
    if (!listItems.length || suggestions.length === 0) return;

    if (e.key === 'ArrowDown') {
        e.preventDefault();
        selectedIndex = (selectedIndex + 1) % suggestions.length;
        updateSelectedHighlight(listItems);
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        selectedIndex = (selectedIndex - 1 + suggestions.length) % suggestions.length;
        updateSelectedHighlight(listItems);
    } else if (e.key === 'Enter') {
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
            selectSuggestion(selectedIndex);
        } else if (suggestions.length > 0) {
            selectSuggestion(0);
        }
    } else if (e.key === 'Escape') {
        e.preventDefault();
        searchInput.value = '';
        suggestionsContainer.classList.add('hidden');
        welcomeState.classList.remove('hidden');
        queryTimeBadge.classList.add('hidden');
        selectedIndex = -1;
        searchInput.blur();
    }
}

function updateSelectedHighlight(listItems) {
    listItems.forEach(li => li.classList.remove('selected'));
    if (selectedIndex >= 0 && selectedIndex < listItems.length) {
        const activeLi = listItems[selectedIndex];
        activeLi.classList.add('selected');
        // Scroll into view if needed
        activeLi.scrollIntoView({ block: 'nearest' });
    }
}

// ------------------------------------------------------------------ //
//  STATS AND METRICS CHART                                            //
// ------------------------------------------------------------------ //

async function fetchStats() {
    try {
        const res = await fetch(`${API_URL}/api/stats`);
        const data = await res.json();
        
        // Update dashboard elements
        statTotalCities.innerText = Number(data.total_cities).toLocaleString();
        statTrieNodes.innerText = Number(data.trie_nodes).toLocaleString();
        statBuildTime.innerText = `${parseFloat(data.build_time_ms).toFixed(1)} ms`;
        statQueriesRun.innerText = Number(data.queries_run).toLocaleString();

        // Calculate and update avg query speed from stats
        const avg = parseFloat(data.avg_query_ms);
        if (avg < 0.1) {
            avgLatencyVal.innerText = `Avg: ${(avg * 1000).toFixed(0)} μs`;
        } else {
            avgLatencyVal.innerText = `Avg: ${avg.toFixed(4)} ms`;
        }

        // Render popular searches leaderboard
        renderLeaderboard(data.most_searched);

        return data;
    } catch (err) {
        console.error('Error fetching statistics:', err);
        return null;
    }
}

function drawSparkline() {
    const points = latencyHistory;
    if (points.length === 0) return;

    const width = 200;
    const height = 50;
    const padding = 5;

    const yMax = Math.max(...points, 0.01) * 1.1; // pad max by 10%
    const yMin = 0; // standard floor to show relative zero

    // Update axis labels
    if (yMax < 0.1) {
        sparklineYMax.innerText = `${(yMax * 1000).toFixed(0)}μs`;
        sparklineYMin.innerText = `0μs`;
    } else {
        sparklineYMax.innerText = `${yMax.toFixed(2)}ms`;
        sparklineYMin.innerText = `0.0ms`;
    }

    const n = points.length;
    let pathD = '';
    let areaD = '';

    const getX = (i) => {
        if (n <= 1) return width / 2;
        return padding + (i / (n - 1)) * (width - 2 * padding);
    };

    const getY = (val) => {
        const ratio = val / yMax;
        return height - padding - ratio * (height - 2 * padding);
    };

    points.forEach((val, i) => {
        const x = getX(i);
        const y = getY(val);
        if (i === 0) {
            pathD = `M ${x} ${y}`;
            areaD = `M ${x} ${height} L ${x} ${y}`;
        } else {
            pathD += ` L ${x} ${y}`;
            areaD += ` L ${x} ${y}`;
        }
        if (i === n - 1) {
            areaD += ` L ${x} ${height} Z`;
        }
    });

    sparklinePath.setAttribute('d', pathD);
    sparklineArea.setAttribute('d', areaD);
}

// ------------------------------------------------------------------ //
//  DATABASE MANAGEMENT MODAL/DRAWER                                   //
// ------------------------------------------------------------------ //

function openDrawer() {
    dbDrawer.classList.add('open');
    document.getElementById('input-city').focus();
}

function closeDrawer() {
    dbDrawer.classList.remove('open');
}

function handleAddCity(e) {
    e.preventDefault();
    const cityInput = document.getElementById('input-city');
    const stateInput = document.getElementById('input-state');
    const tierInput = document.getElementById('input-tier');

    const payload = {
        city: cityInput.value,
        state: stateInput.value,
        tier: parseInt(tierInput.value)
    };

    fetch(`${API_URL}/api/add`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success || data.message) {
            showToast(data.message || 'City added successfully!', 'success');
            cityInput.value = '';
            stateInput.value = '';
            tierInput.value = '3';
            fetchStats();
        } else {
            showToast(data.error || 'Failed to add city', 'error');
        }
    })
    .catch(err => {
        console.error('Error adding city:', err);
        showToast('Server error during city insert', 'error');
    });
}

function handleRemoveCity(e) {
    e.preventDefault();
    const removeInput = document.getElementById('remove-city-input');
    const city = removeInput.value;

    fetch(`${API_URL}/api/remove`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ city })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast(data.message, 'success');
            removeInput.value = '';
            fetchStats();
            
            // If current input is the removed city, clear it
            if (searchInput.value.toLowerCase() === city.toLowerCase()) {
                searchInput.value = '';
                performSearch('');
            }

            // Also remove from recent searches if present
            removeRecentSearch(city);
        } else {
            showToast(data.message || 'City not found', 'error');
        }
    })
    .catch(err => {
        console.error('Error removing city:', err);
        showToast('Server error during city removal', 'error');
    });
}

// ------------------------------------------------------------------ //
//  THEME SWITCHER                                                    //
// ------------------------------------------------------------------ //

function setupTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.remove('dark-theme');
        document.body.classList.add('light-theme');
        moonIcon.classList.add('hidden');
        sunIcon.classList.remove('hidden');
    } else {
        document.body.classList.add('dark-theme');
        document.body.classList.remove('light-theme');
        sunIcon.classList.add('hidden');
        moonIcon.classList.remove('hidden');
    }
}

function toggleTheme() {
    if (document.body.classList.contains('dark-theme')) {
        document.body.classList.remove('dark-theme');
        document.body.classList.add('light-theme');
        moonIcon.classList.add('hidden');
        sunIcon.classList.remove('hidden');
        localStorage.setItem('theme', 'light');
    } else {
        document.body.classList.add('dark-theme');
        document.body.classList.remove('light-theme');
        sunIcon.classList.add('hidden');
        moonIcon.classList.remove('hidden');
        localStorage.setItem('theme', 'dark');
    }
}

// ------------------------------------------------------------------ //
//  TOAST NOTIFICATIONS SYSTEM                                        //
// ------------------------------------------------------------------ //

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '❌';

    toast.innerHTML = `
        <span>${icon}</span>
        <span>${message}</span>
    `;

    notificationContainer.appendChild(toast);

    // Fade out and remove after 3.5 seconds
    setTimeout(() => {
        toast.style.animation = 'toastOut 0.25s forwards';
        setTimeout(() => {
            toast.remove();
        }, 250);
    }, 3500);
}

// ------------------------------------------------------------------ //
//  HELPER FUNCTIONS FOR NEW FEATURES                                 //
// ------------------------------------------------------------------ //

// Record suggestion clicks to backend API
function recordSelection(city, state) {
    fetch(`${API_URL}/api/select`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ city, state })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            fetchStats(); // Update stats to refresh leaderboard click count
        }
    })
    .catch(err => {
        console.error('Error recording city selection:', err);
    });
}

// Render the Popular Search Leaderboard list
function renderLeaderboard(mostSearched) {
    if (!popularSearchesList) return;

    if (!mostSearched || mostSearched.length === 0) {
        popularSearchesList.innerHTML = `<div class="no-popular-data">No searches recorded yet. Select suggestions to start!</div>`;
        return;
    }

    popularSearchesList.innerHTML = '';
    const maxCount = Math.max(...mostSearched.map(x => x.count), 1);

    mostSearched.forEach(entry => {
        const widthPct = (entry.count / maxCount) * 100;
        const item = document.createElement('div');
        item.className = 'leaderboard-item';
        item.innerHTML = `
            <div class="leaderboard-item-header">
                <div>
                    <span class="leaderboard-item-city">${escapeHtml(entry.city)}</span>
                    <span class="leaderboard-item-state">${escapeHtml(entry.state)}</span>
                </div>
                <span class="leaderboard-item-count">${entry.count} search${entry.count > 1 ? 's' : ''}</span>
            </div>
            <div class="leaderboard-progress-bar">
                <div class="leaderboard-progress-fill" style="width: ${widthPct}%"></div>
            </div>
        `;
        popularSearchesList.appendChild(item);
    });
}

// Simple HTML escaping helper to prevent XSS
function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Render the Trie Traversal Path UI
function renderTriePath(path, failed) {
    if (!triePathContainer || !triePathNodes || !triePathStatus) return;

    if (!path || path.length <= 1) {
        triePathContainer.classList.add('hidden');
        return;
    }

    triePathNodes.innerHTML = '';
    triePathStatus.innerText = failed ? 'Path not found' : 'O(k) lookup';

    path.forEach((token, index) => {
        if (index > 0) {
            const arrow = document.createElement('span');
            arrow.className = 'trie-arrow';
            arrow.innerText = '➔';
            triePathNodes.appendChild(arrow);
        }

        const span = document.createElement('span');
        span.className = 'trie-node-token';
        if (token === 'Root') {
            span.classList.add('root-token');
        } else if (token === '❌') {
            span.classList.add('fail-token');
        }
        span.innerText = token;
        triePathNodes.appendChild(span);
    });

    triePathContainer.classList.remove('hidden');
}

// Initialize Recent Searches from localStorage
function initRecentSearches() {
    try {
        const stored = localStorage.getItem('recentSearches');
        if (stored) {
            recentSearches = JSON.parse(stored);
        }
    } catch (e) {
        console.error('Error loading recent searches:', e);
        recentSearches = [];
    }
    renderRecentSearches();
}

// Render Recent Searches list
function renderRecentSearches() {
    if (!recentSearchesContainer || !recentSearchesList) return;

    if (recentSearches.length === 0) {
        recentSearchesContainer.classList.add('hidden');
        return;
    }

    recentSearchesList.innerHTML = '';

    recentSearches.forEach(item => {
        const pill = document.createElement('div');
        pill.className = 'recent-pill';

        pill.addEventListener('click', (e) => {
            if (e.target.classList.contains('recent-pill-remove')) {
                return;
            }
            searchInput.value = item.city;
            searchInput.focus();
            performSearch(item.city);
        });

        const nameSpan = document.createElement('span');
        nameSpan.innerText = item.city;
        pill.appendChild(nameSpan);

        const removeSpan = document.createElement('span');
        removeSpan.className = 'recent-pill-remove';
        removeSpan.innerText = '×';
        removeSpan.addEventListener('click', (e) => {
            e.stopPropagation();
            removeRecentSearch(item.city);
        });
        pill.appendChild(removeSpan);

        recentSearchesList.appendChild(pill);
    });

    recentSearchesContainer.classList.remove('hidden');
}

// Add a search entry to recent searches list
function addRecentSearch(item) {
    recentSearches = recentSearches.filter(
        x => x.city.toLowerCase() !== item.city.toLowerCase()
    );

    recentSearches.unshift({
        city: item.city,
        state: item.state,
        tier: item.tier
    });

    if (recentSearches.length > 5) {
        recentSearches.pop();
    }

    try {
        localStorage.setItem('recentSearches', JSON.stringify(recentSearches));
    } catch (e) {
        console.error('Error saving recent searches:', e);
    }
    renderRecentSearches();
}

// Remove a specific search entry from recent searches list
function removeRecentSearch(city) {
    recentSearches = recentSearches.filter(
        x => x.city.toLowerCase() !== city.toLowerCase()
    );

    try {
        localStorage.setItem('recentSearches', JSON.stringify(recentSearches));
    } catch (e) {
        console.error('Error removing recent search:', e);
    }
    renderRecentSearches();
}
