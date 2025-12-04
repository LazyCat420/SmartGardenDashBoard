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
    tasksList: document.getElementById('tasksList'),
    harvestsList: document.getElementById('harvestsList'),
    notesList: document.getElementById('notesList'),
    weatherList: document.getElementById('weatherList'),
    recipesList: document.getElementById('recipesList'),
    productsList: document.getElementById('productsList'),
    
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
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

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
        scanner: 'Plant Scanner'
    };
    elements.pageTitle.textContent = titles[page] || page;
    
    // Load page data
    loadPageData(page);
}

async function loadPageData(page) {
    switch(page) {
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
        
        if (data.success && data.extracted_actions.length > 0) {
            displayExtractedActions(data.extracted_actions);
        } else if (data.error) {
            showToast(data.error, 'error');
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
}

async function loadPlants() {
    try {
        const response = await fetch(`${API_BASE}/plants`);
        plants = await response.json();
        
        const filter = elements.plantStatusFilter?.value || 'active';
        let filteredPlants = plants;
        
        if (filter !== 'all') {
            filteredPlants = plants.filter(p => p.status === filter);
        }
        
        renderPlants(filteredPlants);
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
                    <span class="note-badge ${note.processed ? 'processed' : 'pending'}">
                        ${note.processed ? '✓ Processed' : 'Pending'}
                    </span>
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
    
    elements.weatherList.innerHTML = weatherList.map(w => {
        const icon = weatherIcons[w.conditions?.toLowerCase()] || '🌤️';
        
        return `
            <div class="weather-item">
                <div class="weather-icon">${icon}</div>
                <div class="weather-info">
                    <div class="weather-date">${formatDate(new Date(w.date))}</div>
                    <div class="weather-conditions">${w.conditions || 'Unknown conditions'}</div>
                </div>
                <div class="weather-temps">
                    <div class="weather-temp high">
                        <div class="weather-temp-value">${w.temperature_high || '--'}°</div>
                        <div class="weather-temp-label">High</div>
                    </div>
                    <div class="weather-temp low">
                        <div class="weather-temp-value">${w.temperature_low || '--'}°</div>
                        <div class="weather-temp-label">Low</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
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
    if (plantGrowthChart) { try { plantGrowthChart.destroy(); } catch(e) {} plantGrowthChart = null; }
    if (plantWateringChart) { try { plantWateringChart.destroy(); } catch(e) {} plantWateringChart = null; }
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
            
            <div class="form-group">
                <label>Notes</label>
                <p>${plant.notes || 'No notes'}</p>
            </div>
            <div class="form-actions">
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
        try { plantGrowthChart.destroy(); } catch(e) {}
        plantGrowthChart = null;
    }
    if (plantWateringChart) {
        try { plantWateringChart.destroy(); } catch(e) {}
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
    
    showModal(`💧 Log Watering - ${plant.name}`, `
        <form id="logWateringForm" data-plant-id="${plantId}">
            <div class="form-row">
                <div class="form-group">
                    <label>Amount (ml)</label>
                    <input type="number" name="amount_ml" placeholder="e.g., 500">
                </div>
                <div class="form-group">
                    <label>Method</label>
                    <select name="method">
                        <option value="watering can">Watering Can</option>
                        <option value="hose">Hose</option>
                        <option value="compost tea">Compost Tea</option>
                        <option value="spray">Spray</option>
                        <option value="soak">Deep Soak</option>
                    </select>
                </div>
            </div>
            <div class="form-group">
                <label>Notes</label>
                <textarea name="notes" rows="2" placeholder="Any notes..."></textarea>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Log Watering</button>
            </div>
        </form>
    `);
    
    document.getElementById('logWateringForm').addEventListener('submit', handleLogWatering);
}

async function handleLogWatering(e) {
    e.preventDefault();
    const form = e.target;
    const plantId = form.dataset.plantId;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    if (data.amount_ml) data.amount_ml = parseFloat(data.amount_ml);
    
    try {
        await fetch(`${API_BASE}/plants/${plantId}/watering`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        showToast('Watering logged!', 'success');
        closeModal();
    } catch (error) {
        showToast('Failed to log watering', 'error');
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
        
        if (data.actions && data.actions.length > 0) {
            // Auto-set plant_id for actions that need it
            data.actions = data.actions.map(action => {
                if (['log_watering', 'log_fertilization', 'log_growth', 'log_harvest', 'report_pest', 'update_status'].includes(action.action)) {
                    action.parameters = action.parameters || {};
                    action.parameters.plant_id = scannedPlant.id;
                    action.parameters.plant_name = scannedPlant.name;
                }
                return action;
            });
            
            displayScanExtractedActions(data.actions);
            showToast(`Found ${data.actions.length} action(s)`, 'success');
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
        'report_pest': '🐛',
        'create_task': '✅',
        'log_weather': '🌤️',
        'update_status': '📊',
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
    reader.onload = function(e) {
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
