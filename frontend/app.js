/**
 * Smart Garden Dashboard - Frontend JavaScript
 * Handles all UI interactions, API calls, and LLM integration
 */

// ============== Configuration ==============
// Dynamically determine API base URL based on current location
const API_BASE = `${window.location.protocol}//${window.location.host}/api`;

// ============== State ==============
let plants = [];
let tasks = [];
let harvests = [];
let notes = [];
let weather = [];
let weatherUnit = 'C';
let lastWeatherSearchResult = null;
let recipes = [];
let products = [];
let healthChart = null;
let growthChart = null;
let wateringChart = null;
let budgetCategoryChart = null;
let budgetMonthlyChart = null;
let plantGrowthChart = null;
let plantWateringChart = null;
let html5QrCode = null;
let scannedPlant = null;
let capturedPhotoData = null;

// Plants view state
let currentPlantsView = 'grid';
// Toggle state for views: allows multiple views to be visible and stacked
let viewVisibility = { grid: true, table: false, charts: false };
let plantSearchQuery = '';
let plantSortColumn = 'name';
let plantSortDirection = 'asc';

// Plants charts
let healthDistributionChart = null;
let growthComparisonChart = null;
let wateringFrequencyChart = null;
let locationDistributionChart = null;

// Leaderboard state
let leaderboardChart = null;
let selectedLeaderboardPlants = new Set(); // Empty = all plants

// ============== DOM Elements ==============
const elements = {
    // Navigation
    navItems: document.querySelectorAll('.nav-item'),
    pages: document.querySelectorAll('.page'),
    pageTitle: document.getElementById('pageTitle'),
    currentDate: document.getElementById('currentDate'),

    // LLM Status
    llmStatusDot: document.getElementById('llmStatusDot'),
    llmStatusText: document.getElementById('llmStatusText'),
    llmSettingsBtn: document.getElementById('llmSettingsBtn'),
    llmSettingsOverlay: document.getElementById('llmSettingsOverlay'),
    llmSettingsClose: document.getElementById('llmSettingsClose'),
    llmUrlInput: document.getElementById('llmUrlInput'),
    llmModelInput: document.getElementById('llmModelInput'),
    llmModelSelect: document.getElementById('llmModelSelect'),
    contextLengthInput: document.getElementById('contextLengthInput'),
    contextLengthValue: document.getElementById('contextLengthValue'),
    gpuLayersInput: document.getElementById('gpuLayersInput'),
    gpuLayersValue: document.getElementById('gpuLayersValue'),
    cpuThreadsInput: document.getElementById('cpuThreadsInput'),
    cpuThreadsValue: document.getElementById('cpuThreadsValue'),
    settingsStatusDot: document.getElementById('settingsStatusDot'),
    settingsStatusText: document.getElementById('settingsStatusText'),
    statusDetails: document.getElementById('statusDetails'),
    testConnectionBtn: document.getElementById('testConnectionBtn'),
    testToolsBtn: document.getElementById('testToolsBtn'),
    saveSettingsBtn: document.getElementById('saveSettingsBtn'),
    resetSettingsBtn: document.getElementById('resetSettingsBtn'),
    viewLogsBtn: document.getElementById('viewLogsBtn'),
    logsContainer: document.getElementById('logsContainer'),
    logsContent: document.getElementById('logsContent'),

    // Note Input
    noteInput: document.getElementById('noteInput'),
    processNoteBtn: document.getElementById('processNoteBtn'),
    clearNoteBtn: document.getElementById('clearNoteBtn'),
    extractedActions: document.getElementById('extractedActions'),
    quickNoteBtn: document.getElementById('quickNoteBtn'),

    // Stats
    statPlants: document.getElementById('statPlants'),
    statTasks: document.getElementById('statTasks'),
    statHarvests: document.getElementById('statHarvests'),
    statPests: document.getElementById('statPests'),

    // Lists
    upcomingTasks: document.getElementById('upcomingTasks'),
    plantsList: document.getElementById('plantsList'),
    plantsTable: document.getElementById('plantsTable'),
    plantsTableBody: document.getElementById('plantsTableBody'),
    plantsCharts: document.getElementById('plantsCharts'),
    tasksList: document.getElementById('tasksList'),
    harvestsList: document.getElementById('harvestsList'),
    notesList: document.getElementById('notesList'),
    weatherList: document.getElementById('weatherList'),
    weatherSearchInput: document.getElementById('weatherSearchInput'),
    fetchWeatherBtn: document.getElementById('fetchWeatherBtn'),
    weatherSearchResult: document.getElementById('weatherSearchResult'),

    // Leaderboard
    leaderboardMetric: document.getElementById('leaderboardMetric'),
    leaderboardCategory: document.getElementById('leaderboardCategory'),

    // Weather
    weatherUnitToggle: document.getElementById('weatherUnitToggle'),

    selectPlantsBtn: document.getElementById('selectPlantsBtn'),
    selectedPlantsCount: document.getElementById('selectedPlantsCount'),
    leaderboardChartTitle: document.getElementById('leaderboardChartTitle'),
    leaderboardRankings: document.getElementById('leaderboardRankings'),
    recipesList: document.getElementById('recipesList'),
    productsList: document.getElementById('productsList'),

    // Plants View Controls
    viewToggleBtns: document.querySelectorAll('.view-btn'),
    plantSearchInput: document.getElementById('plantSearchInput'),

    // Budget Summary
    totalSpent: document.getElementById('totalSpent'),
    totalProducts: document.getElementById('totalProducts'),
    activeRecipes: document.getElementById('activeRecipes'),

    // Chart Filters
    growthPlantFilter: document.getElementById('growthPlantFilter'),
    wateringPlantFilter: document.getElementById('wateringPlantFilter'),

    // Filters
    plantStatusFilter: document.getElementById('plantStatusFilter'),
    taskFilter: document.getElementById('taskFilter'),

    // Buttons
    addPlantBtn: document.getElementById('addPlantBtn'),
    addTaskBtn: document.getElementById('addTaskBtn'),
    addWeatherBtn: document.getElementById('addWeatherBtn'),
    addRecipeBtn: document.getElementById('addRecipeBtn'),
    addProductBtn: document.getElementById('addProductBtn'),

    // Modal
    modalOverlay: document.getElementById('modalOverlay'),
    modal: document.getElementById('modal'),
    modalTitle: document.getElementById('modalTitle'),
    modalBody: document.getElementById('modalBody'),
    modalClose: document.getElementById('modalClose'),

    // Toast
    toastContainer: document.getElementById('toastContainer'),

    // Mobile Menu
    mobileMenuToggle: document.getElementById('mobileMenuToggle'),
    sidebar: document.querySelector('.sidebar'),

    // Scanner
    scannerTabs: document.querySelectorAll('.scanner-tab'),
    scanMode: document.getElementById('scanMode'),
    createMode: document.getElementById('createMode'),
    qrReader: document.getElementById('qrReader'),
    startScannerBtn: document.getElementById('startScannerBtn'),
    stopScannerBtn: document.getElementById('stopScannerBtn'),
    scanResult: document.getElementById('scanResult'),
    scanPlantName: document.getElementById('scanPlantName'),
    scanPlantCode: document.getElementById('scanPlantCode'),
    scanPlantStatus: document.getElementById('scanPlantStatus'),
    scanPlantId: document.getElementById('scanPlantId'),
    scanNoteInput: document.getElementById('scanNoteInput'),
    processScanNoteBtn: document.getElementById('processScanNoteBtn'),
    clearScanBtn: document.getElementById('clearScanBtn'),
    scanExtractedActions: document.getElementById('scanExtractedActions'),
    photoPreview: document.getElementById('photoPreview'),
    plantPhotoInput: document.getElementById('plantPhotoInput'),
    scanPlantNameInput: document.getElementById('scanPlantNameInput'),
    scanVarietyInput: document.getElementById('scanVarietyInput'),
    scanQuantityInput: document.getElementById('scanQuantityInput'),
    scanLocationInput: document.getElementById('scanLocationInput'),
    scanNotesInput: document.getElementById('scanNotesInput'),
    createScanPlantBtn: document.getElementById('createScanPlantBtn')
};

// ============== Initialization ==============
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => initApp());
} else {
    // If script loaded after DOMContentLoaded, call init immediately
    initApp();
}

async function initApp() {
    // Set current date
    elements.currentDate.textContent = new Date().toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    // Setup event listeners
    setupNavigation();
    setupNoteInput();
    setupFilters();
    setupButtons();
    setupModal();
    setupMobileMenu();
    setupScanner();
    setupLLMSettings();
    setupWeatherSearch();
    setupLeaderboard();

    // Check LLM status
    checkLLMStatus();

    // Load initial data
    await loadDashboardData();

    // Handle QR code redirect - check URL params
    handleQRCodeRedirect();
}

// ============== QR Code Redirect Handler ==============
function handleQRCodeRedirect() {
    const urlParams = new URLSearchParams(window.location.search);
    const plantId = urlParams.get('plant');
    const action = urlParams.get('action');
    const error = urlParams.get('error');

    // Show error if plant not found
    if (error === 'plant_not_found') {
        showToast('Plant not found - QR code may be invalid', 'error');
        // Clear the URL params
        window.history.replaceState({}, document.title, window.location.pathname);
        return;
    }

    // If we have a plant ID from QR scan, navigate to it
    if (plantId) {
        // Navigate to plants page
        navigateTo('plants');

        // Wait for plants to load, then show the plant
        setTimeout(() => {
            // plantId is already a string (UUID)
            if (action === 'view') {
                viewPlant(plantId);
            } else if (action === 'water') {
                logWatering(plantId);
            } else if (action === 'growth') {
                logGrowth(plantId);
            } else {
                // Default: show quick action modal
                showPlantQuickActions(plantId);
            }
            // Clear the URL params
            window.history.replaceState({}, document.title, window.location.pathname);
        }, 500);
    }
}

// Show quick actions modal for scanned plant
function showPlantQuickActions(plantId) {
    const plant = plants.find(p => p.id === plantId);
    if (!plant) {
        showToast('Plant not found', 'error');
        return;
    }

    const displayName = plant.display_name || plant.name;

    showModal(`🌱 ${displayName}`, `
        <div class="quick-actions-container">
            <p class="quick-actions-intro">What would you like to do with this plant?</p>
            <div class="quick-actions-grid">
                <button class="quick-action-btn" onclick="closeModal(); viewPlant('${plantId}')">
                    <span class="quick-action-icon">👁️</span>
                    <span>View Details</span>
                </button>
                <button class="quick-action-btn" onclick="closeModal(); logWatering('${plantId}')">
                    <span class="quick-action-icon">💧</span>
                    <span>Log Watering</span>
                </button>
                <button class="quick-action-btn" onclick="closeModal(); logGrowth('${plantId}')">
                    <span class="quick-action-icon">📏</span>
                    <span>Log Growth</span>
                </button>
                <button class="quick-action-btn" onclick="closeModal(); showLabel('${plantId}')">
                    <span class="quick-action-icon">🏷️</span>
                    <span>View Label</span>
                </button>
            </div>
            <div class="plant-quick-info">
                <p><strong>Code:</strong> ${plant.unique_code || 'N/A'}</p>
                <p><strong>Location:</strong> ${plant.location || 'Not set'}</p>
                <p><strong>Status:</strong> <span class="plant-status ${plant.status}">${plant.status}</span></p>
            </div>
        </div>
    `);
}

// ============== Navigation ==============
function setupNavigation() {
    elements.navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.dataset.page;
            navigateTo(page);
        });
    });
}

function navigateTo(page) {
    // Update nav
    elements.navItems.forEach(item => {
        item.classList.toggle('active', item.dataset.page === page);
    });

    // Update pages
    elements.pages.forEach(p => {
        p.classList.toggle('active', p.id === `${page}Page`);
    });

    // Update title
    const titles = {
        dashboard: 'Dashboard',
        plants: 'My Plants',
        tasks: 'Tasks & Reminders',
        recipes: 'Compost Tea Recipes',
        budget: 'Budget & Nutrients',
        harvests: 'Harvest Log',
        notes: 'Garden Notes',
        weather: 'Weather Log',
        scanner: 'Plant Scanner',
        leaderboard: 'Leaderboard'
    };
    elements.pageTitle.textContent = titles[page] || page;

    // Load page data
    loadPageData(page);
}

async function loadPageData(page) {
    switch (page) {
        case 'dashboard':
            await loadDashboardData();
            break;
        case 'plants':
            await loadPlants();
            break;
        case 'tasks':
            await loadTasks();
            break;
        case 'recipes':
            await loadRecipes();
            break;
        case 'budget':
            await loadBudget();
            break;
        case 'harvests':
            await loadHarvests();
            break;
        case 'notes':
            await loadNotes();
            break;
        case 'weather':
            await loadWeather();
            break;
        case 'scanner':
            initScannerPage();
            break;
        case 'leaderboard':
            await loadLeaderboard();
            break;
    }
}

// ============== LLM Integration ==============
async function checkLLMStatus() {
    try {
        const response = await fetch(`${API_BASE}/llm/status`);
        const data = await response.json();

        elements.llmStatusDot.className = 'status-dot ' + (data.connected ? 'connected' : 'disconnected');
        elements.llmStatusText.textContent = data.connected ? 'AI Connected' : 'AI Offline';
    } catch (error) {
        elements.llmStatusDot.className = 'status-dot disconnected';
        elements.llmStatusText.textContent = 'AI Offline';
    }
}

// ============== LLM Settings ==============

// Helper function to refresh the models dropdown
async function refreshModelsDropdown() {
    if (!elements.llmModelSelect) return;

    const currentSelection = elements.llmModelSelect.value;

    try {
        const modelsResp = await fetch(`${API_BASE}/llm/models`);
        const modelsData = await modelsResp.json();
        const models = modelsData.models || [];

        elements.llmModelSelect.innerHTML = '<option value="">-- Select a model --</option>' +
            models.map(m => `<option value="${m}">${m}</option>`).join('');

        // Restore previous selection if still valid
        if (currentSelection && models.includes(currentSelection)) {
            elements.llmModelSelect.value = currentSelection;
        }
    } catch (err) {
        console.debug('Failed to refresh LLM models:', err);
    }
}

function setupLLMSettings() {
    // Open settings modal
    elements.llmSettingsBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        openLLMSettings();
    });

    // Close settings modal
    elements.llmSettingsClose.addEventListener('click', closeLLMSettings);
    elements.llmSettingsOverlay.addEventListener('click', (e) => {
        if (e.target === elements.llmSettingsOverlay) {
            closeLLMSettings();
        }
    });

    // Test connection button
    elements.testConnectionBtn.addEventListener('click', testLLMConnection);

    // Test tool calling button
    elements.testToolsBtn.addEventListener('click', testToolCalling);

    // Save settings button
    elements.saveSettingsBtn.addEventListener('click', saveLLMSettings);

    // Reset settings button
    elements.resetSettingsBtn.addEventListener('click', resetLLMSettings);

    // View logs button
    elements.viewLogsBtn.addEventListener('click', toggleLogs);

    // Refresh models when URL changes (with debounce)
    let urlDebounceTimer = null;
    elements.llmUrlInput?.addEventListener('input', () => {
        clearTimeout(urlDebounceTimer);
        urlDebounceTimer = setTimeout(refreshModelsDropdown, 1000);
    });

    // Sync model select with text input
    elements.llmModelSelect?.addEventListener('change', (e) => {
        if (e.target.value) {
            elements.llmModelInput.value = e.target.value;
        }
    });

    // Update slider value displays
    if (elements.contextLengthInput) {
        elements.contextLengthInput.addEventListener('input', (e) => {
            elements.contextLengthValue.textContent = e.target.value;
        });
    }

    if (elements.gpuLayersInput) {
        elements.gpuLayersInput.addEventListener('input', (e) => {
            elements.gpuLayersValue.textContent = e.target.value;
        });
    }

    if (elements.cpuThreadsInput) {
        elements.cpuThreadsInput.addEventListener('input', (e) => {
            elements.cpuThreadsValue.textContent = e.target.value;
        });
    }
}

async function openLLMSettings() {
    elements.llmSettingsOverlay.classList.add('active');

    // Load current settings
    let currentModel = '';
    try {
        const response = await fetch(`${API_BASE}/llm/settings`);
        const data = await response.json();

        elements.llmUrlInput.value = data.url || '';
        elements.llmModelInput.value = data.model || '';
        currentModel = data.model || '';
        elements.llmUrlInput.placeholder = data.defaults?.url || 'http://localhost:1234/v1/chat/completions';
        elements.llmModelInput.placeholder = data.defaults?.model || 'model-name';

        // Load new settings
        if (elements.contextLengthInput) {
            const contextLength = data.context_length || 8192;
            elements.contextLengthInput.value = contextLength;
            elements.contextLengthValue.textContent = contextLength;
        }

        if (elements.gpuLayersInput) {
            const gpuLayers = data.gpu_layers || 35;
            elements.gpuLayersInput.value = gpuLayers;
            elements.gpuLayersValue.textContent = gpuLayers;
        }

        if (elements.cpuThreadsInput) {
            const cpuThreads = data.cpu_threads || 8;
            elements.cpuThreadsInput.value = cpuThreads;
            elements.cpuThreadsValue.textContent = cpuThreads;
        }
    } catch (error) {
        showToast('Failed to load settings', 'error');
    }

    // Check current status
    await testLLMConnection();
    // Populate model select with available models
    try {
        const modelsResp = await fetch(`${API_BASE}/llm/models`);
        const modelsData = await modelsResp.json();
        const models = modelsData.models || [];
        if (elements.llmModelSelect) {
            elements.llmModelSelect.innerHTML = '<option value="">-- Select a model --</option>' +
                models.map(m => `<option value="${m}">${m}</option>`).join('');
            // If loaded model is present, select it
            if (currentModel) {
                elements.llmModelSelect.value = currentModel;
            }
        }
    } catch (err) {
        // ignore if fetch fails
        console.debug('Failed to load LLM models:', err);
    }
}

function closeLLMSettings() {
    elements.llmSettingsOverlay.classList.remove('active');
    elements.logsContainer.classList.add('hidden');
}

async function testLLMConnection() {
    elements.testConnectionBtn.disabled = true;
    elements.testConnectionBtn.innerHTML = '<span class="loading-spinner" style="width:14px;height:14px;border-width:2px;"></span> Testing...';
    elements.settingsStatusText.textContent = 'Testing connection...';
    elements.settingsStatusDot.className = 'status-dot large';
    elements.statusDetails.innerHTML = '';

    try {
        const response = await fetch(`${API_BASE}/llm/status`);
        const data = await response.json();

        elements.settingsStatusDot.className = 'status-dot large ' + (data.connected ? 'connected' : 'disconnected');
        elements.settingsStatusText.textContent = data.connected ? '✅ Connected' : '❌ Not Connected';

        // Show details
        let details = `<div class="detail-item"><strong>URL:</strong> ${data.url || 'N/A'}</div>`;
        details += `<div class="detail-item"><strong>Model:</strong> ${data.model || 'N/A'}</div>`;

        if (data.connected) {
            details += `<div class="detail-item success"><strong>Status:</strong> ${data.message}</div>`;
            if (data.model_response) {
                details += `<div class="detail-item"><strong>Response:</strong> "${data.model_response}"</div>`;
            }
        } else {
            details += `<div class="detail-item error"><strong>Error:</strong> ${data.message}</div>`;
            if (data.error_details) {
                details += `<div class="detail-item error"><strong>Details:</strong> ${data.error_details.substring(0, 200)}</div>`;
            }
        }

        elements.statusDetails.innerHTML = details;

        // Update sidebar status
        elements.llmStatusDot.className = 'status-dot ' + (data.connected ? 'connected' : 'disconnected');
        elements.llmStatusText.textContent = data.connected ? 'AI Connected' : 'AI Offline';

    } catch (error) {
        elements.settingsStatusDot.className = 'status-dot large disconnected';
        elements.settingsStatusText.textContent = '❌ Connection Failed';
        elements.statusDetails.innerHTML = `<div class="detail-item error"><strong>Error:</strong> ${error.message}</div>`;
    } finally {
        elements.testConnectionBtn.disabled = false;
        elements.testConnectionBtn.innerHTML = '🔌 Test Connection';
    }
}

async function testToolCalling() {
    elements.testToolsBtn.disabled = true;
    elements.testToolsBtn.innerHTML = '<span class="loading-spinner" style="width:14px;height:14px;border-width:2px;"></span> Testing...';

    try {
        const response = await fetch(`${API_BASE}/llm/test-tools`);
        const data = await response.json();

        let details = elements.statusDetails.innerHTML;
        details += '<hr style="margin: 10px 0; border-color: var(--border-color);">';
        details += '<div class="detail-item"><strong>Tool Calling Test:</strong></div>';

        if (data.supports_tools) {
            details += `<div class="detail-item success">✅ ${data.message}</div>`;
        } else {
            details += `<div class="detail-item error">❌ ${data.message}</div>`;
            if (data.hint) {
                details += `<div class="detail-item warning">💡 ${data.hint}</div>`;
            }
            if (data.model_response) {
                details += `<div class="detail-item"><strong>Model said:</strong> "${data.model_response}"</div>`;
            }
        }

        elements.statusDetails.innerHTML = details;

    } catch (error) {
        showToast('Failed to test tool calling', 'error');
    } finally {
        elements.testToolsBtn.disabled = false;
        elements.testToolsBtn.innerHTML = '🔧 Test Tool Calling';
    }
}

async function saveLLMSettings() {
    const url = elements.llmUrlInput.value.trim();
    // Prefer custom text input if present, otherwise use selection
    const selected = elements.llmModelSelect?.value || '';
    const model = (elements.llmModelInput.value.trim() || selected).trim();

    // Get new settings values
    const context_length = parseInt(elements.contextLengthInput?.value || 8192);
    const gpu_layers = parseInt(elements.gpuLayersInput?.value || 35);
    const cpu_threads = parseInt(elements.cpuThreadsInput?.value || 8);

    if (!url) {
        showToast('Please enter an API URL', 'error');
        return;
    }

    elements.saveSettingsBtn.disabled = true;
    elements.saveSettingsBtn.innerHTML = '<span class="loading-spinner" style="width:14px;height:14px;border-width:2px;"></span> Saving...';

    try {
        const response = await fetch(`${API_BASE}/llm/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url,
                model,
                context_length,
                gpu_layers,
                cpu_threads
            })
        });

        const data = await response.json();

        if (data.success) {
            showToast('Settings saved successfully!', 'success');
            // Test connection with new settings
            await testLLMConnection();
            // Refresh models list with new URL
            await refreshModelsDropdown();
        } else {
            showToast(data.message || 'Failed to save settings', 'error');
        }
    } catch (error) {
        showToast('Failed to save settings', 'error');
    } finally {
        elements.saveSettingsBtn.disabled = false;
        elements.saveSettingsBtn.innerHTML = '💾 Save Settings';
    }
}

async function resetLLMSettings() {
    try {
        const response = await fetch(`${API_BASE}/llm/settings`);
        const data = await response.json();

        elements.llmUrlInput.value = data.defaults?.url || 'http://localhost:1234/v1/chat/completions';
        elements.llmModelInput.value = data.defaults?.model || 'ibm-granite/granite-3.3-8b-instruct';

        // Reset new settings
        const defaultContextLength = data.defaults?.context_length || 8192;
        const defaultGpuLayers = data.defaults?.gpu_layers || 35;
        const defaultCpuThreads = data.defaults?.cpu_threads || 8;

        if (elements.contextLengthInput) {
            elements.contextLengthInput.value = defaultContextLength;
            elements.contextLengthValue.textContent = defaultContextLength;
        }

        if (elements.gpuLayersInput) {
            elements.gpuLayersInput.value = defaultGpuLayers;
            elements.gpuLayersValue.textContent = defaultGpuLayers;
        }

        if (elements.cpuThreadsInput) {
            elements.cpuThreadsInput.value = defaultCpuThreads;
            elements.cpuThreadsValue.textContent = defaultCpuThreads;
        }

        showToast('Settings reset to defaults (not saved yet)', 'info');
    } catch (error) {
        showToast('Failed to load default settings', 'error');
    }
}

async function toggleLogs() {
    const container = elements.logsContainer;

    if (container.classList.contains('hidden')) {
        container.classList.remove('hidden');
        elements.viewLogsBtn.innerHTML = '📋 Hide Logs';

        // Load logs
        try {
            const response = await fetch(`${API_BASE}/llm/logs`);
            const data = await response.json();

            if (data.logs && data.logs.length > 0) {
                elements.logsContent.textContent = data.logs.join('');
                // Scroll to bottom
                elements.logsContent.scrollTop = elements.logsContent.scrollHeight;
            } else {
                elements.logsContent.textContent = 'No logs available yet. Try processing a note to generate logs.';
            }
        } catch (error) {
            elements.logsContent.textContent = 'Failed to load logs: ' + error.message;
        }
    } else {
        container.classList.add('hidden');
        elements.viewLogsBtn.innerHTML = '📋 View Recent Logs';
    }
}

function setupNoteInput() {
    elements.processNoteBtn.addEventListener('click', processNote);
    elements.clearNoteBtn.addEventListener('click', () => {
        elements.noteInput.value = '';
        elements.extractedActions.classList.add('hidden');
    });
    elements.quickNoteBtn.addEventListener('click', () => {
        navigateTo('dashboard');
        elements.noteInput.focus();
    });
}

async function processNote() {
    const note = elements.noteInput.value.trim();
    if (!note) {
        showToast('Please enter a note first', 'error');
        return;
    }

    elements.processNoteBtn.disabled = true;
    elements.processNoteBtn.innerHTML = '<span class="loading-spinner" style="width:16px;height:16px;border-width:2px;"></span> Processing...';

    try {
        const response = await fetch(`${API_BASE}/llm/process-note`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ note })
        });

        const data = await response.json();

        if (data.success && data.extracted_actions && data.extracted_actions.length > 0) {
            displayExtractedActions(data.extracted_actions);
        } else if (data.error) {
            // Show more detailed error with hint if available
            let errorMsg = data.error;
            if (data.hint) {
                errorMsg += ` (${data.hint})`;
            }
            showToast(errorMsg, 'error');
            console.error('LLM Error:', data);
            elements.extractedActions.classList.add('hidden');
        } else {
            showToast('No actions could be extracted from the note', 'error');
            elements.extractedActions.classList.add('hidden');
        }
    } catch (error) {
        showToast('Failed to process note. Is the server running?', 'error');
    } finally {
        elements.processNoteBtn.disabled = false;
        elements.processNoteBtn.innerHTML = '<span class="btn-icon">✨</span> Process with AI';
    }
}

function displayExtractedActions(actions) {
    const actionIcons = {
        add_plant: '🌱',
        log_watering: '💧',
        log_fertilization: '🧪',
        log_harvest: '🥕',
        log_growth: '📏',
        report_pest_issue: '🐛',
        create_task: '✅',
        log_weather: '🌤️',
        update_plant_status: '📝'
    };

    const actionNames = {
        add_plant: 'Add Plant',
        log_watering: 'Log Watering',
        log_fertilization: 'Log Fertilization',
        log_harvest: 'Log Harvest',
        log_growth: 'Log Growth',
        report_pest_issue: 'Report Pest Issue',
        create_task: 'Create Task',
        log_weather: 'Log Weather',
        update_plant_status: 'Update Plant Status'
    };

    let html = `<h4>✨ Extracted Actions (${actions.length})</h4>`;

    actions.forEach((action, index) => {
        const icon = actionIcons[action.action] || '📋';
        const name = actionNames[action.action] || action.action;
        const params = Object.entries(action.parameters || {})
            .map(([k, v]) => `<strong>${k}:</strong> ${v}`)
            .join(', ');

        html += `
            <div class="action-item" data-index="${index}">
                <div class="action-icon">${icon}</div>
                <div class="action-details">
                    <div class="action-type">${name}</div>
                    <div class="action-params">${params || 'No parameters'}</div>
                </div>
            </div>
        `;
    });

    html += `
        <div class="action-buttons">
            <button class="btn btn-secondary" onclick="cancelActions()">Cancel</button>
            <button class="btn btn-primary" onclick="applyActions(${JSON.stringify(actions).replace(/"/g, '&quot;')})">
                Apply All Actions
            </button>
        </div>
    `;

    elements.extractedActions.innerHTML = html;
    elements.extractedActions.classList.remove('hidden');
}

function cancelActions() {
    elements.extractedActions.classList.add('hidden');
}

async function applyActions(actions) {
    try {
        const response = await fetch(`${API_BASE}/llm/apply-actions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ actions })
        });

        const data = await response.json();

        const successCount = data.results.filter(r => r.success).length;
        showToast(`Successfully applied ${successCount} of ${actions.length} actions`, 'success');

        // Clear and reload
        elements.noteInput.value = '';
        elements.extractedActions.classList.add('hidden');
        await loadDashboardData();

    } catch (error) {
        showToast('Failed to apply actions', 'error');
    }
}

// ============== Dashboard ==============
async function loadDashboardData() {
    try {
        // Load stats
        const statsResponse = await fetch(`${API_BASE}/dashboard/stats`);
        const stats = await statsResponse.json();

        elements.statPlants.textContent = stats.active_plants;
        elements.statTasks.textContent = stats.pending_tasks;
        elements.statHarvests.textContent = stats.recent_harvests;
        elements.statPests.textContent = stats.active_pests;

        // Load upcoming tasks
        const tasksResponse = await fetch(`${API_BASE}/tasks`);
        tasks = await tasksResponse.json();
        renderUpcomingTasks(tasks.slice(0, 5));

        // Load plants for health chart and filter dropdowns
        const plantsResponse = await fetch(`${API_BASE}/plants`);
        plants = await plantsResponse.json();
        renderHealthChart();

        // Populate chart filter dropdowns
        populateChartFilters();

        // Load growth and watering charts
        await loadGrowthChart();
        await loadWateringChart();

    } catch (error) {
        console.error('Failed to load dashboard data:', error);
    }
}

function populateChartFilters() {
    const activePlants = plants.filter(p => p.status === 'active');

    // Growth chart filter
    const growthFilter = elements.growthPlantFilter;
    if (growthFilter) {
        growthFilter.innerHTML = '<option value="">Select a plant...</option>' +
            activePlants.map(p => `<option value="${p.id}">${p.display_name || p.name}</option>`).join('');
        // Select first plant if available
        if (activePlants.length > 0) {
            growthFilter.value = activePlants[0].id;
        }
    }

    // Watering chart filter
    const wateringFilter = elements.wateringPlantFilter;
    if (wateringFilter) {
        wateringFilter.innerHTML = '<option value="">All Plants</option>' +
            activePlants.map(p => `<option value="${p.id}">${p.display_name || p.name}</option>`).join('');
    }
}

function renderUpcomingTasks(taskList) {
    if (!taskList.length) {
        elements.upcomingTasks.innerHTML = `
            <div class="empty-state">
                <p>No pending tasks</p>
            </div>
        `;
        return;
    }

    elements.upcomingTasks.innerHTML = taskList.map(task => {
        const dueDate = task.due_date ? new Date(task.due_date) : null;
        const isOverdue = dueDate && dueDate < new Date();

        return `
            <div class="task-item">
                <div class="task-checkbox" onclick="completeTask('${task.id}')"></div>
                <div class="task-content">
                    <div class="task-title">${task.title}</div>
                    <div class="task-due ${isOverdue ? 'overdue' : ''}">
                        ${dueDate ? formatDate(dueDate) : 'No due date'}
                    </div>
                </div>
                <span class="task-priority ${task.priority}">${task.priority}</span>
            </div>
        `;
    }).join('');
}

function renderHealthChart() {
    const ctx = document.getElementById('healthChart')?.getContext('2d');
    if (!ctx) return;

    // Get plants with recent growth logs
    const plantData = plants
        .filter(p => p.status === 'active' && p.growth_logs?.length > 0)
        .slice(0, 8)
        .map(p => {
            const latestLog = p.growth_logs[p.growth_logs.length - 1];
            return {
                name: p.name,
                health: latestLog?.health_rating || 5
            };
        });

    if (healthChart) {
        healthChart.destroy();
    }

    if (!plantData.length) {
        ctx.canvas.parentElement.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📊</div>
                <h3>No Health Data Yet</h3>
                <p>Add plants and log their health to see the chart</p>
            </div>
        `;
        return;
    }

    healthChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: plantData.map(p => p.name),
            datasets: [{
                label: 'Health Rating',
                data: plantData.map(p => p.health),
                backgroundColor: plantData.map(p =>
                    p.health >= 7 ? 'rgba(34, 197, 94, 0.5)' :
                        p.health >= 4 ? 'rgba(245, 158, 11, 0.5)' :
                            'rgba(239, 68, 68, 0.5)'
                ),
                borderColor: plantData.map(p =>
                    p.health >= 7 ? '#22c55e' :
                        p.health >= 4 ? '#f59e0b' :
                            '#ef4444'
                ),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 10,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

// ============== Plants ==============
function setupFilters() {
    elements.plantStatusFilter?.addEventListener('change', () => loadPlants());
    elements.taskFilter?.addEventListener('change', () => loadTasks());

    // Plants view toggle - query fresh to ensure buttons are found
    const viewBtns = document.querySelectorAll('.view-btn');
    console.debug('[setupFilters] found view buttons:', viewBtns.length);
    // Initialize button active state based on viewVisibility
    viewBtns.forEach(btn => {
        const v = btn.dataset.view;
        btn.classList.toggle('active', !!viewVisibility[v]);
    });
    // Attach per-button listeners
    viewBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation(); // prevent delegated handler from also firing
            const view = btn.dataset.view;
            // button clicked; toggling handled by switchPlantsView
            if (view) switchPlantsView(view);
        });
    });
    // Fallback: delegated listener on the container to handle cases where the
    // individual listeners aren't attached or DOM nodes are recreated.
    const viewToggleContainer = document.querySelector('.view-toggle');
    if (viewToggleContainer) {
        viewToggleContainer.addEventListener('click', (e) => {
            const btn = (e.target instanceof Element) ? e.target.closest('.view-btn') : null;
            if (btn) {
                e.preventDefault();
                const view = btn.dataset.view;
                if (view) switchPlantsView(view);
            }
        });
    }

    // Plants search
    elements.plantSearchInput?.addEventListener('input', (e) => {
        plantSearchQuery = e.target.value.toLowerCase();
        filterAndRenderPlants();
    });

    // Table sorting
    document.querySelectorAll('.data-table th[data-sort]')?.forEach(th => {
        th.addEventListener('click', () => sortPlantsTable(th.dataset.sort));
        th.style.cursor = 'pointer';
    });
}

function switchPlantsView(view) {
    // Toggle visibility for the requested view
    viewVisibility[view] = !viewVisibility[view];
    currentPlantsView = view; // keep last used view for compatibility
    console.debug('[switchPlantsView] switching to view:', view);

    // Update button states - query fresh
    const viewBtns = document.querySelectorAll('.view-btn');
    viewBtns.forEach(btn => {
        const v = btn.dataset.view;
        btn.classList.toggle('active', !!viewVisibility[v]);
    });

    // Show/hide containers
    elements.plantsList?.classList.toggle('hidden', !viewVisibility.grid);
    elements.plantsTable?.classList.toggle('hidden', !viewVisibility.table);
    elements.plantsCharts?.classList.toggle('hidden', !viewVisibility.charts);
    console.debug('[switchPlantsView] containers hidden state:', {
        listHidden: elements.plantsList?.classList.contains('hidden'),
        tableHidden: elements.plantsTable?.classList.contains('hidden'),
        chartsHidden: elements.plantsCharts?.classList.contains('hidden'),
    });

    // Re-render for current view
    // Re-render for all visible views
    filterAndRenderPlants();

    // Initialize charts if needed
    if (view === 'charts') {
        if (viewVisibility.charts) {
            renderPlantsCharts();
        }
    }
}
// Ensure global reference is available for inline onclick and other global invocations
if (typeof window !== 'undefined') window.switchPlantsView = switchPlantsView;

function filterAndRenderPlants() {
    const filter = elements.plantStatusFilter?.value || 'active';
    let filteredPlants = plants;

    // Filter by status
    if (filter !== 'all') {
        filteredPlants = filteredPlants.filter(p => p.status === filter);
    }

    // Filter by search query
    if (plantSearchQuery) {
        filteredPlants = filteredPlants.filter(p =>
            (p.name || '').toLowerCase().includes(plantSearchQuery) ||
            (p.variety || '').toLowerCase().includes(plantSearchQuery) ||
            (p.location || '').toLowerCase().includes(plantSearchQuery) ||
            (p.unique_code || '').toLowerCase().includes(plantSearchQuery)
        );
    }

    // Render based on viewVisibility so multiple views can be stacked
    if (viewVisibility.grid) {
        renderPlants(filteredPlants);
    } else {
        // If grid hidden, clear contents to avoid stale data left in DOM
        if (elements.plantsList) elements.plantsList.innerHTML = '';
    }
    if (viewVisibility.table) {
        renderPlantsTable(filteredPlants);
    } else {
        if (elements.plantsTableBody) elements.plantsTableBody.innerHTML = '';
    }
    if (viewVisibility.charts) {
        renderPlantsCharts();
    }
}

function sortPlantsTable(column) {
    if (plantSortColumn === column) {
        plantSortDirection = plantSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        plantSortColumn = column;
        plantSortDirection = 'asc';
    }
    filterAndRenderPlants();
}

async function loadPlants() {
    try {
        const response = await fetch(`${API_BASE}/plants`);
        plants = await response.json();

        filterAndRenderPlants();
    } catch (error) {
        console.error('Failed to load plants:', error);
    }
}

function renderPlants(plantList) {
    if (!plantList.length) {
        elements.plantsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🌱</div>
                <h3>No Plants Yet</h3>
                <p>Add your first plant or use the AI note feature!</p>
            </div>
        `;
        return;
    }

    const plantEmojis = ['🌱', '🌿', '🌻', '🌷', '🌹', '🍅', '🥕', '🌶️', '🥬', '🍃'];

    elements.plantsList.innerHTML = plantList.map((plant, index) => {
        const emoji = plantEmojis[index % plantEmojis.length];
        const plantedDate = plant.date_planted ? formatDate(new Date(plant.date_planted)) : 'Unknown';
        const displayName = plant.display_name || plant.name;

        return `
            <div class="plant-card">
                <div class="plant-image">${emoji}</div>
                <div class="plant-info">
                    <div class="plant-name">${displayName}</div>
                    <div class="plant-variety">${plant.variety || 'No variety specified'}</div>
                    <div class="plant-code">${plant.unique_code || ''}</div>
                    <div class="plant-meta">
                        <span class="plant-meta-item">📍 ${plant.location || 'Unknown'}</span>
                        <span class="plant-meta-item">📅 ${plantedDate}</span>
                    </div>
                    <span class="plant-status ${plant.status}">${plant.status}</span>
                    <div class="plant-actions">
                        <button class="btn btn-small btn-secondary" onclick="viewPlant('${plant.id}')">View</button>
                        <button class="btn btn-small btn-secondary" onclick="showLabel('${plant.id}')">🏷️ Label</button>
                        <button class="btn btn-small btn-secondary" onclick="logGrowth('${plant.id}')">📏 Growth</button>
                        <button class="btn btn-small btn-secondary" onclick="logWatering('${plant.id}')">💧 Water</button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function renderPlantsTable(plantList) {
    if (!elements.plantsTableBody) return;

    // Sort the data
    const sortedPlants = [...plantList].sort((a, b) => {
        let aVal, bVal;

        switch (plantSortColumn) {
            case 'name':
                aVal = (a.display_name || a.name || '').toLowerCase();
                bVal = (b.display_name || b.name || '').toLowerCase();
                break;
            case 'variety':
                aVal = (a.variety || '').toLowerCase();
                bVal = (b.variety || '').toLowerCase();
                break;
            case 'location':
                aVal = (a.location || '').toLowerCase();
                bVal = (b.location || '').toLowerCase();
                break;
            case 'status':
                aVal = a.status || '';
                bVal = b.status || '';
                break;
            case 'date_planted':
                aVal = a.date_planted ? new Date(a.date_planted).getTime() : 0;
                bVal = b.date_planted ? new Date(b.date_planted).getTime() : 0;
                break;
            case 'height':
                aVal = getLatestGrowthValue(a, 'height_cm');
                bVal = getLatestGrowthValue(b, 'height_cm');
                break;
            case 'health':
                aVal = getLatestGrowthValue(a, 'health_rating');
                bVal = getLatestGrowthValue(b, 'health_rating');
                break;
            case 'waterings':
                aVal = (a.waterings || []).length;
                bVal = (b.waterings || []).length;
                break;
            default:
                aVal = '';
                bVal = '';
        }

        if (aVal < bVal) return plantSortDirection === 'asc' ? -1 : 1;
        if (aVal > bVal) return plantSortDirection === 'asc' ? 1 : -1;
        return 0;
    });

    if (!sortedPlants.length) {
        elements.plantsTableBody.innerHTML = `
            <tr>
                <td colspan="9" class="empty-table-cell">
                    <div class="empty-state">
                        <div class="empty-state-icon">🌱</div>
                        <h3>No Plants Found</h3>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    elements.plantsTableBody.innerHTML = sortedPlants.map(plant => {
        const displayName = plant.display_name || plant.name;
        const plantedDate = plant.date_planted ? formatDate(new Date(plant.date_planted)) : '-';
        const latestHeight = getLatestGrowthValue(plant, 'height_cm');
        const latestHealth = getLatestGrowthValue(plant, 'health_rating');
        const wateringCount = (plant.waterings || []).length;

        return `
            <tr>
                <td><strong>${displayName}</strong></td>
                <td>${plant.variety || '-'}</td>
                <td>${plant.location || '-'}</td>
                <td><span class="plant-status ${plant.status}">${plant.status}</span></td>
                <td>${plantedDate}</td>
                <td>${latestHeight ? latestHeight + ' cm' : '-'}</td>
                <td>${latestHealth ? getHealthBadge(latestHealth) : '-'}</td>
                <td>${wateringCount}</td>
                <td>
                    <div class="table-actions">
                        <button class="btn btn-small btn-secondary" onclick="viewPlant('${plant.id}')" title="View Details">👁️</button>
                        <button class="btn btn-small btn-secondary" onclick="logGrowth('${plant.id}')" title="Log Growth">📏</button>
                        <button class="btn btn-small btn-secondary" onclick="logWatering('${plant.id}')" title="Log Watering">💧</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function getLatestGrowthValue(plant, field) {
    const logs = plant.growth_logs || [];
    if (!logs.length) return null;

    // Sort by date descending and get latest
    const sorted = [...logs].sort((a, b) => new Date(b.date) - new Date(a.date));
    return sorted[0][field];
}

function getHealthBadge(rating) {
    let color = 'var(--success)';
    if (rating < 4) color = 'var(--danger)';
    else if (rating < 7) color = 'var(--warning)';

    return `<span class="health-badge" style="background: ${color}">${rating}/10</span>`;
}

function renderPlantsCharts() {
    const filter = elements.plantStatusFilter?.value || 'active';
    let chartPlants = plants;

    if (filter !== 'all') {
        chartPlants = plants.filter(p => p.status === filter);
    }

    // Apply search filter to charts too
    if (plantSearchQuery) {
        chartPlants = chartPlants.filter(p =>
            (p.name || '').toLowerCase().includes(plantSearchQuery) ||
            (p.variety || '').toLowerCase().includes(plantSearchQuery) ||
            (p.location || '').toLowerCase().includes(plantSearchQuery)
        );
    }

    renderHealthDistributionChart(chartPlants);
    renderGrowthComparisonChart(chartPlants);
    renderWateringFrequencyChart(chartPlants);
    renderLocationDistributionChart(chartPlants);
}

function renderHealthDistributionChart(plantList) {
    const ctx = document.getElementById('healthDistributionChart');
    if (!ctx) return;

    // Destroy existing chart
    if (healthDistributionChart) {
        healthDistributionChart.destroy();
    }

    // Count plants by health rating groups
    const healthGroups = { 'Excellent (8-10)': 0, 'Good (5-7)': 0, 'Poor (1-4)': 0, 'No Data': 0 };

    plantList.forEach(plant => {
        const health = getLatestGrowthValue(plant, 'health_rating');
        if (!health) healthGroups['No Data']++;
        else if (health >= 8) healthGroups['Excellent (8-10)']++;
        else if (health >= 5) healthGroups['Good (5-7)']++;
        else healthGroups['Poor (1-4)']++;
    });

    healthDistributionChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(healthGroups),
            datasets: [{
                data: Object.values(healthGroups),
                backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#6b7280']
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    onClick: (e, legendItem, legend) => {
                        const index = legendItem.index;
                        const chart = legend.chart;
                        const meta = chart.getDatasetMeta(0);

                        // Toggle the hidden state
                        if (meta.data[index]) {
                            meta.data[index].hidden = !meta.data[index].hidden;
                        }
                        chart.update();
                    }
                }
            }
        }
    });
}

function renderGrowthComparisonChart(plantList) {
    const ctx = document.getElementById('growthComparisonChart');
    if (!ctx) return;

    if (growthComparisonChart) {
        growthComparisonChart.destroy();
    }

    // Get plants with growth data
    const plantsWithGrowth = plantList
        .filter(p => (p.growth_logs || []).length > 0)
        .slice(0, 10); // Top 10 for readability

    if (!plantsWithGrowth.length) {
        growthComparisonChart = new Chart(ctx, {
            type: 'bar',
            data: { labels: ['No Data'], datasets: [{ data: [0] }] },
            options: { responsive: true }
        });
        return;
    }

    const labels = plantsWithGrowth.map(p => p.display_name || p.name);
    const heights = plantsWithGrowth.map(p => getLatestGrowthValue(p, 'height_cm') || 0);
    const bgColors = plantsWithGrowth.map(() => '#3b82f6');

    // Track hidden bars
    const hiddenBars = new Array(plantsWithGrowth.length).fill(false);

    growthComparisonChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Height (cm)',
                data: heights,
                backgroundColor: bgColors
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'Height (cm)' } }
            },
            onClick: (e, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const chart = growthComparisonChart;
                    const meta = chart.getDatasetMeta(0);

                    // Toggle visibility
                    hiddenBars[index] = !hiddenBars[index];
                    meta.data[index].hidden = hiddenBars[index];

                    // Update bar appearance (make transparent when hidden)
                    chart.data.datasets[0].backgroundColor = bgColors.map((color, i) =>
                        hiddenBars[i] ? 'rgba(59, 130, 246, 0.2)' : color
                    );

                    chart.update();
                }
            }
        }
    });
}

function renderWateringFrequencyChart(plantList) {
    const ctx = document.getElementById('wateringFrequencyChart');
    if (!ctx) return;

    if (wateringFrequencyChart) {
        wateringFrequencyChart.destroy();
    }

    // Get watering counts by plant
    const plantsWithWatering = plantList
        .filter(p => (p.waterings || []).length > 0)
        .slice(0, 10);

    if (!plantsWithWatering.length) {
        wateringFrequencyChart = new Chart(ctx, {
            type: 'bar',
            data: { labels: ['No Data'], datasets: [{ data: [0] }] },
            options: { responsive: true }
        });
        return;
    }

    const labels = plantsWithWatering.map(p => p.display_name || p.name);
    const counts = plantsWithWatering.map(p => (p.waterings || []).length);
    const bgColors = plantsWithWatering.map(() => '#06b6d4');

    // Track hidden bars
    const hiddenBars = new Array(plantsWithWatering.length).fill(false);

    wateringFrequencyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Watering Events',
                data: counts,
                backgroundColor: bgColors
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'Count' } }
            },
            onClick: (e, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const chart = wateringFrequencyChart;
                    const meta = chart.getDatasetMeta(0);

                    // Toggle visibility
                    hiddenBars[index] = !hiddenBars[index];
                    meta.data[index].hidden = hiddenBars[index];

                    // Update bar appearance (make transparent when hidden)
                    chart.data.datasets[0].backgroundColor = bgColors.map((color, i) =>
                        hiddenBars[i] ? 'rgba(6, 182, 212, 0.2)' : color
                    );

                    chart.update();
                }
            }
        }
    });
}

function renderLocationDistributionChart(plantList) {
    const ctx = document.getElementById('locationDistributionChart');
    if (!ctx) return;

    if (locationDistributionChart) {
        locationDistributionChart.destroy();
    }

    // Count plants by location
    const locationCounts = {};
    plantList.forEach(plant => {
        const loc = plant.location || 'Unknown';
        locationCounts[loc] = (locationCounts[loc] || 0) + 1;
    });

    locationDistributionChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: Object.keys(locationCounts),
            datasets: [{
                data: Object.values(locationCounts),
                backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    onClick: (e, legendItem, legend) => {
                        const index = legendItem.index;
                        const chart = legend.chart;
                        const meta = chart.getDatasetMeta(0);

                        // Toggle the hidden state
                        if (meta.data[index]) {
                            meta.data[index].hidden = !meta.data[index].hidden;
                        }
                        chart.update();
                    }
                }
            }
        }
    });
}

// ============== Tasks ==============
async function loadTasks() {
    try {
        const filter = elements.taskFilter?.value || 'pending';
        const url = filter === 'completed' ? `${API_BASE}/tasks?completed=true` : `${API_BASE}/tasks`;

        const response = await fetch(url);
        tasks = await response.json();

        let filteredTasks = tasks;
        if (filter === 'completed') {
            filteredTasks = tasks.filter(t => t.completed);
        } else if (filter === 'pending') {
            filteredTasks = tasks.filter(t => !t.completed);
        }

        renderTasks(filteredTasks);
    } catch (error) {
        console.error('Failed to load tasks:', error);
    }
}

function renderTasks(taskList) {
    if (!taskList.length) {
        elements.tasksList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">✅</div>
                <h3>No Tasks</h3>
                <p>Create a task or use the AI to extract tasks from notes!</p>
            </div>
        `;
        return;
    }

    elements.tasksList.innerHTML = taskList.map(task => {
        const dueDate = task.due_date ? new Date(task.due_date) : null;
        const isOverdue = dueDate && dueDate < new Date() && !task.completed;

        return `
            <div class="task-item">
                <div class="task-checkbox ${task.completed ? 'checked' : ''}" 
                     onclick="completeTask('${task.id}')"
                     ${task.completed ? 'style="pointer-events:none"' : ''}></div>
                <div class="task-content">
                    <div class="task-title" style="${task.completed ? 'text-decoration: line-through; opacity: 0.6' : ''}">
                        ${task.title}
                    </div>
                    <div class="task-due ${isOverdue ? 'overdue' : ''}">
                        ${dueDate ? formatDate(dueDate) : 'No due date'}
                        ${task.recurring ? '🔄 Recurring' : ''}
                    </div>
                </div>
                <span class="task-priority ${task.priority}">${task.priority}</span>
                <button class="btn btn-small btn-danger" onclick="deleteTask('${task.id}')">🗑️</button>
            </div>
        `;
    }).join('');
}

async function completeTask(taskId) {
    try {
        await fetch(`${API_BASE}/tasks/${taskId}/complete`, { method: 'PUT' });
        showToast('Task completed!', 'success');
        await loadTasks();
        await loadDashboardData();
    } catch (error) {
        showToast('Failed to complete task', 'error');
    }
}

async function deleteTask(taskId) {
    if (!confirm('Delete this task?')) return;

    try {
        await fetch(`${API_BASE}/tasks/${taskId}`, { method: 'DELETE' });
        showToast('Task deleted', 'success');
        await loadTasks();
    } catch (error) {
        showToast('Failed to delete task', 'error');
    }
}

// ============== Harvests ==============
async function loadHarvests() {
    try {
        const response = await fetch(`${API_BASE}/harvests`);
        harvests = await response.json();
        renderHarvests(harvests);
    } catch (error) {
        console.error('Failed to load harvests:', error);
    }
}

function renderHarvests(harvestList) {
    if (!harvestList.length) {
        elements.harvestsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🥕</div>
                <h3>No Harvests Yet</h3>
                <p>Log your harvests through the AI note feature!</p>
            </div>
        `;
        return;
    }

    elements.harvestsList.innerHTML = harvestList.map(harvest => `
        <div class="harvest-item">
            <div class="harvest-icon">🥕</div>
            <div class="harvest-info">
                <div class="harvest-plant">${harvest.plant_name || 'Unknown Plant'}</div>
                <div class="harvest-date">${formatDate(new Date(harvest.date))}</div>
            </div>
            <div class="harvest-quantity">
                <div class="harvest-amount">${harvest.quantity || '?'}</div>
                <div class="harvest-unit">${harvest.unit || 'units'}</div>
            </div>
        </div>
    `).join('');
}

// ============== Notes ==============
async function loadNotes() {
    try {
        const response = await fetch(`${API_BASE}/notes`);
        notes = await response.json();
        renderNotes(notes);
    } catch (error) {
        console.error('Failed to load notes:', error);
    }
}

function renderNotes(noteList) {
    if (!noteList.length) {
        elements.notesList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📝</div>
                <h3>No Notes Yet</h3>
                <p>Use the Quick Note feature to add your first note!</p>
            </div>
        `;
        return;
    }

    elements.notesList.innerHTML = noteList.map(note => {
        const actions = note.extracted_data || [];

        return `
            <div class="note-item">
                <div class="note-header">
                    <span class="note-date">${formatDate(new Date(note.created_at))}</span>
                    <div class="note-header-right">
                        <span class="note-badge ${note.processed ? 'processed' : 'pending'}">
                            ${note.processed ? '✓ Processed' : 'Pending'}
                        </span>
                        <button class="btn btn-icon btn-danger-outline" onclick="deleteNote('${note.id}')" title="Delete Note">
                            🗑️
                        </button>
                    </div>
                </div>
                <div class="note-text">${note.raw_text}</div>
                ${actions.length ? `
                    <div class="note-actions-list">
                        ${actions.map(a => `
                            <span class="note-action-tag">${a.action}</span>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

async function deleteNote(noteId) {
    if (!confirm('Are you sure you want to delete this note? This cannot be undone.')) return;

    try {
        await fetch(`${API_BASE}/notes/${noteId}`, { method: 'DELETE' });
        showToast('Note deleted', 'success');
        await loadNotes();
    } catch (error) {
        console.error('Failed to delete note:', error);
        showToast('Failed to delete note', 'error');
    }
}

// ============== Weather ==============
async function loadWeather() {
    try {
        const response = await fetch(`${API_BASE}/weather`);
        weather = await response.json();
        renderWeather(weather);
    } catch (error) {
        console.error('Failed to load weather:', error);
    }
}

function setupWeatherSearch() {
    elements.fetchWeatherBtn?.addEventListener('click', fetchWeatherByLocation);
    elements.weatherSearchInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') fetchWeatherByLocation();
    });
    elements.weatherUnitToggle?.addEventListener('click', toggleWeatherUnit);
}

function toggleWeatherUnit() {
    weatherUnit = weatherUnit === 'C' ? 'F' : 'C';
    if (elements.weatherUnitToggle) {
        elements.weatherUnitToggle.textContent = `°${weatherUnit}`;
    }

    // Re-render if we have data
    if (lastWeatherSearchResult) {
        renderWeatherSearchResult(lastWeatherSearchResult);
    }

    // Refresh weather list
    renderWeather(weather);
}

async function fetchWeatherByLocation() {
    const query = elements.weatherSearchInput?.value.trim();
    if (!query) {
        showToast('Please enter a zipcode or city name', 'error');
        return;
    }

    elements.fetchWeatherBtn.disabled = true;
    elements.fetchWeatherBtn.innerHTML = '<span class="loading-spinner" style="width:14px;height:14px;border-width:2px;"></span> Searching...';
    elements.weatherSearchResult.classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE}/weather/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        lastWeatherSearchResult = data;
        renderWeatherSearchResult(data);

    } catch (error) {
        elements.weatherSearchResult.innerHTML = `
            <div class="weather-error">
                <p>❌ Failed to fetch weather: ${error.message}</p>
            </div>
        `;
        elements.weatherSearchResult.classList.remove('hidden');
    } finally {
        elements.fetchWeatherBtn.disabled = false;
        elements.fetchWeatherBtn.innerHTML = '<span>🔍</span> Get Weather';
    }
}

function renderWeatherSearchResult(data) {
    if (data.error) {
        if (data.hint) {
            // API key not configured - show setup prompt
            elements.weatherSearchResult.innerHTML = `
                <div class="weather-error">
                    <p>⚠️ ${data.error}</p>
                    <p class="hint">${data.hint}</p>
                    <button class="btn btn-secondary btn-sm" onclick="showWeatherApiSetup()">Configure API Key</button>
                </div>
            `;
        } else {
            elements.weatherSearchResult.innerHTML = `
                <div class="weather-error">
                    <p>❌ ${data.error}</p>
                </div>
            `;
        }
        elements.weatherSearchResult.classList.remove('hidden');
        return;
    }

    const isC = weatherUnit === 'C';
    const temp = Math.round(isC ? data.temperature : (data.temperature_F !== undefined ? data.temperature_F : (data.temperature * 9 / 5 + 32)));
    const high = Math.round(isC ? data.temperature_high : (data.temperature_high_F !== undefined ? data.temperature_high_F : (data.temperature_high * 9 / 5 + 32)));
    const low = Math.round(isC ? data.temperature_low : (data.temperature_low_F !== undefined ? data.temperature_low_F : (data.temperature_low * 9 / 5 + 32)));
    const unitLabel = isC ? '°C' : '°F';
    const degree = '°';

    const iconUrl = data.icon ? `https://openweathermap.org/img/wn/${data.icon}@2x.png` : '';
    elements.weatherSearchResult.innerHTML = `
        <div class="weather-result-card">
            <div class="weather-result-header">
                ${iconUrl ? `<img src="${iconUrl}" alt="Weather icon" class="weather-icon-img">` : ''}
                <div>
                    <h4>${data.location}${data.country ? `, ${data.country}` : ''}</h4>
                    <p class="weather-condition">${data.conditions}</p>
                </div>
            </div>
            <div class="weather-result-details">
                <div class="weather-stat">
                    <span class="stat-value">${temp}${unitLabel}</span>
                    <span class="stat-label">Current</span>
                </div>
                <div class="weather-stat">
                    <span class="stat-value">${high}${degree}</span>
                    <span class="stat-label">High</span>
                </div>
                <div class="weather-stat">
                    <span class="stat-value">${low}${degree}</span>
                    <span class="stat-label">Low</span>
                </div>
                <div class="weather-stat">
                    <span class="stat-value">${data.humidity}%</span>
                    <span class="stat-label">Humidity</span>
                </div>
                <div class="weather-stat">
                    <span class="stat-value">${data.wind_speed} m/s</span>
                    <span class="stat-label">Wind</span>
                </div>
            </div>
            <div class="weather-result-actions">
                <button class="btn btn-primary btn-sm" onclick="saveWeatherToLog(${JSON.stringify(data).replace(/"/g, '&quot;')})">
                    💾 Save to Weather Log
                </button>
            </div>
        </div>
    `;
    elements.weatherSearchResult.classList.remove('hidden');
}

async function saveWeatherToLog(weatherData) {
    try {
        const data = {
            temperature_high: weatherData.temperature_high,
            temperature_low: weatherData.temperature_low,
            humidity: weatherData.humidity,
            conditions: weatherData.conditions,
            notes: `Location: ${weatherData.location}${weatherData.country ? ', ' + weatherData.country : ''}`
        };

        await fetch(`${API_BASE}/weather`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        showToast('Weather saved to log!', 'success');
        await loadWeather();
    } catch (error) {
        showToast('Failed to save weather', 'error');
    }
}

function showWeatherApiSetup() {
    showModal('⚙️ Weather API Setup', `
        <div class="api-setup">
            <p>To use the weather lookup feature, you need an OpenWeatherMap API key.</p>
            <ol class="setup-steps">
                <li>Go to <a href="https://openweathermap.org/api" target="_blank">openweathermap.org/api</a></li>
                <li>Sign up for a free account</li>
                <li>Get your API key from the dashboard</li>
                <li>Paste it below</li>
            </ol>
            <div class="form-group">
                <label>API Key</label>
                <input type="text" id="weatherApiKeyInput" placeholder="Enter your OpenWeatherMap API key">
            </div>
            <div class="form-actions">
                <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="saveWeatherApiKey()">Save API Key</button>
            </div>
        </div>
    `);
}

async function saveWeatherApiKey() {
    const apiKey = document.getElementById('weatherApiKeyInput')?.value.trim();
    if (!apiKey) {
        showToast('Please enter an API key', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/weather/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey })
        });

        const data = await response.json();
        if (data.success) {
            showToast('API key saved!', 'success');
            closeModal();
        } else {
            showToast(data.error || 'Failed to save', 'error');
        }
    } catch (error) {
        showToast('Failed to save API key', 'error');
    }
}

function renderWeather(weatherList) {
    if (!weatherList.length) {
        elements.weatherList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🌤️</div>
                <h3>No Weather Logs</h3>
                <p>Log weather conditions manually or through AI notes!</p>
            </div>
        `;
        return;
    }

    const weatherIcons = {
        sunny: '☀️',
        cloudy: '☁️',
        rainy: '🌧️',
        stormy: '⛈️',
        snowy: '❄️',
        windy: '💨',
        foggy: '🌫️'
    };

    const isC = weatherUnit === 'C';
    const degree = '°';
    const unitLabel = isC ? 'C' : 'F';

    elements.weatherList.innerHTML = weatherList.map(w => {
        const icon = weatherIcons[w.conditions?.toLowerCase()] || '🌤️';

        // Convert stored logs (assumed C) if needed
        let high = w.temperature_high;
        let low = w.temperature_low;

        if (high !== undefined && high !== null && !isC) {
            high = Math.round(high * 9 / 5 + 32);
        }
        if (low !== undefined && low !== null && !isC) {
            low = Math.round(low * 9 / 5 + 32);
        }

        return `
            <div class="weather-item">
                <div class="weather-icon">${icon}</div>
                <div class="weather-info">
                    <div class="weather-date">${formatDate(new Date(w.date))}</div>
                    <div class="weather-conditions">${w.conditions || 'Unknown conditions'}</div>
                </div>
                <div class="weather-temps">
                    <div class="weather-temp high">
                        <div class="weather-temp-value">${high !== undefined && high !== null ? high + degree : '--'}</div>
                        <div class="weather-temp-label">High</div>
                    </div>
                    <div class="weather-temp low">
                        <div class="weather-temp-value">${low !== undefined && low !== null ? low + degree : '--'}</div>
                        <div class="weather-temp-label">Low</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// ============== Leaderboard ==============
function setupLeaderboard() {
    // Metric selector
    elements.leaderboardMetric?.addEventListener('change', loadLeaderboard);

    // Category selector
    elements.leaderboardCategory?.addEventListener('change', loadLeaderboard);

    // Select plants button
    elements.selectPlantsBtn?.addEventListener('click', showPlantSelectorModal);
}

async function loadLeaderboard() {
    const metric = elements.leaderboardMetric?.value || 'growth_rate';
    const category = elements.leaderboardCategory?.value || 'all';

    // Get selected plant IDs (if any)
    const plantIds = selectedLeaderboardPlants.size > 0
        ? Array.from(selectedLeaderboardPlants).join(',')
        : '';

    try {
        // Also fetch plants to populate categories
        const plantsResponse = await fetch(`${API_BASE}/plants`);
        if (plantsResponse.ok) {
            const plants = await plantsResponse.json();
            populateLeaderboardCategories(plants);
        }

        let url = `${API_BASE}/leaderboard?metric=${metric}`;
        if (category !== 'all') url += `&category=${encodeURIComponent(category)}`;
        if (plantIds) url += `&plant_ids=${plantIds}`;

        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to load leaderboard');

        const data = await response.json();
        renderLeaderboard(data, metric);
        renderLeaderboardChart(data, metric);

        // Update selected plants count
        if (elements.selectedPlantsCount) {
            elements.selectedPlantsCount.textContent = selectedLeaderboardPlants.size > 0
                ? `(${selectedLeaderboardPlants.size} selected)`
                : '(All plants)';
        }
    } catch (error) {
        console.error('Error loading leaderboard:', error);
        if (elements.leaderboardRankings) {
            elements.leaderboardRankings.innerHTML = '<div class="error-message">Failed to load leaderboard data</div>';
        }
    }
}

function populateLeaderboardCategories(plants) {
    if (!elements.leaderboardCategory) return;

    const currentValue = elements.leaderboardCategory.value;
    const categories = [...new Set(plants.map(p => p.category).filter(Boolean))];

    // Only rebuild if categories changed
    if (elements.leaderboardCategory.options.length !== categories.length + 1) {
        elements.leaderboardCategory.innerHTML = '<option value="all">All Plants</option>' +
            categories.map(cat => `<option value="${cat}">${cat}</option>`).join('');

        // Restore selection if still valid
        if (categories.includes(currentValue)) {
            elements.leaderboardCategory.value = currentValue;
        }
    }
}

function renderLeaderboard(data, metric) {
    if (!elements.leaderboardRankings) return;

    const rankings = data.rankings || [];

    if (rankings.length === 0) {
        elements.leaderboardRankings.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">🏆</span>
                <p>No ranking data available</p>
                <p class="empty-hint">Add growth logs or harvest records to see rankings</p>
            </div>
        `;
        return;
    }

    const metricLabels = {
        growth_rate: 'Growth Rate',
        health: 'Health Score',
        harvests: 'Total Harvests'
    };

    const metricUnits = {
        growth_rate: 'cm/day',
        health: '/10',
        harvests: 'harvests'
    };

    elements.leaderboardRankings.innerHTML = rankings.map((item, index) => {
        const rank = index + 1;
        const medal = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '';
        const rankClass = rank <= 3 ? `rank-${rank}` : '';

        // Get value based on the metric - backend returns metric as property name
        const rawValue = item[metric] || 0;
        let displayValue = rawValue;
        if (metric === 'growth_rate') {
            displayValue = rawValue.toFixed(2);
        } else if (metric === 'health') {
            displayValue = rawValue.toFixed(1);
        }

        // Use display_name if available, otherwise fall back to name
        const plantName = item.display_name || item.name;

        return `
            <div class="ranking-item ${rankClass}">
                <div class="ranking-position">
                    ${medal ? `<span class="medal">${medal}</span>` : `<span class="rank-number">${rank}</span>`}
                </div>
                <div class="ranking-info">
                    <div class="ranking-name">${plantName}</div>
                    <div class="ranking-category">${item.category || 'Uncategorized'}</div>
                </div>
                <div class="ranking-value">
                    <span class="value">${displayValue}</span>
                    <span class="unit">${metricUnits[metric]}</span>
                </div>
            </div>
        `;
    }).join('');

    // Update chart title
    if (elements.leaderboardChartTitle) {
        elements.leaderboardChartTitle.textContent = `${metricLabels[metric]} Rankings`;
    }
}

function renderLeaderboardChart(data, metric) {
    const canvas = document.getElementById('leaderboardChart');
    if (!canvas) return;

    const rankings = data.rankings || [];
    if (rankings.length === 0) {
        if (leaderboardChart) {
            leaderboardChart.destroy();
            leaderboardChart = null;
        }
        return;
    }

    // Take top 10 for the chart
    const topRankings = rankings.slice(0, 10);

    const metricColors = {
        growth_rate: { bg: 'rgba(76, 175, 80, 0.6)', border: 'rgba(76, 175, 80, 1)' },
        health: { bg: 'rgba(33, 150, 243, 0.6)', border: 'rgba(33, 150, 243, 1)' },
        harvests: { bg: 'rgba(255, 152, 0, 0.6)', border: 'rgba(255, 152, 0, 1)' }
    };

    const colors = metricColors[metric] || metricColors.growth_rate;

    const chartData = {
        labels: topRankings.map(r => {
            const name = r.display_name || r.name;
            return name.length > 15 ? name.substring(0, 15) + '...' : name;
        }),
        datasets: [{
            label: metric.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
            data: topRankings.map(r => r[metric] || 0),
            backgroundColor: colors.bg,
            borderColor: colors.border,
            borderWidth: 1
        }]
    };

    if (leaderboardChart) {
        leaderboardChart.destroy();
    }

    leaderboardChart = new Chart(canvas, {
        type: 'bar',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true
                }
            }
        }
    });
}

async function showPlantSelectorModal() {
    // Load all plants
    try {
        const response = await fetch(`${API_BASE}/plants`);
        if (!response.ok) throw new Error('Failed to load plants');

        const plants = await response.json();

        const modalContent = `
            <h2>Select Plants for Comparison</h2>
            <div class="plant-selector-list">
                ${plants.map(plant => `
                    <label class="plant-selector-item">
                        <input type="checkbox" value="${plant.id}" 
                            ${selectedLeaderboardPlants.has(plant.id) ? 'checked' : ''}>
                        <span class="plant-selector-name">${plant.name}</span>
                        <span class="plant-selector-category">${plant.category || 'Uncategorized'}</span>
                    </label>
                `).join('')}
            </div>
            <div class="modal-actions">
                <button type="button" class="btn btn-secondary" onclick="clearPlantSelection()">Clear All</button>
                <button type="button" class="btn btn-secondary" onclick="selectAllPlants()">Select All</button>
                <button type="button" class="btn btn-primary" onclick="applyPlantSelection()">Apply</button>
            </div>
        `;

        openModal(modalContent);
    } catch (error) {
        console.error('Error loading plants for selector:', error);
        alert('Failed to load plants');
    }
}

function clearPlantSelection() {
    const checkboxes = document.querySelectorAll('.plant-selector-item input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = false);
}

function selectAllPlants() {
    const checkboxes = document.querySelectorAll('.plant-selector-item input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = true);
}

function applyPlantSelection() {
    const checkboxes = document.querySelectorAll('.plant-selector-item input[type="checkbox"]');
    selectedLeaderboardPlants.clear();

    checkboxes.forEach(cb => {
        if (cb.checked) {
            selectedLeaderboardPlants.add(cb.value);
        }
    });

    closeModal();
    loadLeaderboard();
}

// ============== Buttons ==============
function setupButtons() {
    elements.addPlantBtn?.addEventListener('click', showAddPlantModal);
    elements.addTaskBtn?.addEventListener('click', showAddTaskModal);
    elements.addWeatherBtn?.addEventListener('click', showAddWeatherModal);
    elements.addRecipeBtn?.addEventListener('click', showAddRecipeModal);
    elements.addProductBtn?.addEventListener('click', showAddProductModal);

    // Chart filter listeners
    elements.growthPlantFilter?.addEventListener('change', loadGrowthChart);
    elements.wateringPlantFilter?.addEventListener('change', loadWateringChart);
}

// ============== Modal ==============
function setupModal() {
    elements.modalClose.addEventListener('click', closeModal);
    elements.modalOverlay.addEventListener('click', (e) => {
        if (e.target === elements.modalOverlay) closeModal();
    });
}

function showModal(title, content) {
    elements.modalTitle.textContent = title;
    elements.modalBody.innerHTML = content;
    elements.modalOverlay.classList.add('active');
}

function closeModal() {
    elements.modalOverlay.classList.remove('active');
    // Destroy any plant detail charts to free memory and prevent resize issues
    if (plantGrowthChart) { try { plantGrowthChart.destroy(); } catch (e) { } plantGrowthChart = null; }
    if (plantWateringChart) { try { plantWateringChart.destroy(); } catch (e) { } plantWateringChart = null; }
}

function showAddPlantModal() {
    showModal('Add New Plant', `
        <form id="addPlantForm">
            <div class="form-row">
                <div class="form-group" style="flex: 2;">
                    <label>Plant Name *</label>
                    <input type="text" name="name" required placeholder="e.g., Tomato">
                </div>
                <div class="form-group" style="flex: 1;">
                    <label>Quantity</label>
                    <input type="number" name="quantity" min="1" max="50" value="1" placeholder="1">
                    <small style="color: var(--text-muted); font-size: 11px;">Creates #1, #2, etc.</small>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Variety</label>
                    <input type="text" name="variety" placeholder="e.g., Cherry">
                </div>
                <div class="form-group">
                    <label>Location</label>
                    <input type="text" name="location" placeholder="e.g., Raised Bed 1">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Date Planted</label>
                    <input type="date" name="date_planted">
                </div>
                <div class="form-group">
                    <label>Expected Harvest</label>
                    <input type="date" name="expected_harvest">
                </div>
            </div>
            <div class="form-group">
                <label>Notes</label>
                <textarea name="notes" rows="3" placeholder="Any additional notes..."></textarea>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Add Plant(s)</button>
            </div>
        </form>
    `);

    document.getElementById('addPlantForm').addEventListener('submit', handleAddPlant);
}

async function handleAddPlant(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Convert quantity to integer
    if (data.quantity) {
        data.quantity = parseInt(data.quantity) || 1;
    }

    try {
        const response = await fetch(`${API_BASE}/plants`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();

        if (data.quantity > 1) {
            showToast(`${result.plants?.length || data.quantity} plants added!`, 'success');
        } else {
            showToast('Plant added successfully!', 'success');
        }
        closeModal();
        await loadPlants();
        await loadDashboardData();
    } catch (error) {
        showToast('Failed to add plant', 'error');
    }
}

function showAddTaskModal() {
    showModal('Add New Task', `
        <form id="addTaskForm">
            <div class="form-group">
                <label>Task Title *</label>
                <input type="text" name="title" required placeholder="e.g., Water tomatoes">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Task Type</label>
                    <select name="task_type">
                        <option value="watering">Watering</option>
                        <option value="fertilizing">Fertilizing</option>
                        <option value="pruning">Pruning</option>
                        <option value="harvesting">Harvesting</option>
                        <option value="planting">Planting</option>
                        <option value="pest_control">Pest Control</option>
                        <option value="maintenance">Maintenance</option>
                        <option value="other">Other</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Priority</label>
                    <select name="priority">
                        <option value="low">Low</option>
                        <option value="medium" selected>Medium</option>
                        <option value="high">High</option>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Due Date</label>
                    <input type="date" name="due_date">
                </div>
                <div class="form-group">
                    <label>Recurring?</label>
                    <select name="recurring">
                        <option value="false">No</option>
                        <option value="true">Yes</option>
                    </select>
                </div>
            </div>
            <div class="form-group">
                <label>Description</label>
                <textarea name="description" rows="3" placeholder="Task details..."></textarea>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Add Task</button>
            </div>
        </form>
    `);

    document.getElementById('addTaskForm').addEventListener('submit', handleAddTask);
}

async function handleAddTask(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    data.recurring = data.recurring === 'true';

    try {
        await fetch(`${API_BASE}/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        showToast('Task created!', 'success');
        closeModal();
        await loadTasks();
        await loadDashboardData();
    } catch (error) {
        showToast('Failed to create task', 'error');
    }
}

function showAddWeatherModal() {
    const today = new Date().toISOString().split('T')[0];

    showModal('Log Weather', `
        <form id="addWeatherForm">
            <div class="form-group">
                <label>Date</label>
                <input type="date" name="date" value="${today}">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>High Temperature (°C)</label>
                    <input type="number" name="temperature_high" placeholder="e.g., 25">
                </div>
                <div class="form-group">
                    <label>Low Temperature (°C)</label>
                    <input type="number" name="temperature_low" placeholder="e.g., 15">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Conditions</label>
                    <select name="conditions">
                        <option value="sunny">☀️ Sunny</option>
                        <option value="cloudy">☁️ Cloudy</option>
                        <option value="rainy">🌧️ Rainy</option>
                        <option value="stormy">⛈️ Stormy</option>
                        <option value="windy">💨 Windy</option>
                        <option value="foggy">🌫️ Foggy</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Rainfall (mm)</label>
                    <input type="number" name="rainfall_mm" placeholder="e.g., 5">
                </div>
            </div>
            <div class="form-group">
                <label>Humidity (%)</label>
                <input type="number" name="humidity" min="0" max="100" placeholder="e.g., 65">
            </div>
            <div class="form-group">
                <label>Notes</label>
                <textarea name="notes" rows="2" placeholder="Any weather observations..."></textarea>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Log Weather</button>
            </div>
        </form>
    `);

    document.getElementById('addWeatherForm').addEventListener('submit', handleAddWeather);
}

async function handleAddWeather(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Convert numeric fields
    if (data.temperature_high) data.temperature_high = parseFloat(data.temperature_high);
    if (data.temperature_low) data.temperature_low = parseFloat(data.temperature_low);
    if (data.rainfall_mm) data.rainfall_mm = parseFloat(data.rainfall_mm);
    if (data.humidity) data.humidity = parseFloat(data.humidity);

    try {
        await fetch(`${API_BASE}/weather`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        showToast('Weather logged!', 'success');
        closeModal();
        await loadWeather();
    } catch (error) {
        showToast('Failed to log weather', 'error');
    }
}

// ============== Plant Actions ==============
async function viewPlant(plantId) {
    const plant = plants.find(p => p.id === plantId);
    if (!plant) return;

    const growthLogs = plant.growth_logs || [];
    const latestGrowth = growthLogs[growthLogs.length - 1];
    const displayName = plant.display_name || plant.name;
    const waterings = plant.waterings || [];
    const fertilizations = plant.fertilizations || [];

    // Generate watering history HTML
    const wateringHistoryHtml = waterings.length > 0 ? `
        <div class="history-section">
            <h4>💧 Recent Watering</h4>
            <div class="history-list">
                ${waterings.slice(-5).reverse().map(w => `
                    <div class="history-item">
                        <div class="history-date">${formatDate(new Date(w.date))}</div>
                        <div class="history-details">
                            ${w.amount_ml ? `<span class="history-tag">${w.amount_ml} ml</span>` : ''}
                            ${w.method ? `<span class="history-tag method">${w.method}</span>` : ''}
                        </div>
                        ${w.notes ? `<div class="history-notes">${w.notes}</div>` : ''}
                    </div>
                `).join('')}
            </div>
        </div>
    ` : '';

    // Generate fertilization history HTML
    const fertilizationHistoryHtml = fertilizations.length > 0 ? `
        <div class="history-section">
            <h4>🧪 Recent Feeding / Fertilization</h4>
            <div class="history-list">
                ${fertilizations.slice(-5).reverse().map(f => `
                    <div class="history-item fertilization">
                        <div class="history-date">${formatDate(new Date(f.date))}</div>
                        <div class="history-details">
                            ${f.fertilizer_type ? `<span class="history-tag fertilizer">${f.fertilizer_type}</span>` : ''}
                            ${f.amount ? `<span class="history-tag">${f.amount}</span>` : ''}
                            ${f.npk_ratio ? `<span class="history-tag npk">NPK: ${f.npk_ratio}</span>` : ''}
                        </div>
                        ${f.notes ? `<div class="history-notes">${f.notes}</div>` : ''}
                    </div>
                `).join('')}
            </div>
        </div>
    ` : '';

    showModal(`🌱 ${displayName}`, `
        <div class="plant-details">
            <div class="form-row">
                <div class="form-group">
                    <label>Variety</label>
                    <p>${plant.variety || 'Not specified'}</p>
                </div>
                <div class="form-group">
                    <label>Location</label>
                    <p>${plant.location || 'Not specified'}</p>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Date Planted</label>
                    <p>${plant.date_planted ? formatDate(new Date(plant.date_planted)) : 'Unknown'}</p>
                </div>
                <div class="form-group">
                    <label>Status</label>
                    <p><span class="plant-status ${plant.status}">${plant.status}</span></p>
                </div>
            </div>
            ${plant.unique_code ? `
                <div class="form-group">
                    <label>Plant Code</label>
                    <p class="plant-code-large">${plant.unique_code}</p>
                </div>
            ` : ''}
            ${latestGrowth ? `
                <div class="form-group">
                    <label>Latest Growth Log (${formatDate(new Date(latestGrowth.date))})</label>
                    <p>Height: ${latestGrowth.height_cm || '?'} cm | Health: ${latestGrowth.health_rating || '?'}/10</p>
                </div>
            ` : ''}
            
            <!-- Plant Charts -->
            <div class="plant-charts">
                <div class="plant-chart-container">
                    <h4>📈 Growth History</h4>
                    <canvas id="plantGrowthChart"></canvas>
                </div>
                <div class="plant-chart-container">
                    <h4>💧 Watering History</h4>
                    <canvas id="plantWateringChart"></canvas>
                </div>
            </div>
            
            <!-- Watering & Feeding History -->
            <div class="care-history">
                ${wateringHistoryHtml}
                ${fertilizationHistoryHtml}
            </div>
            
            <div class="form-group">
                <label>Notes</label>
                <p>${plant.notes || 'No notes'}</p>
            </div>
            <div class="form-actions">
                <button class="btn btn-secondary" onclick="logFertilization('${plant.id}')">🧪 Add Feeding</button>
                <button class="btn btn-primary" onclick="showLabel('${plant.id}')">🏷️ Generate Label</button>
                <button class="btn btn-danger" onclick="deletePlant('${plant.id}')">Delete Plant</button>
                <button class="btn btn-secondary" onclick="closeModal()">Close</button>
            </div>
        </div>
    `);

    // Load and render charts after modal is shown
    await renderPlantDetailCharts(plantId);
}

async function renderPlantDetailCharts(plantId) {
    // Destroy any existing detail charts to avoid duplication
    if (plantGrowthChart) {
        try { plantGrowthChart.destroy(); } catch (e) { }
        plantGrowthChart = null;
    }
    if (plantWateringChart) {
        try { plantWateringChart.destroy(); } catch (e) { }
        plantWateringChart = null;
    }

    // Growth Chart
    const growthCtx = document.getElementById('plantGrowthChart')?.getContext('2d');
    if (growthCtx) {
        try {
            const response = await fetch(`${API_BASE}/charts/growth/${plantId}`);
            const data = await response.json();

            const growthContainer = growthCtx.canvas.parentElement;
            const growthCanvas = growthContainer.querySelector('canvas');
            let existingNoData = growthContainer.querySelector('.no-data-small');

            if (data.dates?.length > 0) {
                // Ensure canvas is visible and no-data message is removed
                if (growthCanvas) growthCanvas.style.display = 'block';
                if (existingNoData) { existingNoData.remove(); existingNoData = null; }
                plantGrowthChart = new Chart(growthCtx, {
                    type: 'line',
                    data: {
                        labels: data.dates.map(d => d.slice(5)), // MM-DD format
                        datasets: [{
                            label: 'Height (cm)',
                            data: data.heights,
                            borderColor: '#22c55e',
                            backgroundColor: 'rgba(34, 197, 94, 0.1)',
                            fill: true,
                            tension: 0.3,
                            pointRadius: 4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                grid: { color: 'rgba(255, 255, 255, 0.1)' },
                                ticks: { color: '#94a3b8', font: { size: 10 } }
                            },
                            x: {
                                grid: { display: false },
                                ticks: { color: '#94a3b8', font: { size: 10 } }
                            }
                        },
                        plugins: {
                            legend: { display: false }
                        }
                    }
                });
                plantGrowthChart.resize();
            } else {
                if (growthCanvas) growthCanvas.style.display = 'none';
                if (!existingNoData) {
                    const nd = document.createElement('p');
                    nd.className = 'no-data-small';
                    nd.textContent = 'No growth data yet';
                    growthContainer.appendChild(nd);
                }
            }
        } catch (error) {
            console.error('Failed to load growth chart:', error);
        }
    }

    // Watering Chart
    const waterCtx = document.getElementById('plantWateringChart')?.getContext('2d');
    if (waterCtx) {
        try {
            const response = await fetch(`${API_BASE}/charts/watering/${plantId}`);
            const data = await response.json();
            const waterContainer = waterCtx.canvas.parentElement;
            const waterCanvas = waterContainer.querySelector('canvas');
            let existingNoData2 = waterContainer.querySelector('.no-data-small');

            if (data.dates?.length > 0) {
                // Ensure canvas is visible and remove any no-data message
                if (waterCanvas) waterCanvas.style.display = 'block';
                if (existingNoData2) { existingNoData2.remove(); existingNoData2 = null; }
                plantWateringChart = new Chart(waterCtx, {
                    type: 'bar',
                    data: {
                        labels: data.dates.map(d => d.slice(5)), // MM-DD format
                        datasets: [{
                            label: 'Water (ml)',
                            data: data.amounts,
                            backgroundColor: 'rgba(59, 130, 246, 0.5)',
                            borderColor: '#3b82f6',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                grid: { color: 'rgba(255, 255, 255, 0.1)' },
                                ticks: { color: '#94a3b8', font: { size: 10 } }
                            },
                            x: {
                                grid: { display: false },
                                ticks: { color: '#94a3b8', font: { size: 10 } }
                            }
                        },
                        plugins: {
                            legend: { display: false }
                        }
                    }
                });
                plantWateringChart.resize();
            } else {
                if (waterCanvas) waterCanvas.style.display = 'none';
                if (!existingNoData2) {
                    const nd2 = document.createElement('p');
                    nd2.className = 'no-data-small';
                    nd2.textContent = 'No watering data yet';
                    waterContainer.appendChild(nd2);
                }
            }
        } catch (error) {
            console.error('Failed to load watering chart:', error);
        }
    }
}

// Show plant label with QR code for printing
async function showLabel(plantId) {
    const plant = plants.find(p => p.id === plantId);
    if (!plant) return;

    const displayName = plant.display_name || plant.name;

    showModal(`🏷️ Label - ${displayName}`, `
        <div class="label-preview-container">
            <p class="label-instructions">Label designed for 12×40mm stickers (300 DPI)</p>
            <div class="label-preview-wrapper">
                <img id="labelPreview" class="label-preview" alt="Plant Label" src="" />
                <div class="label-loading">Loading label...</div>
            </div>
            <div class="label-info">
                <span><strong>Code:</strong> ${plant.unique_code || 'N/A'}</span>
                <span><strong>Plant:</strong> ${displayName}</span>
            </div>
            <div class="form-actions">
                <button class="btn btn-primary" onclick="downloadLabel('${plantId}')">📥 Download PNG</button>
                <button class="btn btn-secondary" onclick="printLabel('${plantId}')">🖨️ Print</button>
                <button class="btn btn-secondary" onclick="closeModal()">Close</button>
            </div>
        </div>
    `);

    // Load the label image
    try {
        const response = await fetch(`${API_BASE}/plants/${plantId}/label`);
        if (response.ok) {
            const blob = await response.blob();
            const imageUrl = URL.createObjectURL(blob);
            const labelImg = document.getElementById('labelPreview');
            labelImg.onload = () => {
                labelImg.style.display = 'block';
                document.querySelector('.label-loading').style.display = 'none';
            };
            labelImg.src = imageUrl;
        } else {
            document.querySelector('.label-loading').textContent = 'Failed to generate label';
        }
    } catch (error) {
        console.error('Error loading label:', error);
        document.querySelector('.label-loading').textContent = 'Error loading label';
    }
}

// Download label as PNG
async function downloadLabel(plantId) {
    const plant = plants.find(p => p.id === plantId);
    const displayName = plant ? (plant.display_name || plant.name) : 'plant';
    const code = plant?.unique_code || plantId;

    try {
        const response = await fetch(`${API_BASE}/plants/${plantId}/label`);
        if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `label_${code}_${displayName.replace(/[^a-z0-9]/gi, '_')}.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            showToast('Label downloaded!', 'success');
        }
    } catch (error) {
        showToast('Failed to download label', 'error');
    }
}

// Print label
function printLabel(plantId) {
    const labelImg = document.getElementById('labelPreview');
    if (!labelImg || !labelImg.src) {
        showToast('Label not loaded yet', 'error');
        return;
    }

    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Print Plant Label</title>
            <style>
                @page {
                    size: 40mm 12mm;
                    margin: 0;
                }
                body {
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }
                img {
                    width: 40mm;
                    height: 12mm;
                    object-fit: contain;
                }
            </style>
        </head>
        <body>
            <img src="${labelImg.src}" onload="window.print(); window.close();" />
        </body>
        </html>
    `);
    printWindow.document.close();
}

function logGrowth(plantId) {
    const plant = plants.find(p => p.id === plantId);
    if (!plant) return;

    showModal(`📏 Log Growth - ${plant.name}`, `
        <form id="logGrowthForm" data-plant-id="${plantId}">
            <div class="form-row">
                <div class="form-group">
                    <label>Height (cm)</label>
                    <input type="number" name="height_cm" step="0.1" placeholder="e.g., 25.5">
                </div>
                <div class="form-group">
                    <label>Width (cm)</label>
                    <input type="number" name="width_cm" step="0.1" placeholder="e.g., 15">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Leaf Count</label>
                    <input type="number" name="leaf_count" placeholder="e.g., 12">
                </div>
                <div class="form-group">
                    <label>Health Rating (1-10)</label>
                    <input type="number" name="health_rating" min="1" max="10" placeholder="e.g., 8">
                </div>
            </div>
            <div class="form-group">
                <label>Notes</label>
                <textarea name="notes" rows="2" placeholder="Any observations..."></textarea>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Log Growth</button>
            </div>
        </form>
    `);

    document.getElementById('logGrowthForm').addEventListener('submit', handleLogGrowth);
}

async function handleLogGrowth(e) {
    e.preventDefault();
    const form = e.target;
    const plantId = form.dataset.plantId;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Convert numeric fields
    if (data.height_cm) data.height_cm = parseFloat(data.height_cm);
    if (data.width_cm) data.width_cm = parseFloat(data.width_cm);
    if (data.leaf_count) data.leaf_count = parseInt(data.leaf_count);
    if (data.health_rating) data.health_rating = parseInt(data.health_rating);

    try {
        await fetch(`${API_BASE}/plants/${plantId}/growth`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        showToast('Growth logged!', 'success');
        closeModal();
        await loadPlants();
        await loadDashboardData();
    } catch (error) {
        showToast('Failed to log growth', 'error');
    }
}

function logWatering(plantId) {
    const plant = plants.find(p => p.id === plantId);
    if (!plant) return;

    // Get available recipes for the dropdown
    const recipeOptions = recipes.length > 0
        ? recipes.map(r => `<option value="${r.name}">${r.name}</option>`).join('')
        : '';

    showModal(`💧 Log Watering - ${plant.name}`, `
        <form id="logWateringForm" data-plant-id="${plantId}">
            <div class="form-row">
                <div class="form-group">
                    <label>Amount (ml)</label>
                    <input type="number" name="amount_ml" placeholder="e.g., 500">
                </div>
                <div class="form-group">
                    <label>Method</label>
                    <select name="method" id="wateringMethod">
                        <option value="watering can">Watering Can</option>
                        <option value="hose">Hose</option>
                        <option value="compost tea">Compost Tea</option>
                        <option value="spray">Spray</option>
                        <option value="soak">Deep Soak</option>
                        <option value="fertilizer">Fertilizer Solution</option>
                    </select>
                </div>
            </div>
            <div class="form-group recipe-select ${recipeOptions ? '' : 'hidden'}" id="recipeSelectGroup">
                <label>Recipe Used (optional)</label>
                <select name="recipe" id="recipeSelect">
                    <option value="">No recipe / Plain water</option>
                    ${recipeOptions}
                </select>
                <small class="form-hint">Select if you used a compost tea or fertilizer recipe</small>
            </div>
            <div class="form-group">
                <label>Notes</label>
                <textarea name="notes" rows="2" placeholder="Any notes about this watering..."></textarea>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Log Watering</button>
            </div>
        </form>
    `);

    // Show recipe dropdown when compost tea or fertilizer is selected
    const methodSelect = document.getElementById('wateringMethod');
    const recipeGroup = document.getElementById('recipeSelectGroup');

    if (methodSelect && recipeGroup) {
        methodSelect.addEventListener('change', () => {
            const showRecipe = ['compost tea', 'fertilizer'].includes(methodSelect.value);
            recipeGroup.classList.toggle('hidden', !showRecipe);
        });
    }

    document.getElementById('logWateringForm').addEventListener('submit', handleLogWatering);
}

async function handleLogWatering(e) {
    e.preventDefault();
    const form = e.target;
    const plantId = form.dataset.plantId;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    if (data.amount_ml) data.amount_ml = parseFloat(data.amount_ml);

    // Include recipe in notes if selected
    if (data.recipe && data.recipe !== '') {
        data.notes = data.notes
            ? `${data.notes} | Recipe: ${data.recipe}`
            : `Recipe: ${data.recipe}`;
    }
    delete data.recipe;

    try {
        await fetch(`${API_BASE}/plants/${plantId}/watering`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        showToast('Watering logged!', 'success');
        closeModal();
        await loadPlants();
    } catch (error) {
        showToast('Failed to log watering', 'error');
    }
}

function logFertilization(plantId) {
    const plant = plants.find(p => p.id === plantId);
    if (!plant) return;

    // Get available recipes for the dropdown
    const recipeOptions = recipes.length > 0
        ? recipes.map(r => `<option value="${r.name}">${r.name}</option>`).join('')
        : '';

    showModal(`🧪 Log Fertilization - ${plant.name}`, `
        <form id="logFertilizationForm" data-plant-id="${plantId}">
            <div class="form-group">
                <label>Fertilizer Type *</label>
                <select name="fertilizer_type" id="fertilizerType" required>
                    <option value="">Select type...</option>
                    <option value="compost tea">Compost Tea</option>
                    <option value="liquid fertilizer">Liquid Fertilizer</option>
                    <option value="granular">Granular Fertilizer</option>
                    <option value="fish emulsion">Fish Emulsion</option>
                    <option value="seaweed extract">Seaweed Extract</option>
                    <option value="worm castings">Worm Castings</option>
                    <option value="bone meal">Bone Meal</option>
                    <option value="blood meal">Blood Meal</option>
                    <option value="other">Other</option>
                </select>
            </div>
            ${recipeOptions ? `
            <div class="form-group">
                <label>Recipe Used (optional)</label>
                <select name="recipe" id="fertRecipeSelect">
                    <option value="">Custom / No specific recipe</option>
                    ${recipeOptions}
                </select>
            </div>
            ` : ''}
            <div class="form-row">
                <div class="form-group">
                    <label>Amount</label>
                    <input type="text" name="amount" placeholder="e.g., 1 cup, 500ml">
                </div>
                <div class="form-group">
                    <label>NPK Ratio</label>
                    <input type="text" name="npk_ratio" placeholder="e.g., 10-10-10">
                </div>
            </div>
            <div class="form-group">
                <label>Notes</label>
                <textarea name="notes" rows="2" placeholder="Any notes about this feeding..."></textarea>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Log Fertilization</button>
            </div>
        </form>
    `);

    document.getElementById('logFertilizationForm').addEventListener('submit', handleLogFertilization);
}

async function handleLogFertilization(e) {
    e.preventDefault();
    const form = e.target;
    const plantId = form.dataset.plantId;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Include recipe in notes if selected
    if (data.recipe && data.recipe !== '') {
        data.notes = data.notes
            ? `${data.notes} | Recipe: ${data.recipe}`
            : `Recipe: ${data.recipe}`;
    }
    delete data.recipe;

    try {
        await fetch(`${API_BASE}/plants/${plantId}/fertilization`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        showToast('Fertilization logged!', 'success');
        closeModal();
        await loadPlants();
    } catch (error) {
        showToast('Failed to log fertilization', 'error');
    }
}

async function deletePlant(plantId) {
    if (!confirm('Are you sure you want to delete this plant? This cannot be undone.')) return;

    try {
        await fetch(`${API_BASE}/plants/${plantId}`, { method: 'DELETE' });
        showToast('Plant deleted', 'success');
        closeModal();
        await loadPlants();
        await loadDashboardData();
    } catch (error) {
        showToast('Failed to delete plant', 'error');
    }
}

// ============== Charts ==============
async function loadGrowthChart() {
    const ctx = document.getElementById('growthChart')?.getContext('2d');
    if (!ctx) return;

    const plantId = elements.growthPlantFilter?.value;
    if (!plantId) {
        if (growthChart) growthChart.destroy();
        ctx.canvas.parentElement.querySelector('canvas').style.display = 'block';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/charts/growth/${plantId}`);
        const data = await response.json();

        if (growthChart) growthChart.destroy();

        if (!data.dates?.length) {
            ctx.canvas.style.display = 'none';
            const placeholder = document.createElement('div');
            placeholder.className = 'empty-state';
            placeholder.innerHTML = '<p>No growth data for this plant</p>';
            ctx.canvas.parentElement.appendChild(placeholder);
            return;
        }

        ctx.canvas.style.display = 'block';

        growthChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [{
                    label: 'Height (cm)',
                    data: data.heights,
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34, 197, 94, 0.1)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: '#94a3b8' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8' }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    } catch (error) {
        console.error('Failed to load growth chart:', error);
    }
}

async function loadWateringChart() {
    const ctx = document.getElementById('wateringChart')?.getContext('2d');
    if (!ctx) return;

    const plantId = elements.wateringPlantFilter?.value || '';

    try {
        const url = plantId ? `${API_BASE}/charts/watering/${plantId}` : `${API_BASE}/charts/watering`;
        const response = await fetch(url);
        const data = await response.json();

        if (wateringChart) wateringChart.destroy();

        if (!data.dates?.length) {
            ctx.canvas.style.display = 'none';
            return;
        }

        ctx.canvas.style.display = 'block';

        wateringChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.dates,
                datasets: [{
                    label: 'Water (ml)',
                    data: data.amounts,
                    backgroundColor: 'rgba(59, 130, 246, 0.5)',
                    borderColor: '#3b82f6',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: '#94a3b8' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8' }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    } catch (error) {
        console.error('Failed to load watering chart:', error);
    }
}

// ============== Recipes ==============
async function loadRecipes() {
    try {
        const response = await fetch(`${API_BASE}/recipes`);
        recipes = await response.json();
        renderRecipes();
    } catch (error) {
        console.error('Failed to load recipes:', error);
        elements.recipesList.innerHTML = '<p class="error">Failed to load recipes</p>';
    }
}

function renderRecipes() {
    if (!elements.recipesList) return;

    if (!recipes.length) {
        elements.recipesList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🧪</div>
                <h3>No Recipes Yet</h3>
                <p>Create your first compost tea recipe!</p>
            </div>
        `;
        return;
    }

    elements.recipesList.innerHTML = recipes.map(recipe => `
        <div class="recipe-card">
            <div class="recipe-header">
                <span class="recipe-name">${recipe.name}</span>
                <span class="recipe-type ${recipe.type.replace(' ', '-')}">${recipe.type}</span>
            </div>
            ${recipe.description ? `<p class="recipe-description">${recipe.description}</p>` : ''}
            <div class="recipe-ingredients">
                <h4>Ingredients</h4>
                <div class="ingredient-list">
                    ${recipe.ingredients.map(ing => `
                        <div class="ingredient-item">
                            <span class="ingredient-name">${ing.product_name || ing.name}</span>
                            <span class="ingredient-amount">${ing.amount} ${ing.unit}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="recipe-cost">
                <span class="cost-label">Estimated Cost</span>
                <span class="cost-value">$${(recipe.total_cost || 0).toFixed(2)}</span>
            </div>
            <div class="recipe-actions">
                <button class="btn btn-secondary btn-sm" onclick="editRecipe('${recipe.id}')">Edit</button>
                <button class="btn btn-danger btn-sm" onclick="deleteRecipe('${recipe.id}')">Delete</button>
            </div>
        </div>
    `).join('');
}

function showAddRecipeModal() {
    showModal('Add New Recipe', `
        <form id="addRecipeForm">
            <div class="form-group">
                <label>Recipe Name *</label>
                <input type="text" name="name" required placeholder="e.g., Compost Tea Mix #1">
            </div>
            <div class="form-group">
                <label>Type</label>
                <select name="type">
                    <option value="compost-tea">Compost Tea</option>
                    <option value="fertilizer">Fertilizer</option>
                    <option value="pesticide">Pesticide</option>
                    <option value="other">Other</option>
                </select>
            </div>
            <div class="form-group">
                <label>Description</label>
                <textarea name="description" rows="2" placeholder="Notes about this recipe..."></textarea>
            </div>
            <div class="ingredients-builder">
                <h4>Ingredients</h4>
                <div id="ingredientsList"></div>
                <button type="button" class="btn-add-ingredient" onclick="addIngredientRow()">+ Add Ingredient</button>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Save Recipe</button>
            </div>
        </form>
    `);

    // Add one initial ingredient row
    addIngredientRow();

    document.getElementById('addRecipeForm').addEventListener('submit', handleAddRecipe);
}

function addIngredientRow() {
    const container = document.getElementById('ingredientsList');
    const row = document.createElement('div');
    row.className = 'ingredient-row';
    row.innerHTML = `
        <input type="text" name="ingredient_name[]" placeholder="Product/Ingredient" required>
        <input type="number" name="ingredient_amount[]" step="0.1" min="0" placeholder="Amount" required>
        <select name="ingredient_unit[]">
            <option value="tbsp">tbsp</option>
            <option value="tsp">tsp</option>
            <option value="cups">cups</option>
            <option value="ml">ml</option>
            <option value="g">g</option>
            <option value="oz">oz</option>
            <option value="lb">lb</option>
        </select>
        <button type="button" class="btn-remove-ingredient" onclick="this.parentElement.remove()">×</button>
    `;
    container.appendChild(row);
}

async function handleAddRecipe(e) {
    e.preventDefault();
    const form = e.target;

    const ingredients = [];
    const names = form.querySelectorAll('[name="ingredient_name[]"]');
    const amounts = form.querySelectorAll('[name="ingredient_amount[]"]');
    const units = form.querySelectorAll('[name="ingredient_unit[]"]');

    for (let i = 0; i < names.length; i++) {
        if (names[i].value && amounts[i].value) {
            ingredients.push({
                name: names[i].value,
                amount: parseFloat(amounts[i].value),
                unit: units[i].value
            });
        }
    }

    const data = {
        name: form.name.value,
        type: form.type.value,
        description: form.description.value,
        ingredients: ingredients
    };

    try {
        const response = await fetch(`${API_BASE}/recipes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            showToast('Recipe saved!', 'success');
            closeModal();
            await loadRecipes();
        } else {
            const err = await response.json();
            showToast(err.error || 'Failed to save recipe', 'error');
        }
    } catch (error) {
        showToast('Failed to save recipe', 'error');
    }
}

async function editRecipe(recipeId) {
    const recipe = recipes.find(r => r.id === recipeId);
    if (!recipe) return;

    showModal('Edit Recipe', `
        <form id="editRecipeForm" data-recipe-id="${recipeId}">
            <div class="form-group">
                <label>Recipe Name *</label>
                <input type="text" name="name" required value="${recipe.name}">
            </div>
            <div class="form-group">
                <label>Type</label>
                <select name="type">
                    <option value="compost-tea" ${recipe.type === 'compost-tea' ? 'selected' : ''}>Compost Tea</option>
                    <option value="fertilizer" ${recipe.type === 'fertilizer' ? 'selected' : ''}>Fertilizer</option>
                    <option value="pesticide" ${recipe.type === 'pesticide' ? 'selected' : ''}>Pesticide</option>
                    <option value="other" ${recipe.type === 'other' ? 'selected' : ''}>Other</option>
                </select>
            </div>
            <div class="form-group">
                <label>Description</label>
                <textarea name="description" rows="2">${recipe.description || ''}</textarea>
            </div>
            <div class="ingredients-builder">
                <h4>Ingredients</h4>
                <div id="ingredientsList"></div>
                <button type="button" class="btn-add-ingredient" onclick="addIngredientRow()">+ Add Ingredient</button>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Save Recipe</button>
            </div>
        </form>
    `);

    // Populate existing ingredients
    recipe.ingredients.forEach(ing => {
        const container = document.getElementById('ingredientsList');
        const row = document.createElement('div');
        row.className = 'ingredient-row';
        row.innerHTML = `
            <input type="text" name="ingredient_name[]" placeholder="Product/Ingredient" value="${ing.product_name || ing.name}" required>
            <input type="number" name="ingredient_amount[]" step="0.1" min="0" value="${ing.amount}" required>
            <select name="ingredient_unit[]">
                <option value="tbsp" ${ing.unit === 'tbsp' ? 'selected' : ''}>tbsp</option>
                <option value="tsp" ${ing.unit === 'tsp' ? 'selected' : ''}>tsp</option>
                <option value="cups" ${ing.unit === 'cups' ? 'selected' : ''}>cups</option>
                <option value="ml" ${ing.unit === 'ml' ? 'selected' : ''}>ml</option>
                <option value="g" ${ing.unit === 'g' ? 'selected' : ''}>g</option>
                <option value="oz" ${ing.unit === 'oz' ? 'selected' : ''}>oz</option>
                <option value="lb" ${ing.unit === 'lb' ? 'selected' : ''}>lb</option>
            </select>
            <button type="button" class="btn-remove-ingredient" onclick="this.parentElement.remove()">×</button>
        `;
        container.appendChild(row);
    });

    if (recipe.ingredients.length === 0) {
        addIngredientRow();
    }

    document.getElementById('editRecipeForm').addEventListener('submit', handleEditRecipe);
}

async function handleEditRecipe(e) {
    e.preventDefault();
    const form = e.target;
    const recipeId = form.dataset.recipeId;

    const ingredients = [];
    const names = form.querySelectorAll('[name="ingredient_name[]"]');
    const amounts = form.querySelectorAll('[name="ingredient_amount[]"]');
    const units = form.querySelectorAll('[name="ingredient_unit[]"]');

    for (let i = 0; i < names.length; i++) {
        if (names[i].value && amounts[i].value) {
            ingredients.push({
                name: names[i].value,
                amount: parseFloat(amounts[i].value),
                unit: units[i].value
            });
        }
    }

    const data = {
        name: form.name.value,
        type: form.type.value,
        description: form.description.value,
        ingredients: ingredients
    };

    try {
        const response = await fetch(`${API_BASE}/recipes/${recipeId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            showToast('Recipe updated!', 'success');
            closeModal();
            await loadRecipes();
        } else {
            showToast('Failed to update recipe', 'error');
        }
    } catch (error) {
        showToast('Failed to update recipe', 'error');
    }
}

async function deleteRecipe(recipeId) {
    if (!confirm('Are you sure you want to delete this recipe?')) return;

    try {
        await fetch(`${API_BASE}/recipes/${recipeId}`, { method: 'DELETE' });
        showToast('Recipe deleted', 'success');
        await loadRecipes();
    } catch (error) {
        showToast('Failed to delete recipe', 'error');
    }
}

// ============== Budget ==============
async function loadBudget() {
    try {
        const [productsResponse, summaryResponse] = await Promise.all([
            fetch(`${API_BASE}/budget/products`),
            fetch(`${API_BASE}/budget/summary`)
        ]);

        products = await productsResponse.json();
        const summary = await summaryResponse.json();

        // Update summary cards
        if (elements.totalSpent) {
            elements.totalSpent.textContent = `$${(summary.total_spent || 0).toFixed(2)}`;
        }
        if (elements.totalProducts) {
            elements.totalProducts.textContent = summary.total_products || 0;
        }
        if (elements.activeRecipes) {
            elements.activeRecipes.textContent = summary.active_recipes || 0;
        }

        renderProducts();
        await loadBudgetCharts();
    } catch (error) {
        console.error('Failed to load budget:', error);
    }
}

function renderProducts() {
    if (!elements.productsList) return;

    if (!products.length) {
        elements.productsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">💰</div>
                <h3>No Products Yet</h3>
                <p>Add products to track your garden budget!</p>
            </div>
        `;
        return;
    }

    elements.productsList.innerHTML = products.map(product => `
        <div class="product-card">
            <div class="product-header">
                <span class="product-name">${product.name}</span>
                <span class="product-category">${product.category || 'General'}</span>
            </div>
            <div class="product-details">
                <div class="product-detail">
                    <span class="product-detail-label">Price</span>
                    <span class="product-detail-value">$${(product.price || 0).toFixed(2)}</span>
                </div>
                <div class="product-detail">
                    <span class="product-detail-label">Size</span>
                    <span class="product-detail-value">${product.size_amount || '-'} ${product.size_unit || ''}</span>
                </div>
                <div class="product-detail">
                    <span class="product-detail-label">Price/Unit</span>
                    <span class="product-detail-value price-per-unit">$${(product.price_per_unit || 0).toFixed(4)}</span>
                </div>
                <div class="product-detail">
                    <span class="product-detail-label">Purchased</span>
                    <span class="product-detail-value">${product.purchase_date ? formatDate(new Date(product.purchase_date)) : '-'}</span>
                </div>
            </div>
            <div class="product-actions">
                <button class="btn btn-secondary btn-sm" onclick="editProduct('${product.id}')">Edit</button>
                <button class="btn btn-danger btn-sm" onclick="deleteProduct('${product.id}')">Delete</button>
            </div>
        </div>
    `).join('');
}

function showAddProductModal() {
    showModal('Add New Product', `
        <form id="addProductForm">
            <div class="form-group">
                <label>Product Name *</label>
                <input type="text" name="name" required placeholder="e.g., Fish Emulsion">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Category</label>
                    <select name="category">
                        <option value="fertilizer">Fertilizer</option>
                        <option value="nutrient">Nutrient</option>
                        <option value="soil">Soil</option>
                        <option value="pesticide">Pesticide</option>
                        <option value="equipment">Equipment</option>
                        <option value="other">Other</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Price ($) *</label>
                    <input type="number" name="price" step="0.01" min="0" required placeholder="0.00">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Size Amount</label>
                    <input type="number" name="size_amount" step="0.1" min="0" placeholder="e.g., 16">
                </div>
                <div class="form-group">
                    <label>Size Unit</label>
                    <select name="size_unit">
                        <option value="oz">oz</option>
                        <option value="lb">lb</option>
                        <option value="g">g</option>
                        <option value="kg">kg</option>
                        <option value="ml">ml</option>
                        <option value="L">L</option>
                        <option value="gal">gal</option>
                        <option value="qt">qt</option>
                    </select>
                </div>
            </div>
            <div class="form-group">
                <label>Purchase Date</label>
                <input type="date" name="purchase_date">
            </div>
            <div class="form-group">
                <label>Where Purchased</label>
                <input type="text" name="store" placeholder="e.g., Home Depot">
            </div>
            <div class="form-group">
                <label>Notes</label>
                <textarea name="notes" rows="2" placeholder="Any notes about this product..."></textarea>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Save Product</button>
            </div>
        </form>
    `);

    document.getElementById('addProductForm').addEventListener('submit', handleAddProduct);
}

async function handleAddProduct(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Convert numbers
    if (data.price) data.price = parseFloat(data.price);
    if (data.size_amount) data.size_amount = parseFloat(data.size_amount);

    try {
        const response = await fetch(`${API_BASE}/budget/products`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            showToast('Product saved!', 'success');
            closeModal();
            await loadBudget();
        } else {
            const err = await response.json();
            showToast(err.error || 'Failed to save product', 'error');
        }
    } catch (error) {
        showToast('Failed to save product', 'error');
    }
}

async function editProduct(productId) {
    const product = products.find(p => p.id === productId);
    if (!product) return;

    showModal('Edit Product', `
        <form id="editProductForm" data-product-id="${productId}">
            <div class="form-group">
                <label>Product Name *</label>
                <input type="text" name="name" required value="${product.name}">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Category</label>
                    <select name="category">
                        <option value="fertilizer" ${product.category === 'fertilizer' ? 'selected' : ''}>Fertilizer</option>
                        <option value="nutrient" ${product.category === 'nutrient' ? 'selected' : ''}>Nutrient</option>
                        <option value="soil" ${product.category === 'soil' ? 'selected' : ''}>Soil</option>
                        <option value="pesticide" ${product.category === 'pesticide' ? 'selected' : ''}>Pesticide</option>
                        <option value="equipment" ${product.category === 'equipment' ? 'selected' : ''}>Equipment</option>
                        <option value="other" ${product.category === 'other' ? 'selected' : ''}>Other</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Price ($) *</label>
                    <input type="number" name="price" step="0.01" min="0" required value="${product.price || ''}">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Size Amount</label>
                    <input type="number" name="size_amount" step="0.1" min="0" value="${product.size_amount || ''}">
                </div>
                <div class="form-group">
                    <label>Size Unit</label>
                    <select name="size_unit">
                        <option value="oz" ${product.size_unit === 'oz' ? 'selected' : ''}>oz</option>
                        <option value="lb" ${product.size_unit === 'lb' ? 'selected' : ''}>lb</option>
                        <option value="g" ${product.size_unit === 'g' ? 'selected' : ''}>g</option>
                        <option value="kg" ${product.size_unit === 'kg' ? 'selected' : ''}>kg</option>
                        <option value="ml" ${product.size_unit === 'ml' ? 'selected' : ''}>ml</option>
                        <option value="L" ${product.size_unit === 'L' ? 'selected' : ''}>L</option>
                        <option value="gal" ${product.size_unit === 'gal' ? 'selected' : ''}>gal</option>
                        <option value="qt" ${product.size_unit === 'qt' ? 'selected' : ''}>qt</option>
                    </select>
                </div>
            </div>
            <div class="form-group">
                <label>Purchase Date</label>
                <input type="date" name="purchase_date" value="${product.purchase_date || ''}">
            </div>
            <div class="form-group">
                <label>Where Purchased</label>
                <input type="text" name="store" value="${product.store || ''}">
            </div>
            <div class="form-group">
                <label>Notes</label>
                <textarea name="notes" rows="2">${product.notes || ''}</textarea>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Save Product</button>
            </div>
        </form>
    `);

    document.getElementById('editProductForm').addEventListener('submit', handleEditProduct);
}

async function handleEditProduct(e) {
    e.preventDefault();
    const form = e.target;
    const productId = form.dataset.productId;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    if (data.price) data.price = parseFloat(data.price);
    if (data.size_amount) data.size_amount = parseFloat(data.size_amount);

    try {
        const response = await fetch(`${API_BASE}/budget/products/${productId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            showToast('Product updated!', 'success');
            closeModal();
            await loadBudget();
        } else {
            showToast('Failed to update product', 'error');
        }
    } catch (error) {
        showToast('Failed to update product', 'error');
    }
}

async function deleteProduct(productId) {
    if (!confirm('Are you sure you want to delete this product?')) return;

    try {
        await fetch(`${API_BASE}/budget/products/${productId}`, { method: 'DELETE' });
        showToast('Product deleted', 'success');
        await loadBudget();
    } catch (error) {
        showToast('Failed to delete product', 'error');
    }
}

async function loadBudgetCharts() {
    try {
        const response = await fetch(`${API_BASE}/charts/budget`);
        const data = await response.json();

        // Category Chart
        const catCtx = document.getElementById('budgetCategoryChart')?.getContext('2d');
        if (catCtx && data.by_category) {
            if (budgetCategoryChart) budgetCategoryChart.destroy();

            const categories = Object.keys(data.by_category);
            const values = Object.values(data.by_category);

            if (categories.length > 0) {
                budgetCategoryChart = new Chart(catCtx, {
                    type: 'doughnut',
                    data: {
                        labels: categories,
                        datasets: [{
                            data: values,
                            backgroundColor: [
                                '#22c55e', '#3b82f6', '#f59e0b',
                                '#ef4444', '#8b5cf6', '#ec4899'
                            ]
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: { color: '#94a3b8' }
                            }
                        }
                    }
                });
            }
        }

        // Monthly Chart
        const monthCtx = document.getElementById('budgetMonthlyChart')?.getContext('2d');
        if (monthCtx && data.by_month) {
            if (budgetMonthlyChart) budgetMonthlyChart.destroy();

            const months = Object.keys(data.by_month);
            const values = Object.values(data.by_month);

            if (months.length > 0) {
                budgetMonthlyChart = new Chart(monthCtx, {
                    type: 'bar',
                    data: {
                        labels: months,
                        datasets: [{
                            label: 'Spending ($)',
                            data: values,
                            backgroundColor: 'rgba(59, 130, 246, 0.5)',
                            borderColor: '#3b82f6',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                grid: { color: 'rgba(255, 255, 255, 0.1)' },
                                ticks: { color: '#94a3b8' }
                            },
                            x: {
                                grid: { display: false },
                                ticks: { color: '#94a3b8' }
                            }
                        },
                        plugins: {
                            legend: { display: false }
                        }
                    }
                });
            }
        }
    } catch (error) {
        console.error('Failed to load budget charts:', error);
    }
}

// ============== Utilities ==============
function formatDate(date) {
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${type === 'success' ? '✓' : '✕'}</span>
        <span class="toast-message">${message}</span>
    `;

    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Make functions available globally for inline handlers
window.applyActions = applyActions;
window.cancelActions = cancelActions;
window.completeTask = completeTask;
window.deleteTask = deleteTask;
window.viewPlant = viewPlant;
window.logGrowth = logGrowth;
window.logWatering = logWatering;
window.deletePlant = deletePlant;
window.deleteNote = deleteNote;
window.closeModal = closeModal;
window.addIngredientRow = addIngredientRow;
window.editRecipe = editRecipe;
window.deleteRecipe = deleteRecipe;
window.editProduct = editProduct;
window.deleteProduct = deleteProduct;
window.showLabel = showLabel;
window.scanQuickAction = scanQuickAction;
window.applyScanActions = applyScanActions;
window.cancelScanActions = cancelScanActions;

// ============== Mobile Menu ==============
function setupMobileMenu() {
    if (elements.mobileMenuToggle) {
        elements.mobileMenuToggle.addEventListener('click', () => {
            elements.sidebar.classList.toggle('open');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 &&
                elements.sidebar.classList.contains('open') &&
                !elements.sidebar.contains(e.target) &&
                !elements.mobileMenuToggle.contains(e.target)) {
                elements.sidebar.classList.remove('open');
            }
        });

        // Close sidebar when navigating on mobile
        elements.navItems.forEach(item => {
            item.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    elements.sidebar.classList.remove('open');
                }
            });
        });
    }
}

// ============== Scanner Page ==============
function setupScanner() {
    // Scanner mode tabs
    if (elements.scannerTabs) {
        elements.scannerTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const mode = tab.dataset.mode;
                switchScannerMode(mode);
            });
        });
    }

    // Start/Stop Scanner buttons
    if (elements.startScannerBtn) {
        elements.startScannerBtn.addEventListener('click', startScanner);
    }
    if (elements.stopScannerBtn) {
        elements.stopScannerBtn.addEventListener('click', stopScanner);
    }

    // Process scanned note with AI
    if (elements.processScanNoteBtn) {
        elements.processScanNoteBtn.addEventListener('click', processScanNote);
    }

    // Clear scan result
    if (elements.clearScanBtn) {
        elements.clearScanBtn.addEventListener('click', clearScanResult);
    }

    // Photo capture
    if (elements.photoPreview) {
        elements.photoPreview.addEventListener('click', () => {
            elements.plantPhotoInput?.click();
        });
    }
    if (elements.plantPhotoInput) {
        elements.plantPhotoInput.addEventListener('change', handlePhotoCapture);
    }

    // Create plant from scanner
    if (elements.createScanPlantBtn) {
        elements.createScanPlantBtn.addEventListener('click', createPlantFromScanner);
    }
}

function initScannerPage() {
    // Ensure plants are loaded for scanning
    if (plants.length === 0) {
        loadPlants();
    }
    // Stop any running scanner when leaving page
    stopScanner();
}

function switchScannerMode(mode) {
    // Update tabs
    elements.scannerTabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.mode === mode);
    });

    // Update mode visibility
    if (elements.scanMode) {
        elements.scanMode.classList.toggle('active', mode === 'scan');
    }
    if (elements.createMode) {
        elements.createMode.classList.toggle('active', mode === 'create');
    }

    // Stop scanner when switching to create mode
    if (mode === 'create') {
        stopScanner();
    }
}

async function startScanner() {
    try {
        // Initialize html5-qrcode if not already done
        if (!html5QrCode) {
            html5QrCode = new Html5Qrcode("qrReader");
        }

        const config = {
            fps: 10,
            qrbox: { width: 250, height: 250 },
            aspectRatio: 1.0
        };

        await html5QrCode.start(
            { facingMode: "environment" },
            config,
            onScanSuccess,
            onScanFailure
        );

        // Update UI
        elements.startScannerBtn.classList.add('hidden');
        elements.stopScannerBtn.classList.remove('hidden');
        showToast('Scanner started', 'success');

    } catch (error) {
        console.error('Failed to start scanner:', error);
        showToast('Could not start camera. Please allow camera access.', 'error');
    }
}

async function stopScanner() {
    try {
        if (html5QrCode && html5QrCode.isScanning) {
            await html5QrCode.stop();
        }
    } catch (error) {
        console.error('Error stopping scanner:', error);
    }

    // Update UI
    if (elements.startScannerBtn) {
        elements.startScannerBtn.classList.remove('hidden');
    }
    if (elements.stopScannerBtn) {
        elements.stopScannerBtn.classList.add('hidden');
    }
}

function onScanSuccess(decodedText, decodedResult) {
    console.log('Scanned:', decodedText);

    // Parse the scanned URL
    // Expected format: http://host/plant/CODE-001 or just CODE-001
    let plantCode = decodedText;

    // Try to extract code from URL
    const urlMatch = decodedText.match(/\/plant\/([A-Z]{3}-\d+)/i);
    if (urlMatch) {
        plantCode = urlMatch[1];
    }

    // Find plant by unique_code
    const plant = plants.find(p =>
        p.unique_code && p.unique_code.toUpperCase() === plantCode.toUpperCase()
    );

    if (plant) {
        // Stop scanner after successful scan
        stopScanner();

        // Store scanned plant reference
        scannedPlant = plant;

        // Show scan result panel
        showScanResult(plant);
        showToast(`Found: ${plant.display_name || plant.name}`, 'success');
    } else {
        // Plant not found - could be first scan ever or invalid code
        showToast(`No plant found with code: ${plantCode}`, 'error');
    }
}

function onScanFailure(error) {
    // Silently ignore scan failures (no QR in view)
    // Only log if it's not a "No QR code found" error
    if (!error.includes('No QR code found')) {
        console.warn('QR scan error:', error);
    }
}

function showScanResult(plant) {
    if (!elements.scanResult) return;

    const displayName = plant.display_name || plant.name;

    // Populate plant info
    elements.scanPlantName.textContent = displayName;
    elements.scanPlantCode.textContent = plant.unique_code || 'N/A';
    elements.scanPlantStatus.textContent = plant.status;
    elements.scanPlantStatus.className = `scan-plant-status ${plant.status}`;
    elements.scanPlantId.value = plant.id;

    // Clear previous note and actions
    elements.scanNoteInput.value = '';
    elements.scanExtractedActions.classList.add('hidden');
    elements.scanExtractedActions.innerHTML = '';

    // Show the result panel
    elements.scanResult.classList.remove('hidden');

    // Scroll to result
    elements.scanResult.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function clearScanResult() {
    scannedPlant = null;

    if (elements.scanResult) {
        elements.scanResult.classList.add('hidden');
    }
    if (elements.scanNoteInput) {
        elements.scanNoteInput.value = '';
    }
    if (elements.scanExtractedActions) {
        elements.scanExtractedActions.classList.add('hidden');
        elements.scanExtractedActions.innerHTML = '';
    }
}

// Quick action buttons add pre-filled text
function scanQuickAction(action) {
    if (!scannedPlant) return;

    const displayName = scannedPlant.display_name || scannedPlant.name;
    let prefill = '';

    switch (action) {
        case 'water':
            prefill = `Watered ${displayName}. `;
            break;
        case 'growth':
            prefill = `${displayName} is now cm tall, health rating /10. `;
            break;
        case 'harvest':
            prefill = `Harvested from ${displayName}: `;
            break;
        case 'pest':
            prefill = `Found issue on ${displayName}: `;
            break;
    }

    elements.scanNoteInput.value = prefill;
    elements.scanNoteInput.focus();

    // Position cursor where user should type
    const cursorPos = prefill.indexOf('cm') > 0 ? prefill.indexOf('cm') - 1 : prefill.length;
    elements.scanNoteInput.setSelectionRange(cursorPos, cursorPos);
}

async function processScanNote() {
    const note = elements.scanNoteInput.value.trim();

    if (!note) {
        showToast('Please enter a note first', 'error');
        return;
    }

    if (!scannedPlant) {
        showToast('No plant selected', 'error');
        return;
    }

    elements.processScanNoteBtn.disabled = true;
    elements.processScanNoteBtn.innerHTML = '<span class="btn-icon">⏳</span> Processing...';

    try {
        // Add plant context to the note
        const displayName = scannedPlant.display_name || scannedPlant.name;
        const contextNote = `[For plant: ${displayName} (${scannedPlant.unique_code})] ${note}`;

        const response = await fetch(`${API_BASE}/llm/process-note`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                note: contextNote,
                plant_context: {
                    id: scannedPlant.id,
                    name: scannedPlant.name,
                    unique_code: scannedPlant.unique_code
                }
            })
        });

        const data = await response.json();

        if (data.extracted_actions && data.extracted_actions.length > 0) {
            // Auto-set plant_id for actions that need it
            data.extracted_actions = data.extracted_actions.map(action => {
                if (['log_watering', 'log_fertilization', 'log_growth', 'log_harvest', 'report_pest_issue', 'update_plant_status'].includes(action.action)) {
                    action.parameters = action.parameters || {};
                    action.parameters.plant_id = scannedPlant.id;
                    action.parameters.plant_name = scannedPlant.name;
                }
                return action;
            });

            displayScanExtractedActions(data.extracted_actions);
            showToast(`Found ${data.extracted_actions.length} action(s)`, 'success');
        } else {
            showToast('No actions detected in note', 'error');
        }
    } catch (error) {
        console.error('Failed to process note:', error);
        showToast('Failed to process note with AI', 'error');
    } finally {
        elements.processScanNoteBtn.disabled = false;
        elements.processScanNoteBtn.innerHTML = '<span class="btn-icon">✨</span> Process with AI';
    }
}

function displayScanExtractedActions(actions) {
    const container = elements.scanExtractedActions;

    const actionIcons = {
        'add_plant': '🌱',
        'log_watering': '💧',
        'log_fertilization': '🧪',
        'log_growth': '📏',
        'log_harvest': '🥕',
        'report_pest_issue': '🐛',
        'create_task': '✅',
        'log_weather': '🌤️',
        'update_plant_status': '📊',
        'add_budget_item': '💰'
    };

    let html = `
        <h4>Extracted Actions</h4>
        <div class="actions-list">
    `;

    actions.forEach((action, index) => {
        const icon = actionIcons[action.action] || '📝';
        const params = Object.entries(action.parameters || {})
            .filter(([key]) => !['plant_id'].includes(key))
            .map(([key, value]) => `<span class="param">${key}: ${value}</span>`)
            .join('');

        html += `
            <div class="action-item">
                <span class="action-icon">${icon}</span>
                <div class="action-details">
                    <strong>${action.action.replace(/_/g, ' ')}</strong>
                    <div class="action-params">${params}</div>
                </div>
            </div>
        `;
    });

    html += `
        </div>
        <div class="actions-buttons">
            <button class="btn btn-secondary" onclick="cancelScanActions()">Cancel</button>
            <button class="btn btn-primary" onclick="applyScanActions()">Apply All Actions</button>
        </div>
    `;

    container.innerHTML = html;
    container.classList.remove('hidden');

    // Store actions for applying
    container.dataset.actions = JSON.stringify(actions);
}

async function applyScanActions() {
    const container = elements.scanExtractedActions;
    const actions = JSON.parse(container.dataset.actions || '[]');

    if (actions.length === 0) return;

    try {
        const response = await fetch(`${API_BASE}/llm/apply-actions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ actions })
        });

        const data = await response.json();

        showToast(data.message || 'Actions applied successfully!', 'success');

        // Clear the scan result and reload data
        clearScanResult();
        await loadPlants();
        await loadDashboardData();

    } catch (error) {
        console.error('Failed to apply actions:', error);
        showToast('Failed to apply actions', 'error');
    }
}

function cancelScanActions() {
    elements.scanExtractedActions.classList.add('hidden');
    elements.scanExtractedActions.innerHTML = '';
}

// ============== Photo Capture for New Plant ==============
function handlePhotoCapture(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function (e) {
        capturedPhotoData = e.target.result;

        // Update preview
        const preview = elements.photoPreview;
        preview.innerHTML = `<img src="${capturedPhotoData}" alt="Plant photo">`;
        preview.classList.add('has-image');
    };
    reader.readAsDataURL(file);
}

async function createPlantFromScanner() {
    const name = elements.scanPlantNameInput?.value.trim();
    const variety = elements.scanVarietyInput?.value.trim();
    const quantity = parseInt(elements.scanQuantityInput?.value) || 1;
    const location = elements.scanLocationInput?.value.trim();
    const notes = elements.scanNotesInput?.value.trim();

    if (!name) {
        showToast('Please enter a plant name', 'error');
        return;
    }

    elements.createScanPlantBtn.disabled = true;
    elements.createScanPlantBtn.textContent = 'Creating...';

    try {
        const plantData = {
            name,
            variety,
            quantity,
            location,
            notes,
            date_planted: new Date().toISOString().split('T')[0]
        };

        const response = await fetch(`${API_BASE}/plants`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(plantData)
        });

        const data = await response.json();

        if (data.id || data.ids) {
            const plantId = data.id || data.ids[0];

            // If we have a photo, upload it
            if (capturedPhotoData && plantId) {
                await uploadPlantPhoto(plantId, capturedPhotoData);
            }

            showToast('Plant created! Generating QR code...', 'success');

            // Reload plants and show the label
            await loadPlants();

            // Show the QR label for the new plant
            setTimeout(() => {
                showLabel(plantId);
            }, 500);

            // Reset form
            resetScannerCreateForm();
        }
    } catch (error) {
        console.error('Failed to create plant:', error);
        showToast('Failed to create plant', 'error');
    } finally {
        elements.createScanPlantBtn.disabled = false;
        elements.createScanPlantBtn.textContent = '🌱 Create Plant & Generate QR';
    }
}

async function uploadPlantPhoto(plantId, photoData) {
    try {
        const response = await fetch(`${API_BASE}/plant/${plantId}/image`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_data: photoData })
        });

        if (response.ok) {
            console.log('Photo uploaded successfully');
        }
    } catch (error) {
        console.error('Failed to upload photo:', error);
        // Don't show error - photo upload is optional
    }
}

function resetScannerCreateForm() {
    if (elements.scanPlantNameInput) elements.scanPlantNameInput.value = '';
    if (elements.scanVarietyInput) elements.scanVarietyInput.value = '';
    if (elements.scanQuantityInput) elements.scanQuantityInput.value = '1';
    if (elements.scanLocationInput) elements.scanLocationInput.value = '';
    if (elements.scanNotesInput) elements.scanNotesInput.value = '';
    if (elements.plantPhotoInput) elements.plantPhotoInput.value = '';

    // Reset photo preview
    if (elements.photoPreview) {
        elements.photoPreview.innerHTML = `
            <span class="photo-placeholder">📷</span>
            <p>Tap to take photo</p>
        `;
        elements.photoPreview.classList.remove('has-image');
    }

    capturedPhotoData = null;
}
